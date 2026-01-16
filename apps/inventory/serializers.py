"""
Inventory serializers.
"""
from rest_framework import serializers
from .models import (
    Inventory, InventoryMovement,
    StockCount, StockCountItem,
    StockTransfer, StockTransferItem
)


class InventorySerializer(serializers.ModelSerializer):
    """Inventory serializer."""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'warehouse', 'warehouse_name',
            'product', 'product_name', 'product_sku',
            'quantity', 'available_quantity', 'reserved_quantity',
            'updated_at'
        ]


class InventoryMovementSerializer(serializers.ModelSerializer):
    """InventoryMovement serializer."""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    type_display = serializers.CharField(source='get_movement_type_display', read_only=True)

    class Meta:
        model = InventoryMovement
        fields = [
            'id', 'warehouse', 'warehouse_name',
            'product', 'product_name',
            'movement_type', 'type_display',
            'quantity', 'balance',
            'reference_type', 'reference_id', 'note',
            'created_by', 'created_at'
        ]


class StockAdjustmentSerializer(serializers.Serializer):
    """Stock adjustment request serializer."""
    warehouse_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    adjustment_type = serializers.ChoiceField(choices=['IN', 'OUT'])
    note = serializers.CharField(max_length=200, required=False, default='')


class StockCountItemSerializer(serializers.ModelSerializer):
    """StockCountItem serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = StockCountItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'system_quantity', 'actual_quantity', 'difference'
        ]


class StockCountSerializer(serializers.ModelSerializer):
    """StockCount serializer."""
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = StockCountItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockCount
        fields = [
            'id', 'count_number', 'warehouse', 'warehouse_name',
            'status', 'status_display', 'count_date',
            'completed_at', 'note', 'items',
            'created_by', 'created_at'
        ]
        read_only_fields = ['count_number', 'completed_at']


class StockTransferItemSerializer(serializers.ModelSerializer):
    """StockTransferItem serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = StockTransferItem
        fields = ['id', 'product', 'product_name', 'product_sku', 'quantity']


class StockTransferSerializer(serializers.ModelSerializer):
    """StockTransfer serializer."""
    from_warehouse_name = serializers.CharField(source='from_warehouse.name', read_only=True)
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = StockTransferItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number',
            'from_warehouse', 'from_warehouse_name',
            'to_warehouse', 'to_warehouse_name',
            'status', 'status_display', 'transfer_date',
            'completed_at', 'note', 'items',
            'created_by', 'created_at'
        ]
        read_only_fields = ['transfer_number', 'completed_at']
