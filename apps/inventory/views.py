"""
Inventory views.
F04-001 ~ F04-007: 庫存管理功能
F05-010: 庫存同步機制
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import F, Sum, Count

from apps.core.views import BaseViewSet, ReadOnlyViewSet
from apps.core.mixins import StandardResponseMixin
from apps.core.utils import generate_order_number
from apps.core.permissions import IsManagerOrAbove
from .models import (
    Inventory, InventoryMovement,
    StockCount, StockCountItem,
    StockTransfer, StockTransferItem
)
from .serializers import (
    InventorySerializer,
    InventoryMovementSerializer,
    StockAdjustmentSerializer,
    StockCountSerializer,
    StockTransferSerializer,
)
from .services import InventoryService
from .sync_services import InventorySyncService, InventoryEventHandler


class InventoryViewSet(StandardResponseMixin, ReadOnlyViewSet):
    """Inventory query ViewSet."""
    queryset = Inventory.objects.select_related('warehouse', 'product').all()
    serializer_class = InventorySerializer
    filterset_fields = ['warehouse', 'product']
    search_fields = ['product__name', 'product__sku']
    ordering_fields = ['quantity', 'available_quantity']

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        """Adjust inventory quantity."""
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            movement_type = 'ADJUST_IN' if data['adjustment_type'] == 'IN' else 'ADJUST_OUT'
            quantity = data['quantity'] if data['adjustment_type'] == 'IN' else -data['quantity']

            result = InventoryService.adjust_stock(
                warehouse_id=data['warehouse_id'],
                product_id=data['product_id'],
                quantity=quantity,
                movement_type=movement_type,
                note=data.get('note', ''),
                user=request.user
            )

            return self.success_response(
                message='庫存調整成功',
                data={'new_quantity': result.quantity}
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock."""
        warehouse_id = request.query_params.get('warehouse')

        queryset = self.get_queryset().select_related('product')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        low_stock_items = queryset.filter(
            quantity__lte=F('product__safety_stock')
        )

        serializer = self.get_serializer(low_stock_items, many=True)
        return self.success_response(data=serializer.data)

    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """
        Get low stock alerts with severity levels.
        F04-007: 安全庫存警示
        """
        warehouse_id = request.query_params.get('warehouse')
        level = request.query_params.get('level')  # OUT_OF_STOCK, CRITICAL, WARNING, LOW

        alerts = InventorySyncService.get_low_stock_alerts(
            warehouse_id=int(warehouse_id) if warehouse_id else None
        )

        if level:
            alerts = [a for a in alerts if a['alert_level'] == level]

        # Summary stats
        summary = {
            'OUT_OF_STOCK': len([a for a in alerts if a['alert_level'] == 'OUT_OF_STOCK']),
            'CRITICAL': len([a for a in alerts if a['alert_level'] == 'CRITICAL']),
            'WARNING': len([a for a in alerts if a['alert_level'] == 'WARNING']),
            'LOW': len([a for a in alerts if a['alert_level'] == 'LOW']),
        }

        return self.success_response(data={
            'summary': summary,
            'total': len(alerts),
            'alerts': alerts
        })

    @action(detail=False, methods=['get'], url_path='product/(?P<product_id>[^/.]+)')
    def product_summary(self, request, product_id=None):
        """
        Get inventory summary for a product across all warehouses.
        F04-001: 庫存卡查詢
        """
        try:
            summary = InventorySyncService.get_product_inventory_summary(
                product_id=int(product_id)
            )
            return self.success_response(data=summary)
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['post'])
    def sync_adjust(self, request):
        """
        Adjust inventory with distributed locking.
        F05-010: 庫存同步機制
        """
        warehouse_id = request.data.get('warehouse_id')
        product_id = request.data.get('product_id')
        adjustment_type = request.data.get('adjustment_type')  # 'IN' or 'OUT'
        quantity = request.data.get('quantity')
        note = request.data.get('note', '')

        if not all([warehouse_id, product_id, adjustment_type, quantity]):
            return self.error_response(message='缺少必要參數')

        try:
            movement_type = 'ADJUST_IN' if adjustment_type == 'IN' else 'ADJUST_OUT'
            qty_change = int(quantity) if adjustment_type == 'IN' else -int(quantity)

            result = InventorySyncService.sync_update_inventory(
                warehouse_id=int(warehouse_id),
                product_id=int(product_id),
                quantity_change=qty_change,
                movement_type=movement_type,
                note=note,
                user=request.user
            )

            return self.success_response(
                message='庫存調整成功（同步）',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['post'])
    def reserve(self, request):
        """
        Reserve stock for an order.
        F05-010: 庫存預留
        """
        warehouse_id = request.data.get('warehouse_id')
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        reference_type = request.data.get('reference_type', '')
        reference_id = request.data.get('reference_id')

        if not all([warehouse_id, product_id, quantity]):
            return self.error_response(message='缺少必要參數')

        try:
            result = InventorySyncService.sync_reserve_stock(
                warehouse_id=int(warehouse_id),
                product_id=int(product_id),
                quantity=int(quantity),
                reference_type=reference_type,
                reference_id=int(reference_id) if reference_id else None,
                user=request.user
            )

            return self.success_response(
                message='庫存預留成功',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['post'])
    def release(self, request):
        """
        Release reserved stock.
        F05-010: 釋放預留庫存
        """
        warehouse_id = request.data.get('warehouse_id')
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        reference_type = request.data.get('reference_type', '')
        reference_id = request.data.get('reference_id')

        if not all([warehouse_id, product_id, quantity]):
            return self.error_response(message='缺少必要參數')

        try:
            result = InventorySyncService.sync_release_stock(
                warehouse_id=int(warehouse_id),
                product_id=int(product_id),
                quantity=int(quantity),
                reference_type=reference_type,
                reference_id=int(reference_id) if reference_id else None,
                user=request.user
            )

            return self.success_response(
                message='庫存釋放成功',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['post'])
    def batch_adjust(self, request):
        """
        Batch adjust inventory for multiple products.
        F05-010: 批量庫存調整
        """
        updates = request.data.get('updates', [])

        if not updates:
            return self.error_response(message='沒有提供調整資料')

        try:
            result = InventorySyncService.batch_sync_inventory(
                updates=updates,
                user=request.user
            )

            return self.success_response(
                message=f'批量調整完成: 成功 {result["success_count"]} 筆, 失敗 {result["failed_count"]} 筆',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))


