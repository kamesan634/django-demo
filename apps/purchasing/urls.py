"""
Purchasing URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, PurchaseOrderViewSet, PurchaseReturnViewSet, SupplierPriceViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'purchase-returns', PurchaseReturnViewSet, basename='purchase-return')
router.register(r'supplier-prices', SupplierPriceViewSet, basename='supplier-price')

urlpatterns = [
    path('', include(router.urls)),
]
