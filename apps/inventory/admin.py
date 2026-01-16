"""
Inventory admin configuration.
"""
from django.contrib import admin
from .models import (
    Inventory, InventoryMovement,
    StockCount, StockCountItem,
    StockTransfer, StockTransferItem
)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity', 'available_quantity', 'reserved_quantity']
    list_filter = ['warehouse']
    search_fields = ['product__name', 'product__sku']


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'movement_type', 'quantity', 'balance', 'created_at']
    list_filter = ['movement_type', 'warehouse', 'created_at']
    search_fields = ['product__name', 'product__sku']
    ordering = ['-created_at']


class StockCountItemInline(admin.TabularInline):
    model = StockCountItem
    extra = 1


@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
    list_display = ['count_number', 'warehouse', 'status', 'count_date', 'created_at']
    list_filter = ['status', 'warehouse']
    ordering = ['-created_at']
    inlines = [StockCountItemInline]


class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ['transfer_number', 'from_warehouse', 'to_warehouse', 'status', 'transfer_date']
    list_filter = ['status', 'from_warehouse', 'to_warehouse']
    ordering = ['-created_at']
    inlines = [StockTransferItemInline]
