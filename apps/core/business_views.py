"""
Business configuration views.
F02-003: 付款方式管理
F02-006: 編號規則設定
F03-003: 價格管理
F07-008: 應付帳款管理
F07-009: 供應商績效評分
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta

from apps.core.views import BaseViewSet
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsAdminUser, IsManagerOrAbove
from apps.core.business_models import (
    PaymentMethod,
    NumberingRule,
    ProductPrice,
    SupplierPerformance,
    AccountPayable,
    PayablePayment,
)
from apps.core.business_serializers import (
    PaymentMethodSerializer,
    NumberingRuleSerializer,
    ProductPriceSerializer,
    SupplierPerformanceSerializer,
    AccountPayableSerializer,
    AccountPayableDetailSerializer,
    PayablePaymentSerializer,
)


class PaymentMethodViewSet(StandardResponseMixin, BaseViewSet):
    """
    Payment method management ViewSet.
    F02-003: 付款方式管理
    """
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    search_fields = ['name', 'code']
    filterset_fields = ['is_active']
    ordering_fields = ['sort_order', 'name']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active payment methods."""
        methods = self.get_queryset().filter(is_active=True).order_by('sort_order')
        serializer = self.get_serializer(methods, many=True)
        return self.success_response(data=serializer.data)


class NumberingRuleViewSet(StandardResponseMixin, BaseViewSet):
    """
    Numbering rule management ViewSet.
    F02-006: 編號規則設定
    """
    queryset = NumberingRule.objects.all()
    serializer_class = NumberingRuleSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['document_type', 'is_active']

    @action(detail=False, methods=['get'])
    def preview(self, request):
        """Preview next number for a document type."""
        document_type = request.query_params.get('document_type')
        if not document_type:
            return self.error_response(message='請指定單據類型')

        try:
            rule = NumberingRule.objects.get(document_type=document_type)
            # Generate preview without saving
            today = timezone.now().date()
            next_seq = rule.current_sequence + 1
            date_part = rule._format_date(today)
            seq_part = str(next_seq).zfill(rule.sequence_length)
            preview = f'{rule.prefix}{date_part}{seq_part}{rule.suffix}'

            return self.success_response(data={
                'preview': preview,
                'current_sequence': rule.current_sequence,
                'next_sequence': next_seq
            })
        except NumberingRule.DoesNotExist:
            # Return default preview
            defaults = NumberingRule._get_default_config(document_type)
            today = timezone.now().date()
            preview = f"{defaults.get('prefix', '')}{today.strftime('%Y%m%d')}0001"
            return self.success_response(data={
                'preview': preview,
                'current_sequence': 0,
                'next_sequence': 1,
                'is_default': True
            })

    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """Reset sequence number."""
        rule = self.get_object()
        rule.current_sequence = 0
        rule.last_reset_date = timezone.now().date()
        rule.save(update_fields=['current_sequence', 'last_reset_date'])
        return self.success_response(message='流水號已重置')


class ProductPriceViewSet(StandardResponseMixin, BaseViewSet):
    """
    Product price management ViewSet.
    F03-003: 價格管理
    """
    queryset = ProductPrice.objects.select_related('product', 'customer_level').all()
    serializer_class = ProductPriceSerializer
    filterset_fields = ['product', 'price_type', 'customer_level', 'is_active']
    ordering_fields = ['product', 'price', 'valid_from']

    @action(detail=False, methods=['get'])
    def for_product(self, request):
        """Get all prices for a specific product."""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return self.error_response(message='請指定商品ID')

        prices = self.get_queryset().filter(product_id=product_id)
        serializer = self.get_serializer(prices, many=True)
        return self.success_response(data=serializer.data)

    @action(detail=False, methods=['get'])
    def best_price(self, request):
        """Get best price for a product."""
        product_id = request.query_params.get('product_id')
        customer_level_id = request.query_params.get('customer_level_id')
        quantity = int(request.query_params.get('quantity', 1))

        if not product_id:
            return self.error_response(message='請指定商品ID')

        best = ProductPrice.get_best_price(
            product_id=product_id,
            customer_level_id=customer_level_id,
            quantity=quantity
        )

        if best:
            serializer = self.get_serializer(best)
            return self.success_response(data=serializer.data)
        else:
            return self.error_response(
                message='找不到適用的價格',
                status_code=status.HTTP_404_NOT_FOUND
            )


