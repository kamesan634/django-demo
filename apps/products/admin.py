"""
Product admin configuration.
"""
from django.contrib import admin
from .models import Category, Product, ProductVariant, ProductBarcode, Unit, TaxType


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']
    ordering = ['sort_order', 'name']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol']
    search_fields = ['name']


@admin.register(TaxType)
class TaxTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'rate', 'is_default']
    list_filter = ['is_default']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductBarcodeInline(admin.TabularInline):
    model = ProductBarcode
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'sale_price', 'cost_price', 'status']
    list_filter = ['status', 'category']
    search_fields = ['name', 'sku']
    ordering = ['-created_at']
    inlines = [ProductVariantInline, ProductBarcodeInline]
