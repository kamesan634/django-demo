"""
Purchasing admin configuration.
"""
from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_name', 'phone', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'contact_name']
    ordering = ['name']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['subtotal', 'received_quantity']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'warehouse', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'supplier', 'warehouse']
    search_fields = ['po_number', 'supplier__name']
    ordering = ['-created_at']
    inlines = [PurchaseOrderItemInline]


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'purchase_order', 'status', 'receipt_date', 'created_at']
    list_filter = ['status']
    ordering = ['-created_at']
    inlines = [GoodsReceiptItemInline]