class SupplierPerformanceViewSet(StandardResponseMixin, BaseViewSet):
    """
    Supplier performance management ViewSet.
    F07-009: 供應商績效評分
    """
    queryset = SupplierPerformance.objects.select_related('supplier').all()
    serializer_class = SupplierPerformanceSerializer
    permission_classes = [IsManagerOrAbove]
    filterset_fields = ['supplier', 'rating']
    ordering_fields = ['period_end', 'overall_score']

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Calculate supplier performance for a period.
        """
        from apps.purchasing.models import PurchaseOrder, GoodsReceipt, PurchaseReturn

        supplier_id = request.data.get('supplier_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')

        if not all([supplier_id, period_start, period_end]):
            return self.error_response(message='請提供供應商ID和評估期間')

        # Get purchase orders in period
        orders = PurchaseOrder.objects.filter(
            supplier_id=supplier_id,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )

        total_orders = orders.count()
        completed_orders = orders.filter(status='COMPLETED').count()

        # Get goods receipts for on-time delivery calculation
        receipts = GoodsReceipt.objects.filter(
            purchase_order__supplier_id=supplier_id,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        on_time = receipts.filter(
            created_at__date__lte=F('purchase_order__expected_date')
        ).count() if receipts.exists() else 0

        # Get returns for quality calculation
        returns = PurchaseReturn.objects.filter(
            supplier_id=supplier_id,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        return_amount = returns.aggregate(total=Sum('total_amount'))['total'] or 0

        # Total amount
        total_amount = orders.aggregate(total=Sum('total_amount'))['total'] or 0

        # Create or update performance record
        performance, created = SupplierPerformance.objects.update_or_create(
            supplier_id=supplier_id,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'on_time_deliveries': on_time,
                'quality_pass_orders': completed_orders - returns.count(),
                'total_amount': total_amount,
                'return_amount': return_amount,
                'price_score': 80,  # Default, can be manually adjusted
                'service_score': 80,  # Default, can be manually adjusted
            }
        )

        serializer = self.get_serializer(performance)
        return self.success_response(
            message='績效計算完成',
            data=serializer.data
        )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get performance summary for all suppliers."""
        # Get latest performance for each supplier
        from django.db.models import Subquery, OuterRef

        latest_dates = SupplierPerformance.objects.filter(
            supplier=OuterRef('supplier')
        ).order_by('-period_end').values('period_end')[:1]

        performances = SupplierPerformance.objects.filter(
            period_end=Subquery(latest_dates)
        ).select_related('supplier')

        summary = {
            'total_suppliers': performances.count(),
            'by_rating': {},
            'suppliers': []
        }

        # Count by rating
        for rating, label in SupplierPerformance.RATING_CHOICES:
            count = performances.filter(rating=rating).count()
            summary['by_rating'][rating] = {'label': label, 'count': count}

        # Get top/bottom suppliers
        for perf in performances.order_by('-overall_score')[:10]:
            summary['suppliers'].append({
                'supplier_id': perf.supplier_id,
                'supplier_name': perf.supplier.name,
                'overall_score': float(perf.overall_score),
                'rating': perf.rating,
                'period': f'{perf.period_start} ~ {perf.period_end}'
            })

        return self.success_response(data=summary)


class AccountPayableViewSet(StandardResponseMixin, BaseViewSet):
    """
    Accounts payable management ViewSet.
    F07-008: 應付帳款管理
    """
    queryset = AccountPayable.objects.select_related(
        'supplier', 'purchase_order', 'goods_receipt'
    ).all()
    serializer_class = AccountPayableSerializer
    filterset_fields = ['supplier', 'status']
    search_fields = ['payable_number', 'invoice_number']
    ordering_fields = ['due_date', 'total_amount', 'created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AccountPayableDetailSerializer
        return AccountPayableSerializer

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payables summary."""
        queryset = self.get_queryset()

        # By status
        status_summary = {}
        for code, label in AccountPayable.STATUS_CHOICES:
            agg = queryset.filter(status=code).aggregate(
                count=Count('id'),
                total=Sum('total_amount'),
                remaining=Sum('total_amount') - Sum('paid_amount')
            )
            status_summary[code] = {
                'label': label,
                'count': agg['count'] or 0,
                'total': float(agg['total'] or 0),
                'remaining': float(agg['remaining'] or 0)
            }

        # Overdue
        today = timezone.now().date()
        overdue = queryset.filter(
            due_date__lt=today,
            status__in=['PENDING', 'PARTIAL']
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount') - Sum('paid_amount')
        )

        # Due this week
        week_end = today + timedelta(days=7)
        due_soon = queryset.filter(
            due_date__gte=today,
            due_date__lte=week_end,
            status__in=['PENDING', 'PARTIAL']
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount') - Sum('paid_amount')
        )

        return self.success_response(data={
            'by_status': status_summary,
            'overdue': {
                'count': overdue['count'] or 0,
                'total': float(overdue['total'] or 0)
            },
            'due_this_week': {
                'count': due_soon['count'] or 0,
                'total': float(due_soon['total'] or 0)
            }
        })

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Record a payment for this payable."""
        payable = self.get_object()

        amount = request.data.get('amount')
        payment_date = request.data.get('payment_date', timezone.now().date())
        payment_method = request.data.get('payment_method', 'BANK_TRANSFER')
        reference_number = request.data.get('reference_number', '')
        notes = request.data.get('notes', '')

        if not amount:
            return self.error_response(message='請提供付款金額')

        try:
            amount = float(amount)
        except ValueError:
            return self.error_response(message='金額格式錯誤')

        if amount > payable.remaining_amount:
            return self.error_response(
                message=f'付款金額超過應付餘額 (${payable.remaining_amount})'
            )

        payment = PayablePayment.objects.create(
            payable=payable,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=request.user
        )

        serializer = PayablePaymentSerializer(payment)
        return self.created_response(
            message='付款記錄已建立',
            data=serializer.data
        )

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get payment history for this payable."""
        payable = self.get_object()
        payments = payable.payments.order_by('-payment_date')
        serializer = PayablePaymentSerializer(payments, many=True)
        return self.success_response(data=serializer.data)
