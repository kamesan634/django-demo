"""
Customer serializers.
"""
from rest_framework import serializers
from apps.core.utils import generate_code
from .models import Customer, CustomerLevel, PointsLog


class CustomerLevelSerializer(serializers.ModelSerializer):
    """CustomerLevel serializer."""
    class Meta:
        model = CustomerLevel
        fields = [
            'id', 'name', 'discount_rate', 'points_multiplier',
            'min_points', 'min_spending', 'sort_order', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PointsLogSerializer(serializers.ModelSerializer):
    """PointsLog serializer."""
    type_display = serializers.CharField(source='get_log_type_display', read_only=True)

    class Meta:
        model = PointsLog
        fields = [
            'id', 'points', 'balance', 'log_type', 'type_display',
            'description', 'reference_type', 'reference_id',
            'created_at'
        ]


class CustomerListSerializer(serializers.ModelSerializer):
    """Customer list serializer."""
    level_name = serializers.CharField(source='level.name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'member_no', 'name', 'phone', 'email',
            'level', 'level_name', 'points', 'total_spending',
            'is_active', 'created_at'
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Customer detail serializer."""
    level = CustomerLevelSerializer(read_only=True)
    level_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Customer
        fields = [
            'id', 'member_no', 'name', 'phone', 'email',
            'birthday', 'gender', 'address',
            'level', 'level_id', 'points', 'total_spending',
            'total_orders', 'note', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['member_no', 'points', 'total_spending', 'total_orders', 'created_at', 'updated_at']


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Customer create serializer."""
    class Meta:
        model = Customer
        fields = [
            'name', 'phone', 'email', 'birthday',
            'gender', 'address', 'level', 'note'
        ]

    def create(self, validated_data):
        # Generate member number
        validated_data['member_no'] = generate_code('M', 8)

        # Set default level if not provided
        if not validated_data.get('level'):
            default_level = CustomerLevel.objects.filter(is_default=True).first()
            validated_data['level'] = default_level

        return super().create(validated_data)


class AddPointsSerializer(serializers.Serializer):
    """Add points serializer."""
    points = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=200, required=False, default='')
