"""
Promotions URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromotionViewSet, CouponViewSet

router = DefaultRouter()
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = [
    path('', include(router.urls)),
]
