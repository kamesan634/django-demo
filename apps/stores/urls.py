"""
Store URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, WarehouseViewSet

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')

urlpatterns = [
    path('', include(router.urls)),
]
