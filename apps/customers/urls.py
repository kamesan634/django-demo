"""
Customer URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerLevelViewSet

router = DefaultRouter()
router.register(r'customer-levels', CustomerLevelViewSet, basename='customer-level')
router.register(r'customers', CustomerViewSet, basename='customer')

urlpatterns = [
    path('', include(router.urls)),
]
