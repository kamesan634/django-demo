"""
Sales services.
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.core.utils import generate_order_number, calculate_tax
from apps.core.exceptions import InvalidOperationError
from apps.inventory.services import InventoryService
from .models import Order, OrderItem, Payment, Refund, Invoice, InvoiceItem


class SalesService:
    """Sales business logic service."""

    @staticmethod
    @transaction.atomic
    def create_order(data, user):
        """Create a new order from checkout data."""
        # Calculate totals
        subtotal = Decimal('0')
        items_data = data['items']

        for item in items_data:
            item_subtotal = (Decimal(str(item['quantity'])) *
                           Decimal(str(item['unit_price'])) -
                           Decimal(str(item.get('discount_amount', 0))))
            subtotal += item_subtotal

        discount_amount = Decimal(str(data.get('discount_amount', 0)))
        tax_amount = calculate_tax(subtotal - discount_amount)
        total_amount = subtotal - discount_amount + tax_amount

        # Create order
        order = Order.objects.create(
            order_number=generate_order_number('POS'),
            store_id=data['store_id'],
            warehouse_id=data['warehouse_id'],
            customer_id=data.get('customer_id'),
            order_type='POS',
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            points_used=data.get('points_used', 0),
            status='COMPLETED',
            note=data.get('note', ''),
            created_by=user
        )

        # Create order items and deduct inventory
        for item in items_data:
            OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                variant_id=item.get('variant_id'),
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                discount_amount=item.get('discount_amount', 0),
                subtotal=(item['quantity'] * item['unit_price'] -
                         item.get('discount_amount', 0)),
                created_by=user
            )

            # Deduct inventory
            InventoryService.adjust_stock(
                warehouse_id=data['warehouse_id'],
                product_id=item['product_id'],
                quantity=-item['quantity'],
                movement_type='SALE_OUT',
                reference_type='Order',
                reference_id=order.id,
                note=f'銷售出庫: {order.order_number}',
                user=user
            )

        # Create payments
        for payment_data in data['payments']:
            Payment.objects.create(
                order=order,
                method=payment_data['method'],
                amount=payment_data['amount'],
                reference_number=payment_data.get('reference_number', ''),
                status='COMPLETED',
                created_by=user
            )

        # Handle customer points
        if order.customer:
            # Use points
            if order.points_used > 0:
                order.customer.use_points(
                    points=order.points_used,
                    description=f'訂單 {order.order_number} 點數折抵',
                    user=user
                )

            # Earn points (1 point per 100 spent)
            points_earned = int(total_amount / 100)
            if points_earned > 0:
                order.customer.add_points(
                    points=points_earned,
                    description=f'訂單 {order.order_number} 消費獲得',
                    user=user
                )
                order.points_earned = points_earned
                order.save(update_fields=['points_earned'])

            # Update customer stats
            order.customer.total_spending += total_amount
            order.customer.total_orders += 1
            order.customer.save(update_fields=['total_spending', 'total_orders'])

        return order

    @staticmethod
    @transaction.atomic
    def void_order(order, reason, user):
        """Void an order and restore inventory."""
        if order.status == 'VOIDED':
            raise InvalidOperationError('訂單已作廢')

        if order.status == 'CANCELLED':
            raise InvalidOperationError('已取消的訂單無法作廢')

        # Restore inventory
        for item in order.items.all():
            InventoryService.adjust_stock(
                warehouse_id=order.warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity,
                movement_type='RETURN_IN',
                reference_type='Order',
                reference_id=order.id,
                note=f'訂單作廢入庫: {order.order_number}',
                user=user
            )

        # Restore customer points
        if order.customer:
            if order.points_earned > 0:
                order.customer.use_points(
                    points=order.points_earned,
                    description=f'訂單 {order.order_number} 作廢扣回',
                    user=user
                )

            if order.points_used > 0:
                order.customer.add_points(
                    points=order.points_used,
                    description=f'訂單 {order.order_number} 作廢退還',
                    user=user
                )

            order.customer.total_spending -= order.total_amount
            order.customer.total_orders -= 1
            order.customer.save(update_fields=['total_spending', 'total_orders'])

        # Update order status
        order.status = 'VOIDED'
        order.void_reason = reason
        order.voided_by = user
        order.voided_at = timezone.now()
        order.save()

        return order

    @staticmethod
    @transaction.atomic
    def complete_refund(refund, user):
        """Complete refund and return inventory."""
        # Return inventory
        for item in refund.items.all():
            order_item = item.order_item

            InventoryService.adjust_stock(
                warehouse_id=refund.order.warehouse_id,
                product_id=order_item.product_id,
                quantity=item.quantity,
                movement_type='RETURN_IN',
                reference_type='Refund',
                reference_id=refund.id,
                note=f'退貨入庫: {refund.refund_number}',
                user=user
            )

            # Update order item refunded quantity
            order_item.refunded_quantity += item.quantity
            order_item.save(update_fields=['refunded_quantity'])

        # Update refund status
        refund.status = 'COMPLETED'
        refund.completed_at = timezone.now()
        refund.save()

        return refund


class InvoiceService:
    """Invoice business logic service."""

    @staticmethod
    def generate_invoice_number():
        """Generate invoice number based on Taiwan format: XX-12345678."""
        # 簡化版發票號碼產生（實際應對接財政部電子發票平台）
        import random
        import string
        prefix = ''.join(random.choices(string.ascii_uppercase, k=2))
        number = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}-{number}"

    @staticmethod
    @transaction.atomic
    def create_invoice(order_id, invoice_type='B2C', buyer_tax_id='',
                       buyer_name='', carrier_type='', carrier_id='',
                       donation_code='', user=None):
        """Create invoice for an order."""
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            raise InvalidOperationError('找不到此訂單')

        # Check if order already has invoice
        if hasattr(order, 'invoice'):
            raise InvalidOperationError('此訂單已開立發票')

        # Check order status
        if order.status not in ['COMPLETED', 'CONFIRMED']:
            raise InvalidOperationError('訂單狀態不允許開立發票')

        # Calculate tax breakdown
        taxable_amount = order.subtotal - order.discount_amount
        tax_rate = Decimal('0.05')  # 5% 營業稅
        tax_amount = (taxable_amount * tax_rate).quantize(Decimal('1'))
        total_amount = taxable_amount + tax_amount

        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number=InvoiceService.generate_invoice_number(),
            order=order,
            invoice_type=invoice_type,
            status='PENDING',
            taxable_amount=taxable_amount,
            tax_free_amount=Decimal('0'),
            tax_amount=tax_amount,
            total_amount=total_amount,
            buyer_tax_id=buyer_tax_id,
            buyer_name=buyer_name,
            carrier_type=carrier_type,
            carrier_id=carrier_id,
            donation_code=donation_code,
            created_by=user
        )

        # Create invoice items from order items
        for order_item in order.items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                description=order_item.product.name,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                amount=order_item.subtotal,
                created_by=user
            )

        return invoice

    @staticmethod
    @transaction.atomic
    def issue_invoice(invoice, user=None):
        """Issue (finalize) an invoice."""
        if invoice.status != 'PENDING':
            raise InvalidOperationError('發票狀態不允許開立')

        invoice.status = 'ISSUED'
        invoice.issued_at = timezone.now()
        invoice.updated_by = user
        invoice.save()

        return invoice

    @staticmethod
    @transaction.atomic
    def void_invoice(invoice, reason, user=None):
        """Void an issued invoice."""
        if invoice.status != 'ISSUED':
            raise InvalidOperationError('只有已開立的發票可以作廢')

        invoice.status = 'VOIDED'
        invoice.void_reason = reason
        invoice.voided_at = timezone.now()
        invoice.updated_by = user
        invoice.save()

        return invoice
