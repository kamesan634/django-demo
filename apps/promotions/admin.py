"""
Promotions admin configuration.
"""
from django.contrib import admin
from .models import Promotion, Coupon, CouponUsage


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'promotion_type', 'discount_value', 'start_date', 'end_date', 'is_active']
    list_filter = ['promotion_type', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['products', 'categories', 'stores', 'customer_levels']
    ordering = ['-created_at']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'discount_type', 'discount_value', 'used_count', 'usage_limit', 'status']
    list_filter = ['status', 'discount_type']
    search_fields = ['code', 'name']
    ordering = ['-created_at']


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'order', 'discount_amount', 'created_at']
    list_filter = ['coupon']
    ordering = ['-created_at']
