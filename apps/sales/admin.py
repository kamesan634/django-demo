"""
Sales admin configuration.
"""
from django.contrib import admin
from .models import Order, OrderItem, Payment, Refund, RefundItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'store', 'customer', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'order_type', 'store', 'created_at']
    search_fields = ['order_number', 'customer__name', 'customer__phone']
    ordering = ['-created_at']
    inlines = [OrderItemInline, PaymentInline]


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['refund_number', 'order', 'refund_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refund_number', 'order__order_number']
    ordering = ['-created_at']
    inlines = [RefundItemInline]
