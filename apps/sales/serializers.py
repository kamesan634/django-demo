"""
Sales serializers.
"""
from rest_framework import serializers
from .models import Order, OrderItem, Payment, Refund, RefundItem, Invoice, InvoiceItem


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer."""
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'method', 'method_display', 'amount',
            'status', 'reference_number', 'created_at'
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """OrderItem serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True, default='')

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'variant', 'variant_name',
            'quantity', 'unit_price', 'discount_amount', 'subtotal',
            'refunded_quantity'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Order list serializer."""
    store_name = serializers.CharField(source='store.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'store', 'store_name',
            'customer', 'customer_name',
            'order_type', 'type_display',
            'total_amount', 'status', 'status_display',
            'item_count', 'created_at'
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Order detail serializer."""
    store_name = serializers.CharField(source='store.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number',
            'store', 'store_name', 'warehouse', 'warehouse_name',
            'customer', 'customer_name',
            'order_type', 'type_display',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'points_earned', 'points_used',
            'status', 'status_display', 'note',
            'void_reason', 'voided_at',
            'items', 'payments',
            'created_by', 'created_at', 'updated_at'
        ]


class CheckoutItemSerializer(serializers.Serializer):
    """Checkout item serializer."""
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)


class CheckoutPaymentSerializer(serializers.Serializer):
    """Checkout payment serializer."""
    method = serializers.ChoiceField(choices=Payment.METHOD_CHOICES)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reference_number = serializers.CharField(max_length=100, required=False, default='')


class CheckoutSerializer(serializers.Serializer):
    """POS checkout serializer."""
    store_id = serializers.IntegerField()
    warehouse_id = serializers.IntegerField()
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    items = CheckoutItemSerializer(many=True)
    payments = CheckoutPaymentSerializer(many=True)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    points_used = serializers.IntegerField(default=0, min_value=0)
    note = serializers.CharField(max_length=500, required=False, default='')


class VoidOrderSerializer(serializers.Serializer):
    """Void order serializer."""
    reason = serializers.CharField(max_length=500)


class RefundItemSerializer(serializers.ModelSerializer):
    """RefundItem serializer."""
    product_name = serializers.CharField(source='order_item.product.name', read_only=True)

    class Meta:
        model = RefundItem
        fields = ['id', 'order_item', 'product_name', 'quantity']


class RefundSerializer(serializers.ModelSerializer):
    """Refund serializer."""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = RefundItemSerializer(many=True, read_only=True)

    class Meta:
        model = Refund
        fields = [
            'id', 'refund_number', 'order', 'order_number',
            'refund_amount', 'reason', 'status', 'status_display',
            'items', 'completed_at', 'created_at'
        ]
        read_only_fields = ['refund_number', 'status', 'completed_at', 'created_at']


# ==========================================
# Invoice Serializers
# ==========================================
class InvoiceItemSerializer(serializers.ModelSerializer):
    """Invoice item serializer."""

    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount']
        read_only_fields = ['amount']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Invoice list serializer."""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'order', 'order_number',
            'invoice_type', 'type_display', 'status', 'status_display',
            'total_amount', 'issued_at', 'created_at'
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Invoice detail serializer."""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'order', 'order_number',
            'invoice_type', 'type_display', 'status', 'status_display',
            'taxable_amount', 'tax_free_amount', 'tax_amount', 'total_amount',
            'buyer_tax_id', 'buyer_name',
            'carrier_type', 'carrier_id', 'donation_code',
            'issued_at', 'void_reason', 'voided_at',
            'items', 'created_at', 'updated_at'
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    """Invoice create serializer."""
    order_id = serializers.IntegerField()
    invoice_type = serializers.ChoiceField(choices=Invoice.TYPE_CHOICES, default='B2C')
    buyer_tax_id = serializers.CharField(max_length=20, required=False, default='')
    buyer_name = serializers.CharField(max_length=100, required=False, default='')
    carrier_type = serializers.CharField(max_length=20, required=False, default='')
    carrier_id = serializers.CharField(max_length=100, required=False, default='')
    donation_code = serializers.CharField(max_length=10, required=False, default='')


class InvoiceVoidSerializer(serializers.Serializer):
    """Invoice void serializer."""
    reason = serializers.CharField(max_length=500)
