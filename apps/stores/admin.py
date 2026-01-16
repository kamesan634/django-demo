"""
Store admin configuration.
"""
from django.contrib import admin
from .models import Store, Warehouse


class WarehouseInline(admin.TabularInline):
    model = Warehouse
    extra = 1


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'phone', 'status', 'manager', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'code', 'address']
    ordering = ['code']
    inlines = [WarehouseInline]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'store', 'warehouse_type', 'is_default', 'is_active']
    list_filter = ['warehouse_type', 'is_active', 'store']
    search_fields = ['name', 'code']
    ordering = ['store', 'code']