class InventoryMovementViewSet(ReadOnlyViewSet):
    """InventoryMovement query ViewSet."""
    queryset = InventoryMovement.objects.select_related(
        'warehouse', 'product', 'created_by'
    ).all()
    serializer_class = InventoryMovementSerializer
    filterset_fields = ['warehouse', 'product', 'movement_type']
    search_fields = ['product__name', 'product__sku']
    ordering_fields = ['created_at']


class StockCountViewSet(StandardResponseMixin, BaseViewSet):
    """StockCount management ViewSet."""
    queryset = StockCount.objects.select_related('warehouse').prefetch_related('items')
    serializer_class = StockCountSerializer
    filterset_fields = ['warehouse', 'status']
    ordering_fields = ['count_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(
            count_number=generate_order_number('SC'),
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete stock count and adjust inventory.
        F04-005: 庫存盤點
        F05-010: 同步盤點調整
        """
        stock_count = self.get_object()

        if stock_count.status != 'IN_PROGRESS':
            return self.error_response(message='盤點單狀態不正確')

        try:
            # Collect all adjustments
            adjustments = []
            for item in stock_count.items.filter(actual_quantity__isnull=False):
                if item.difference != 0:
                    adjustments.append({
                        'product_id': item.product_id,
                        'difference': item.difference
                    })

            # Use event handler for batch adjustment
            if adjustments:
                result = InventoryEventHandler.on_stock_count_completed(
                    warehouse_id=stock_count.warehouse_id,
                    adjustments=adjustments,
                    count_id=stock_count.id,
                    user=request.user
                )

            stock_count.status = 'COMPLETED'
            stock_count.completed_at = timezone.now()
            stock_count.save()

            return self.success_response(
                message='盤點完成',
                data={
                    'adjusted_items': len(adjustments),
                    'count_number': stock_count.count_number
                }
            )
        except Exception as e:
            return self.error_response(message=str(e))


class StockTransferViewSet(StandardResponseMixin, BaseViewSet):
    """StockTransfer management ViewSet."""
    queryset = StockTransfer.objects.select_related(
        'from_warehouse', 'to_warehouse'
    ).prefetch_related('items')
    serializer_class = StockTransferSerializer
    filterset_fields = ['from_warehouse', 'to_warehouse', 'status']
    ordering_fields = ['transfer_date', 'created_at']

    def perform_create(self, serializer):
        serializer.save(
            transfer_number=generate_order_number('TR'),
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete stock transfer with distributed locking.
        F04-006: 庫存調撥
        F05-010: 同步調撥
        """
        transfer = self.get_object()

        if transfer.status != 'IN_TRANSIT':
            return self.error_response(message='調撥單狀態不正確')

        try:
            results = []
            for item in transfer.items.all():
                # Use sync service for atomic transfer
                result = InventorySyncService.sync_transfer_stock(
                    from_warehouse_id=transfer.from_warehouse_id,
                    to_warehouse_id=transfer.to_warehouse_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    transfer_id=transfer.id,
                    user=request.user
                )
                results.append(result)

            transfer.status = 'COMPLETED'
            transfer.completed_at = timezone.now()
            transfer.save()

            return self.success_response(
                message='調撥完成',
                data={'transfers': results}
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=False, methods=['post'])
    def quick_transfer(self, request):
        """
        Quick stock transfer without creating transfer document.
        F05-010: 快速調撥
        """
        from_warehouse_id = request.data.get('from_warehouse_id')
        to_warehouse_id = request.data.get('to_warehouse_id')
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')

        if not all([from_warehouse_id, to_warehouse_id, product_id, quantity]):
            return self.error_response(message='缺少必要參數')

        if from_warehouse_id == to_warehouse_id:
            return self.error_response(message='來源倉庫與目標倉庫不能相同')

        try:
            result = InventorySyncService.sync_transfer_stock(
                from_warehouse_id=int(from_warehouse_id),
                to_warehouse_id=int(to_warehouse_id),
                product_id=int(product_id),
                quantity=int(quantity),
                user=request.user
            )

            return self.success_response(
                message='快速調撥完成',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))


