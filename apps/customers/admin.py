"""
Customer admin configuration.
"""
from django.contrib import admin
from .models import Customer, CustomerLevel, PointsLog


@admin.register(CustomerLevel)
class CustomerLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_rate', 'points_multiplier', 'min_points', 'is_default']
    list_filter = ['is_default']
    ordering = ['sort_order']


class PointsLogInline(admin.TabularInline):
    model = PointsLog
    extra = 0
    readonly_fields = ['points', 'balance', 'log_type', 'description', 'created_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['member_no', 'name', 'phone', 'level', 'points', 'total_spending', 'is_active']
    list_filter = ['level', 'is_active']
    search_fields = ['member_no', 'name', 'phone', 'email']
    ordering = ['-created_at']
    inlines = [PointsLogInline]
