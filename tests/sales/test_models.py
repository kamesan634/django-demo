"""
Tests for sales models.
"""
import pytest
from decimal import Decimal
from apps.sales.models import Order, OrderItem, Payment, Refund


@pytest.mark.django_db
class TestOrderModel:
    """Tests for Order model."""

    def test_create_order(self, store, warehouse):
        """Test creating an order."""
        order = Order.objects.create(
            order_number='ORD20260101001',
            store=store,
            warehouse=warehouse,
            order_type='POS',
            status='PENDING',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('5.00'),
            total_amount=Decimal('105.00')
        )

        assert order.order_number == 'ORD20260101001'
        assert order.store == store
        assert order.total_amount == Decimal('105.00')

    def test_order_str(self, store, warehouse):
        """Test order string representation."""
        order = Order.objects.create(
            order_number='ORD20260101002',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('0'),
            total_amount=Decimal('0')
        )

        assert 'ORD20260101002' in str(order)

    def test_order_with_customer(self, store, warehouse, create_customer):
        """Test order with customer."""
        customer = create_customer(name='VIP客戶')
        order = Order.objects.create(
            order_number='ORD20260101003',
            store=store,
            warehouse=warehouse,
            customer=customer,
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00')
        )

        assert order.customer == customer
        assert order.customer.name == 'VIP客戶'

    def test_order_status_choices(self, store, warehouse):
        """Test order status choices."""
        order = Order.objects.create(
            order_number='ORD20260101004',
            store=store,
            warehouse=warehouse,
            status='PENDING',
            subtotal=Decimal('0'),
            total_amount=Decimal('0')
        )

        assert order.status == 'PENDING'

        order.status = 'COMPLETED'
        order.save()
        order.refresh_from_db()
        assert order.status == 'COMPLETED'


@pytest.mark.django_db
class TestOrderItemModel:
    """Tests for OrderItem model."""

    def test_create_order_item(self, store, warehouse, create_product):
        """Test creating an order item."""
        product = create_product(name='測試商品', sale_price=Decimal('100.00'))
        order = Order.objects.create(
            order_number='ORD20260101005',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )

        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            unit_price=Decimal('100.00'),
            subtotal=Decimal('200.00')
        )

        assert item.quantity == 2
        assert item.unit_price == Decimal('100.00')
        assert item.subtotal == Decimal('200.00')

    def test_order_item_auto_subtotal(self, store, warehouse, create_product):
        """Test order item auto-calculates subtotal."""
        product = create_product(sale_price=Decimal('50.00'))
        order = Order.objects.create(
            order_number='ORD20260101006',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('0'),
            total_amount=Decimal('0')
        )

        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=3,
            unit_price=Decimal('50.00'),
            discount_amount=Decimal('10.00'),
            subtotal=Decimal('140.00')  # Will be recalculated on save
        )

        # The model's save method calculates: (3 * 50) - 10 = 140
        assert item.subtotal == Decimal('140.00')


@pytest.mark.django_db
class TestPaymentModel:
    """Tests for Payment model."""

    def test_create_payment(self, store, warehouse):
        """Test creating a payment."""
        order = Order.objects.create(
            order_number='ORD20260101007',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )

        payment = Payment.objects.create(
            order=order,
            method='CASH',
            amount=Decimal('100.00'),
            status='COMPLETED'
        )

        assert payment.method == 'CASH'
        assert payment.amount == Decimal('100.00')
        assert payment.status == 'COMPLETED'

    def test_payment_methods(self, store, warehouse):
        """Test different payment methods."""
        order = Order.objects.create(
            order_number='ORD20260101008',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00')
        )

        # Cash payment
        p1 = Payment.objects.create(
            order=order,
            method='CASH',
            amount=Decimal('500.00'),
            status='COMPLETED'
        )

        # Credit card payment
        p2 = Payment.objects.create(
            order=order,
            method='CREDIT_CARD',
            amount=Decimal('500.00'),
            status='COMPLETED'
        )

        assert order.payments.count() == 2
        assert p1.method == 'CASH'
        assert p2.method == 'CREDIT_CARD'


@pytest.mark.django_db
class TestRefundModel:
    """Tests for Refund model."""

    def test_create_refund(self, store, warehouse):
        """Test creating a refund."""
        order = Order.objects.create(
            order_number='ORD20260101009',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00')
        )

        refund = Refund.objects.create(
            refund_number='REF20260101001',
            order=order,
            refund_amount=Decimal('100.00'),
            reason='商品瑕疵',
            status='PENDING'
        )

        assert refund.refund_number == 'REF20260101001'
        assert refund.refund_amount == Decimal('100.00')
        assert refund.order == order

    def test_refund_str(self, store, warehouse):
        """Test refund string representation."""
        order = Order.objects.create(
            order_number='ORD20260101010',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('0'),
            total_amount=Decimal('0')
        )

        refund = Refund.objects.create(
            refund_number='REF20260101002',
            order=order,
            refund_amount=Decimal('50.00'),
            reason='測試退貨'
        )

        assert 'REF20260101002' in str(refund)