class InventorySyncView(StandardResponseMixin, APIView):
    """
    Inventory synchronization status and operations view.
    F05-010: 庫存同步機制
    """
    permission_classes = [IsManagerOrAbove]

    def get(self, request):
        """Get inventory sync status."""
        warehouse_id = request.query_params.get('warehouse_id')
        product_id = request.query_params.get('product_id')

        if warehouse_id and product_id:
            # Get specific inventory sync status
            cached = InventorySyncService.get_cached_inventory(
                warehouse_id=int(warehouse_id),
                product_id=int(product_id)
            )
            version = InventorySyncService.get_inventory_version(
                warehouse_id=int(warehouse_id),
                product_id=int(product_id)
            )
            return self.success_response(data={
                'cached': cached,
                'version': version,
                'is_cached': cached is not None
            })

        # Get general sync statistics
        from django.db.models import Count
        stats = Inventory.objects.aggregate(
            total_records=Count('id'),
            total_warehouses=Count('warehouse', distinct=True),
            total_products=Count('product', distinct=True)
        )

        # Get low stock count
        low_stock_count = Inventory.objects.filter(
            quantity__lte=F('product__safety_stock'),
            product__status='ACTIVE'
        ).count()

        return self.success_response(data={
            'sync_status': 'active',
            'statistics': stats,
            'low_stock_count': low_stock_count,
            'channels': {
                'inventory_updates': InventorySyncService.INVENTORY_CHANNEL,
                'low_stock_alerts': InventorySyncService.LOW_STOCK_CHANNEL,
                'transfers': InventorySyncService.TRANSFER_CHANNEL
            }
        })

    def post(self, request):
        """Trigger inventory sync operations."""
        action = request.data.get('action')

        if action == 'refresh_cache':
            # Refresh cache for specific inventory
            warehouse_id = request.data.get('warehouse_id')
            product_id = request.data.get('product_id')

            if warehouse_id and product_id:
                InventorySyncService.invalidate_inventory_cache(
                    warehouse_id=int(warehouse_id),
                    product_id=int(product_id)
                )
                return self.success_response(message='快取已清除')

            return self.error_response(message='請指定倉庫和商品ID')

        elif action == 'check_alerts':
            # Check and publish all low stock alerts
            alerts = InventorySyncService.get_low_stock_alerts()
            return self.success_response(data={
                'message': f'找到 {len(alerts)} 筆低庫存警示',
                'alerts': alerts[:20]  # Return first 20
            })

        elif action == 'sync_all':
            # Sync all inventory to cache (admin operation)
            from django.db import connection
            inventories = Inventory.objects.select_related(
                'warehouse', 'product'
            ).all()[:1000]  # Limit to prevent timeout

            synced = 0
            for inv in inventories:
                cache_data = {
                    'id': inv.id,
                    'warehouse_id': inv.warehouse_id,
                    'product_id': inv.product_id,
                    'quantity': inv.quantity,
                    'available_quantity': inv.available_quantity,
                    'reserved_quantity': inv.reserved_quantity
                }
                InventorySyncService.set_cached_inventory(
                    inv.warehouse_id,
                    inv.product_id,
                    cache_data
                )
                synced += 1

            return self.success_response(data={
                'message': f'已同步 {synced} 筆庫存資料至快取',
                'synced_count': synced
            })

        return self.error_response(message='未知的操作類型')


