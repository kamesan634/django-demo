"""
Inventory URLs.
F04-001 ~ F04-007: 庫存管理功能
F05-010: 庫存同步機制
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryViewSet,
    InventoryMovementViewSet,
    StockCountViewSet,
    StockTransferViewSet,
    InventorySyncView,
    InventoryEventView,
)

router = DefaultRouter()
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'inventory-movements', InventoryMovementViewSet, basename='inventory-movement')
router.register(r'stock-counts', StockCountViewSet, basename='stock-count')
router.register(r'stock-transfers', StockTransferViewSet, basename='stock-transfer')

urlpatterns = [
    path('', include(router.urls)),

    # Inventory sync endpoints (F05-010)
    path('inventory/sync/', InventorySyncView.as_view(), name='inventory-sync'),
    path('inventory/events/', InventoryEventView.as_view(), name='inventory-events'),
]
