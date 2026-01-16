"""
Store views.
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count

from apps.core.views import BaseViewSet
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from .models import Store, Warehouse
from .serializers import (
    StoreListSerializer,
    StoreDetailSerializer,
    StoreCreateSerializer,
    WarehouseSerializer,
)


class StoreViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """Store management ViewSet."""
    queryset = Store.objects.all()
    serializer_class = StoreListSerializer
    serializer_classes = {
        'list': StoreListSerializer,
        'retrieve': StoreDetailSerializer,
        'create': StoreCreateSerializer,
        'update': StoreDetailSerializer,
        'partial_update': StoreDetailSerializer,
    }
    search_fields = ['name', 'code', 'address']
    filterset_fields = ['status']
    ordering_fields = ['name', 'code', 'created_at']

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get store summary (today's sales, orders, etc.)."""
        store = self.get_object()

        # Placeholder - implement actual summary logic
        summary_data = {
            'store_id': store.id,
            'store_name': store.name,
            'today_sales': 0,
            'today_orders': 0,
            'inventory_value': 0,
            'low_stock_items': 0,
        }

        return self.success_response(data=summary_data)

    @action(detail=True, methods=['get'])
    def warehouses(self, request, pk=None):
        """Get store warehouses."""
        store = self.get_object()
        warehouses = store.warehouses.filter(is_active=True)
        serializer = WarehouseSerializer(warehouses, many=True)
        return self.success_response(data=serializer.data)


class WarehouseViewSet(BaseViewSet):
    """Warehouse management ViewSet."""
    queryset = Warehouse.objects.select_related('store').all()
    serializer_class = WarehouseSerializer
    search_fields = ['name', 'code']
    filterset_fields = ['store', 'warehouse_type', 'is_active']
    ordering_fields = ['name', 'code', 'created_at']

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set warehouse as default for its store."""
        warehouse = self.get_object()
        warehouse.is_default = True
        warehouse.save()
        return Response({
            'success': True,
            'message': f'{warehouse.name} 已設為預設倉庫'
        })
