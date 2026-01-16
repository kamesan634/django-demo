"""
Product URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, UnitViewSet, TaxTypeViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'units', UnitViewSet, basename='unit')
router.register(r'tax-types', TaxTypeViewSet, basename='tax-type')

urlpatterns = [
    path('', include(router.urls)),
]