class InventoryEventView(StandardResponseMixin, APIView):
    """
    Handle inventory events from other modules.
    F05-010: 庫存事件處理
    """

    def post(self, request):
        """Process inventory event."""
        event_type = request.data.get('event_type')
        warehouse_id = request.data.get('warehouse_id')
        items = request.data.get('items', [])
        reference_id = request.data.get('reference_id')

        if not all([event_type, warehouse_id, items]):
            return self.error_response(message='缺少必要參數')

        try:
            if event_type == 'SALE_CREATED':
                result = InventoryEventHandler.on_sale_created(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    order_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            elif event_type == 'SALE_COMPLETED':
                result = InventoryEventHandler.on_sale_completed(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    order_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            elif event_type == 'SALE_CANCELLED':
                result = InventoryEventHandler.on_sale_cancelled(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    order_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            elif event_type == 'PURCHASE_RECEIVED':
                result = InventoryEventHandler.on_purchase_received(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    receipt_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            elif event_type == 'PURCHASE_RETURNED':
                result = InventoryEventHandler.on_purchase_returned(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    return_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            elif event_type == 'CUSTOMER_RETURN':
                result = InventoryEventHandler.on_customer_return(
                    warehouse_id=int(warehouse_id),
                    items=items,
                    return_id=int(reference_id) if reference_id else None,
                    user=request.user
                )
            else:
                return self.error_response(message=f'未知的事件類型: {event_type}')

            return self.success_response(
                message=f'事件 {event_type} 處理完成',
                data=result
            )
        except Exception as e:
            return self.error_response(message=str(e))
