"""
Sales URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, POSViewSet, RefundViewSet, InvoiceViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'pos', POSViewSet, basename='pos')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
