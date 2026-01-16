"""
Sales views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from apps.core.views import BaseViewSet, ReadOnlyViewSet
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from apps.core.utils import generate_order_number
from .models import Order, OrderItem, Payment, Refund, Invoice
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CheckoutSerializer,
    VoidOrderSerializer,
    RefundSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    InvoiceVoidSerializer,
)
from .services import SalesService, InvoiceService


class OrderViewSet(MultiSerializerMixin, StandardResponseMixin, ReadOnlyViewSet):
    """Order query ViewSet (read-only, use POS for create)."""
    queryset = Order.objects.select_related('store', 'warehouse', 'customer').all()
    serializer_class = OrderListSerializer
    serializer_classes = {
        'list': OrderListSerializer,
        'retrieve': OrderDetailSerializer,
    }
    filterset_fields = ['store', 'status', 'order_type', 'customer']
    search_fields = ['order_number', 'customer__name', 'customer__phone']
    ordering_fields = ['created_at', 'total_amount']


class POSViewSet(StandardResponseMixin, viewsets.ViewSet):
    """POS operations ViewSet."""

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Process POS checkout."""
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = SalesService.create_order(
                data=serializer.validated_data,
                user=request.user
            )
            return self.success_response(
                message='結帳成功',
                data=OrderDetailSerializer(order).data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['post'], url_path='void')
    def void_order(self, request, pk=None):
        """Void an order."""
        serializer = VoidOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.get(pk=pk)
            SalesService.void_order(
                order=order,
                reason=serializer.validated_data['reason'],
                user=request.user
            )
            return self.success_response(message='訂單已作廢')
        except Order.DoesNotExist:
            return self.error_response(
                message='找不到此訂單',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return self.error_response(message=str(e))


class RefundViewSet(StandardResponseMixin, BaseViewSet):
    """Refund management ViewSet."""
    queryset = Refund.objects.select_related('order').prefetch_related('items')
    serializer_class = RefundSerializer
    filterset_fields = ['status', 'order']
    ordering_fields = ['created_at']

    def perform_create(self, serializer):
        serializer.save(
            refund_number=generate_order_number('RF'),
            created_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete refund and return stock."""
        refund = self.get_object()

        if refund.status != 'PENDING':
            return self.error_response(message='退貨單狀態不正確')

        try:
            SalesService.complete_refund(refund=refund, user=request.user)
            return self.success_response(message='退貨處理完成')
        except Exception as e:
            return self.error_response(message=str(e))


class InvoiceViewSet(MultiSerializerMixin, StandardResponseMixin, ReadOnlyViewSet):
    """Invoice management ViewSet."""
    queryset = Invoice.objects.select_related('order').prefetch_related('items')
    serializer_class = InvoiceListSerializer
    serializer_classes = {
        'list': InvoiceListSerializer,
        'retrieve': InvoiceDetailSerializer,
    }
    filterset_fields = ['status', 'invoice_type', 'order']
    search_fields = ['invoice_number', 'order__order_number', 'buyer_name', 'buyer_tax_id']
    ordering_fields = ['created_at', 'issued_at', 'total_amount']

    @action(detail=False, methods=['post'])
    def create_invoice(self, request):
        """Create invoice for an order."""
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = InvoiceService.create_invoice(
                order_id=serializer.validated_data['order_id'],
                invoice_type=serializer.validated_data.get('invoice_type', 'B2C'),
                buyer_tax_id=serializer.validated_data.get('buyer_tax_id', ''),
                buyer_name=serializer.validated_data.get('buyer_name', ''),
                carrier_type=serializer.validated_data.get('carrier_type', ''),
                carrier_id=serializer.validated_data.get('carrier_id', ''),
                donation_code=serializer.validated_data.get('donation_code', ''),
                user=request.user
            )
            return self.success_response(
                message='發票建立成功',
                data=InvoiceDetailSerializer(invoice).data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Issue (finalize) an invoice."""
        invoice = self.get_object()

        try:
            InvoiceService.issue_invoice(invoice=invoice, user=request.user)
            return self.success_response(
                message='發票已開立',
                data=InvoiceDetailSerializer(invoice).data
            )
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void an issued invoice."""
        serializer = InvoiceVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = self.get_object()

        try:
            InvoiceService.void_invoice(
                invoice=invoice,
                reason=serializer.validated_data['reason'],
                user=request.user
            )
            return self.success_response(message='發票已作廢')
        except Exception as e:
            return self.error_response(message=str(e))
