"""
Store serializers.
"""
from rest_framework import serializers
from .models import Store, Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    """Warehouse serializer."""
    store_name = serializers.CharField(source='store.name', read_only=True)
    type_display = serializers.CharField(source='get_warehouse_type_display', read_only=True)

    class Meta:
        model = Warehouse
        fields = [
            'id', 'store', 'store_name', 'name', 'code',
            'warehouse_type', 'type_display', 'address',
            'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StoreListSerializer(serializers.ModelSerializer):
    """Store list serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    manager_name = serializers.CharField(source='manager.display_name', read_only=True)
    warehouse_count = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'code', 'address', 'phone',
            'status', 'status_display', 'manager_name',
            'warehouse_count', 'created_at'
        ]

    def get_warehouse_count(self, obj):
        return obj.warehouses.filter(is_active=True).count()


class StoreDetailSerializer(serializers.ModelSerializer):
    """Store detail serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    manager_name = serializers.CharField(source='manager.display_name', read_only=True)
    warehouses = WarehouseSerializer(many=True, read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'code', 'address', 'phone', 'tax_id',
            'status', 'status_display', 'business_hours',
            'manager', 'manager_name', 'warehouses',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StoreCreateSerializer(serializers.ModelSerializer):
    """Store create serializer."""
    create_default_warehouse = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text='是否自動建立預設倉庫'
    )

    class Meta:
        model = Store
        fields = [
            'name', 'code', 'address', 'phone', 'tax_id',
            'status', 'business_hours', 'manager',
            'create_default_warehouse'
        ]

    def create(self, validated_data):
        create_warehouse = validated_data.pop('create_default_warehouse', True)
        store = super().create(validated_data)

        if create_warehouse:
            Warehouse.objects.create(
                store=store,
                name=f'{store.name} 倉庫',
                code=f'WH-{store.code}',
                warehouse_type='STORE',
                is_default=True,
                created_by=validated_data.get('created_by')
            )

        return store
