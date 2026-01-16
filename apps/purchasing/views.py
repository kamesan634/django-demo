"""
Purchasing views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import F, Sum, Q

from apps.core.views import BaseViewSet
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from apps.core.utils import generate_order_number
from apps.inventory.services import InventoryService
from .models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem,
    PurchaseReturn, PurchaseReturnItem,
    SupplierPrice
)
from .serializers import (
    SupplierSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseOrderCreateSerializer,
    ReceiveSerializer,
    GoodsReceiptSerializer,
    PurchaseReturnListSerializer,
    PurchaseReturnDetailSerializer,
    PurchaseReturnCreateSerializer,
    SupplierPriceSerializer,
)


class SupplierViewSet(BaseViewSet):
    """Supplier management ViewSet."""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ['name', 'code', 'contact_name', 'phone']
    filterset_fields = ['is_active']
    ordering_fields = ['name', 'code', 'created_at']


class PurchaseOrderViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """PurchaseOrder management ViewSet."""
    queryset = PurchaseOrder.objects.select_related('supplier', 'warehouse').all()
    serializer_class = PurchaseOrderListSerializer
    serializer_classes = {
        'list': PurchaseOrderListSerializer,
        'retrieve': PurchaseOrderDetailSerializer,
        'create': PurchaseOrderCreateSerializer,
    }
    filterset_fields = ['supplier', 'warehouse', 'status']
    search_fields = ['po_number', 'supplier__name']
    ordering_fields = ['created_at', 'total_amount']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit purchase order for approval."""
        po = self.get_object()

        if po.status != 'DRAFT':
            return self.error_response(message='只有草稿狀態的採購單可以送出')

        if not po.items.exists():
            return self.error_response(message='採購單沒有明細項目')

        po.status = 'SUBMITTED'
        po.submitted_at = timezone.now()
        po.save()

        return self.success_response(message='採購單已送出')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve purchase order."""
        po = self.get_object()

        if po.status != 'SUBMITTED':
            return self.error_response(message='只有已送出的採購單可以核准')

        po.status = 'APPROVED'
        po.approved_by = request.user
        po.approved_at = timezone.now()
        po.save()

        return self.success_response(message='採購單已核准')

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Receive goods for purchase order."""
        po = self.get_object()

        if po.status not in ['APPROVED', 'PARTIAL']:
            return self.error_response(message='採購單狀態不正確，無法驗收')

        serializer = ReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Create goods receipt
            receipt = GoodsReceipt.objects.create(
                receipt_number=generate_order_number('GR'),
                purchase_order=po,
                receipt_date=timezone.now().date(),
                note=serializer.validated_data.get('note', ''),
                created_by=request.user
            )

            for item_data in serializer.validated_data['items']:
                po_item = PurchaseOrderItem.objects.get(pk=item_data['po_item_id'])

                if po_item.purchase_order_id != po.id:
                    raise ValueError('項目不屬於此採購單')

                remaining = po_item.quantity - po_item.received_quantity
                if item_data['received_quantity'] > remaining:
                    raise ValueError(f'商品 {po_item.product.name} 收貨數量超過未收數量')

                # Create receipt item
                GoodsReceiptItem.objects.create(
                    receipt=receipt,
                    po_item=po_item,
                    received_quantity=item_data['received_quantity'],
                    created_by=request.user
                )

                # Update PO item received quantity
                po_item.received_quantity += item_data['received_quantity']
                po_item.save(update_fields=['received_quantity'])

                # Add to inventory
                InventoryService.adjust_stock(
                    warehouse_id=po.warehouse_id,
                    product_id=po_item.product_id,
                    quantity=item_data['received_quantity'],
                    movement_type='PURCHASE_IN',
                    reference_type='PurchaseOrder',
                    reference_id=po.id,
                    note=f'採購入庫: {po.po_number}',
                    user=request.user
                )

            receipt.status = 'COMPLETED'
            receipt.save()

            # Update PO status
            total_qty = po.items.aggregate(total=Sum('quantity'))['total'] or 0
            received_qty = po.items.aggregate(total=Sum('received_quantity'))['total'] or 0

            if received_qty >= total_qty:
                po.status = 'COMPLETED'
            else:
                po.status = 'PARTIAL'
            po.save()

            return self.success_response(
                message='驗收完成',
                data={'receipt_number': receipt.receipt_number}
            )

        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get purchase suggestions based on low stock."""
        from apps.inventory.models import Inventory
        from django.db.models import F

        low_stock = Inventory.objects.select_related('product', 'warehouse').filter(
            quantity__lte=F('product__safety_stock'),
            product__status='ACTIVE'
        )

        suggestions = []
        for inv in low_stock:
            suggestions.append({
                'product_id': inv.product.id,
                'product_name': inv.product.name,
                'product_sku': inv.product.sku,
                'warehouse_id': inv.warehouse.id,
                'warehouse_name': inv.warehouse.name,
                'current_stock': inv.quantity,
                'safety_stock': inv.product.safety_stock,
                'suggested_quantity': max(0, inv.product.safety_stock * 2 - inv.quantity)
            })

        return Response({
            'success': True,
            'data': suggestions
        })


class PurchaseReturnViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """Purchase Return management ViewSet."""
    queryset = PurchaseReturn.objects.select_related(
        'purchase_order', 'supplier', 'warehouse'
    ).prefetch_related('items')
    serializer_class = PurchaseReturnListSerializer
    serializer_classes = {
        'list': PurchaseReturnListSerializer,
        'retrieve': PurchaseReturnDetailSerializer,
    }
    filterset_fields = ['supplier', 'warehouse', 'status', 'reason']
    search_fields = ['return_number', 'purchase_order__po_number', 'supplier__name']
    ordering_fields = ['created_at', 'total_amount', 'return_date']

    @action(detail=False, methods=['post'])
    def create_return(self, request):
        """Create a purchase return."""
        serializer = PurchaseReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            po = PurchaseOrder.objects.get(pk=data['purchase_order_id'])

            if po.status not in ['PARTIAL', 'COMPLETED']:
                return self.error_response(message='採購單狀態不允許退貨')

            # Create purchase return
            pr = PurchaseReturn.objects.create(
                return_number=generate_order_number('PR'),
                purchase_order=po,
                supplier=po.supplier,
                warehouse=po.warehouse,
                reason=data['reason'],
                reason_detail=data.get('reason_detail', ''),
                return_date=data['return_date'],
                note=data.get('note', ''),
                created_by=request.user
            )

            # Create return items
            for item_data in data['items']:
                po_item = PurchaseOrderItem.objects.get(pk=item_data['po_item_id'])

                if po_item.purchase_order_id != po.id:
                    raise ValueError('項目不屬於此採購單')

                if item_data['quantity'] > po_item.received_quantity:
                    raise ValueError(f'商品 {po_item.product.name} 退貨數量不能超過已收數量')

                PurchaseReturnItem.objects.create(
                    purchase_return=pr,
                    po_item=po_item,
                    product=po_item.product,
                    quantity=item_data['quantity'],
                    unit_price=po_item.unit_price,
                    reason=item_data.get('reason', ''),
                    created_by=request.user
                )

            pr.calculate_total()

            return self.success_response(
                message='採購退貨單建立成功',
                data=PurchaseReturnDetailSerializer(pr).data,
                status_code=status.HTTP_201_CREATED
            )

        except PurchaseOrder.DoesNotExist:
            return self.error_response(message='找不到採購單')
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit purchase return for approval."""
        pr = self.get_object()

        if pr.status != 'DRAFT':
            return self.error_response(message='只有草稿狀態可以送出')

        if not pr.items.exists():
            return self.error_response(message='退貨單沒有明細項目')

        pr.status = 'SUBMITTED'
        pr.save()

        return self.success_response(message='退貨單已送出')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve purchase return."""
        pr = self.get_object()

        if pr.status != 'SUBMITTED':
            return self.error_response(message='只有已送出的退貨單可以核准')

        pr.status = 'APPROVED'
        pr.approved_by = request.user
        pr.approved_at = timezone.now()
        pr.save()

        return self.success_response(message='退貨單已核准')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete purchase return and deduct inventory."""
        pr = self.get_object()

        if pr.status != 'APPROVED':
            return self.error_response(message='只有已核准的退貨單可以完成')

        try:
            for item in pr.items.all():
                # Deduct from inventory
                InventoryService.adjust_stock(
                    warehouse_id=pr.warehouse_id,
                    product_id=item.product_id,
                    quantity=-item.quantity,
                    movement_type='RETURN_OUT',
                    reference_type='PurchaseReturn',
                    reference_id=pr.id,
                    note=f'採購退貨出庫: {pr.return_number}',
                    user=request.user
                )

                # Update PO item received quantity
                item.po_item.received_quantity -= item.quantity
                item.po_item.save(update_fields=['received_quantity'])

            pr.status = 'COMPLETED'
            pr.completed_at = timezone.now()
            pr.save()

            return self.success_response(message='退貨處理完成')

        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel purchase return."""
        pr = self.get_object()

        if pr.status in ['COMPLETED', 'CANCELLED']:
            return self.error_response(message='此狀態的退貨單無法取消')

        pr.status = 'CANCELLED'
        pr.save()

        return self.success_response(message='退貨單已取消')


class SupplierPriceViewSet(StandardResponseMixin, BaseViewSet):
    """Supplier Price management ViewSet."""
    queryset = SupplierPrice.objects.select_related('supplier', 'product')
    serializer_class = SupplierPriceSerializer
    filterset_fields = ['supplier', 'product', 'is_preferred']
    search_fields = ['supplier__name', 'product__name', 'product__sku']
    ordering_fields = ['unit_price', 'effective_from', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get all supplier prices for a product."""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return self.error_response(message='請提供商品ID')

        prices = SupplierPrice.objects.filter(
            product_id=product_id
        ).select_related('supplier').order_by('unit_price')

        # Filter to active prices only
        from django.utils import timezone
        today = timezone.now().date()
        active_prices = [
            p for p in prices
            if p.effective_from <= today and (not p.effective_to or p.effective_to >= today)
        ]

        return self.success_response(
            data=SupplierPriceSerializer(active_prices, many=True).data
        )

    @action(detail=False, methods=['get'])
    def by_supplier(self, request):
        """Get all product prices for a supplier."""
        supplier_id = request.query_params.get('supplier_id')
        if not supplier_id:
            return self.error_response(message='請提供供應商ID')

        prices = SupplierPrice.objects.filter(
            supplier_id=supplier_id
        ).select_related('product').order_by('product__name')

        return self.success_response(
            data=SupplierPriceSerializer(prices, many=True).data
        )

    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Compare prices from different suppliers for products."""
        product_ids = request.query_params.get('product_ids', '').split(',')
        product_ids = [int(pid) for pid in product_ids if pid.strip().isdigit()]

        if not product_ids:
            return self.error_response(message='請提供商品ID')

        from django.utils import timezone
        from apps.products.models import Product
        today = timezone.now().date()

        result = []
        for product_id in product_ids:
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                continue

            prices = SupplierPrice.objects.filter(
                product_id=product_id,
                effective_from__lte=today
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=today)
            ).select_related('supplier').order_by('unit_price')

            suppliers_data = []
            for price in prices:
                suppliers_data.append({
                    'supplier_id': price.supplier_id,
                    'supplier_name': price.supplier.name,
                    'unit_price': float(price.unit_price),
                    'min_quantity': price.min_quantity,
                    'lead_time_days': price.lead_time_days,
                    'is_preferred': price.is_preferred
                })

            result.append({
                'product_id': product_id,
                'product_name': product.name,
                'product_sku': product.sku,
                'suppliers': suppliers_data,
                'lowest_price': float(prices.first().unit_price) if prices.exists() else None
            })

        return self.success_response(data=result)

    @action(detail=True, methods=['post'])
    def set_preferred(self, request, pk=None):
        """Set this price as preferred for the product-supplier combination."""
        price = self.get_object()

        # Remove preferred from other prices for this product
        SupplierPrice.objects.filter(
            product=price.product,
            is_preferred=True
        ).update(is_preferred=False)

        price.is_preferred = True
        price.save()

        return self.success_response(message='已設為首選供應商')
