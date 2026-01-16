"""
Promotions serializers.
"""
from rest_framework import serializers
from .models import Promotion, Coupon


class PromotionSerializer(serializers.ModelSerializer):
    """Promotion serializer."""
    type_display = serializers.CharField(source='get_promotion_type_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description',
            'promotion_type', 'type_display',
            'discount_value', 'min_purchase',
            'buy_quantity', 'get_quantity',
            'start_date', 'end_date', 'is_active', 'is_valid',
            'products', 'categories', 'stores', 'customer_levels',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CouponSerializer(serializers.ModelSerializer):
    """Coupon serializer."""
    type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    remaining_uses = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'name',
            'discount_type', 'type_display',
            'discount_value', 'min_purchase', 'max_discount',
            'usage_limit', 'used_count', 'remaining_uses',
            'start_date', 'end_date',
            'status', 'status_display', 'is_valid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['used_count', 'created_at', 'updated_at']

    def get_remaining_uses(self, obj):
        if obj.usage_limit == 0:
            return -1  # Unlimited
        return max(0, obj.usage_limit - obj.used_count)


class CalculateDiscountItemSerializer(serializers.Serializer):
    """Item for discount calculation."""
    product_id = serializers.IntegerField()
    category_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CalculateDiscountSerializer(serializers.Serializer):
    """Calculate discount request serializer."""
    items = CalculateDiscountItemSerializer(many=True)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    store_id = serializers.IntegerField(required=False, allow_null=True)
    coupon_code = serializers.CharField(max_length=30, required=False, allow_blank=True)


class ValidateCouponSerializer(serializers.Serializer):
    """Validate coupon request serializer."""
    code = serializers.CharField(max_length=30)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
