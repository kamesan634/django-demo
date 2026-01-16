"""
Business configuration serializers.
"""
from rest_framework import serializers
from apps.core.business_models import (
    PaymentMethod,
    NumberingRule,
    ProductPrice,
    SupplierPerformance,
    AccountPayable,
    PayablePayment,
)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """PaymentMethod serializer."""

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'code', 'name', 'description', 'is_active',
            'sort_order', 'fee_rate', 'requires_reference', 'icon',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class NumberingRuleSerializer(serializers.ModelSerializer):
    """NumberingRule serializer."""
    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    reset_frequency_display = serializers.CharField(
        source='get_reset_frequency_display',
        read_only=True
    )

    class Meta:
        model = NumberingRule
        fields = [
            'id', 'document_type', 'document_type_display',
            'prefix', 'suffix', 'date_format', 'sequence_length',
            'current_sequence', 'last_reset_date',
            'reset_frequency', 'reset_frequency_display',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['current_sequence', 'last_reset_date', 'created_at', 'updated_at']


class ProductPriceSerializer(serializers.ModelSerializer):
    """ProductPrice serializer."""
    price_type_display = serializers.CharField(
        source='get_price_type_display',
        read_only=True
    )
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    customer_level_name = serializers.CharField(
        source='customer_level.name',
        read_only=True,
        default=''
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductPrice
        fields = [
            'id', 'product', 'product_name', 'price_type', 'price_type_display',
            'customer_level', 'customer_level_name', 'price', 'min_quantity',
            'valid_from', 'valid_to', 'is_active', 'is_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SupplierPerformanceSerializer(serializers.ModelSerializer):
    """SupplierPerformance serializer."""
    supplier_name = serializers.CharField(
        source='supplier.name',
        read_only=True
    )
    rating_display = serializers.CharField(
        source='get_rating_display',
        read_only=True
    )
    delivery_rate = serializers.SerializerMethodField()
    quality_rate = serializers.SerializerMethodField()

    class Meta:
        model = SupplierPerformance
        fields = [
            'id', 'supplier', 'supplier_name',
            'period_start', 'period_end',
            'total_orders', 'completed_orders', 'on_time_deliveries',
            'quality_pass_orders', 'total_amount', 'return_amount',
            'delivery_score', 'quality_score', 'price_score', 'service_score',
            'overall_score', 'rating', 'rating_display',
            'delivery_rate', 'quality_rate', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'delivery_score', 'quality_score', 'overall_score', 'rating',
            'created_at', 'updated_at'
        ]

    def get_delivery_rate(self, obj):
        if obj.total_orders > 0:
            return round(obj.on_time_deliveries / obj.total_orders * 100, 1)
        return 0

    def get_quality_rate(self, obj):
        if obj.total_orders > 0:
            return round(obj.quality_pass_orders / obj.total_orders * 100, 1)
        return 0


class AccountPayableSerializer(serializers.ModelSerializer):
    """AccountPayable serializer."""
    supplier_name = serializers.CharField(
        source='supplier.name',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    purchase_order_number = serializers.CharField(
        source='purchase_order.po_number',
        read_only=True,
        default=''
    )

    class Meta:
        model = AccountPayable
        fields = [
            'id', 'payable_number', 'supplier', 'supplier_name',
            'purchase_order', 'purchase_order_number', 'goods_receipt',
            'total_amount', 'paid_amount', 'remaining_amount',
            'invoice_date', 'due_date', 'status', 'status_display',
            'invoice_number', 'is_overdue', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['payable_number', 'paid_amount', 'created_at', 'updated_at']


class PayablePaymentSerializer(serializers.ModelSerializer):
    """PayablePayment serializer."""
    payable_number = serializers.CharField(
        source='payable.payable_number',
        read_only=True
    )

    class Meta:
        model = PayablePayment
        fields = [
            'id', 'payable', 'payable_number', 'amount',
            'payment_date', 'payment_method', 'reference_number',
            'notes', 'created_at'
        ]
        read_only_fields = ['created_at']


class AccountPayableDetailSerializer(AccountPayableSerializer):
    """AccountPayable detail serializer with payment history."""
    payments = PayablePaymentSerializer(many=True, read_only=True)

    class Meta(AccountPayableSerializer.Meta):
        fields = AccountPayableSerializer.Meta.fields + ['payments']
