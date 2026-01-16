"""
Purchasing serializers.
"""
from rest_framework import serializers
from .models import (
    Supplier, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem,
    PurchaseReturn, PurchaseReturnItem,
    SupplierPrice
)


class SupplierSerializer(serializers.ModelSerializer):
    """Supplier serializer."""
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'contact_name', 'phone', 'email',
            'tax_id', 'address', 'payment_terms', 'note', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """PurchaseOrderItem serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'quantity', 'received_quantity', 'remaining_quantity',
            'unit_price', 'subtotal'
        ]
        read_only_fields = ['subtotal', 'received_quantity']

    def get_remaining_quantity(self, obj):
        return obj.quantity - obj.received_quantity


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """PurchaseOrder list serializer."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name',
            'warehouse', 'warehouse_name',
            'status', 'status_display', 'total_amount',
            'expected_date', 'item_count', 'created_at'
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    """PurchaseOrder detail serializer."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.display_name', read_only=True, default='')
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number',
            'supplier', 'supplier_name',
            'warehouse', 'warehouse_name',
            'status', 'status_display', 'total_amount',
            'expected_date', 'submitted_at',
            'approved_by', 'approved_by_name', 'approved_at',
            'note', 'items',
            'created_by', 'created_at', 'updated_at'
        ]


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    """PurchaseOrder create serializer."""
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'warehouse', 'expected_date', 'note', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        from apps.core.utils import generate_order_number

        po = PurchaseOrder.objects.create(
            po_number=generate_order_number('PO'),
            **validated_data
        )

        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=po, **item_data)

        po.calculate_total()
        return po


class ReceiveItemSerializer(serializers.Serializer):
    """Receive item serializer."""
    po_item_id = serializers.IntegerField()
    received_quantity = serializers.IntegerField(min_value=1)


class ReceiveSerializer(serializers.Serializer):
    """Receive goods serializer."""
    items = ReceiveItemSerializer(many=True)
    note = serializers.CharField(max_length=500, required=False, default='')


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    """GoodsReceiptItem serializer."""
    product_name = serializers.CharField(source='po_item.product.name', read_only=True)

    class Meta:
        model = GoodsReceiptItem
        fields = ['id', 'po_item', 'product_name', 'received_quantity']


class GoodsReceiptSerializer(serializers.ModelSerializer):
    """GoodsReceipt serializer."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = GoodsReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            'id', 'receipt_number', 'purchase_order', 'po_number',
            'status', 'status_display', 'receipt_date', 'note',
            'items', 'created_at'
        ]


# ==========================================
# Purchase Return Serializers
# ==========================================
class PurchaseReturnItemSerializer(serializers.ModelSerializer):
    """PurchaseReturnItem serializer."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)

    class Meta:
        model = PurchaseReturnItem
        fields = [
            'id', 'po_item', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'subtotal', 'reason'
        ]
        read_only_fields = ['subtotal']


class PurchaseReturnListSerializer(serializers.ModelSerializer):
    """PurchaseReturn list serializer."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseReturn
        fields = [
            'id', 'return_number', 'purchase_order', 'po_number',
            'supplier', 'supplier_name', 'warehouse', 'warehouse_name',
            'status', 'status_display', 'reason', 'reason_display',
            'total_amount', 'return_date', 'item_count', 'created_at'
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class PurchaseReturnDetailSerializer(serializers.ModelSerializer):
    """PurchaseReturn detail serializer."""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.display_name', read_only=True, default='')
    items = PurchaseReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReturn
        fields = [
            'id', 'return_number',
            'purchase_order', 'po_number',
            'supplier', 'supplier_name',
            'warehouse', 'warehouse_name',
            'status', 'status_display',
            'reason', 'reason_display', 'reason_detail',
            'total_amount', 'return_date',
            'approved_by', 'approved_by_name', 'approved_at',
            'completed_at', 'note', 'items',
            'created_by', 'created_at', 'updated_at'
        ]


class PurchaseReturnCreateItemSerializer(serializers.Serializer):
    """Create return item serializer."""
    po_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=200, required=False, default='')


class PurchaseReturnCreateSerializer(serializers.Serializer):
    """PurchaseReturn create serializer."""
    purchase_order_id = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=PurchaseReturn.REASON_CHOICES)
    reason_detail = serializers.CharField(max_length=500, required=False, default='')
    return_date = serializers.DateField()
    note = serializers.CharField(max_length=500, required=False, default='')
    items = PurchaseReturnCreateItemSerializer(many=True)


# ==========================================
# Supplier Price Serializers
# ==========================================
class SupplierPriceSerializer(serializers.ModelSerializer):
    """SupplierPrice serializer."""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupplierPrice
        fields = [
            'id', 'supplier', 'supplier_name',
            'product', 'product_name', 'product_sku',
            'unit_price', 'min_quantity', 'lead_time_days',
            'effective_from', 'effective_to', 'is_preferred',
            'is_active', 'note',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SupplierPriceCompareSerializer(serializers.Serializer):
    """Serializer for comparing supplier prices."""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    product_sku = serializers.CharField()
    suppliers = serializers.ListField(child=serializers.DictField())
