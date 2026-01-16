"""
Tests for sales services.
"""
import pytest
from decimal import Decimal
from apps.sales.services import SalesService
from apps.sales.models import Order, OrderItem, Payment, Refund, RefundItem
from apps.inventory.services import InventoryService
from apps.inventory.models import Inventory
from apps.core.exceptions import InvalidOperationError


@pytest.mark.django_db
class TestSalesServiceCreateOrder:
    """Tests for SalesService.create_order method."""

    def test_create_order_basic(self, store, warehouse, create_product, admin_user):
        """Test creating a basic order."""
        product = create_product(name='測試商品', sku='SALE001', sale_price=Decimal('100'))

        # Add inventory first
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2,
                    'unit_price': 100,
                }
            ],
            'payments': [
                {
                    'method': 'CASH',
                    'amount': 210,  # Including tax
                }
            ]
        }

        order = SalesService.create_order(order_data, admin_user)

        assert order.order_number.startswith('POS')
        assert order.store_id == store.id
        assert order.status == 'COMPLETED'
        assert order.subtotal == Decimal('200')
        assert order.items.count() == 1
        assert order.payments.count() == 1

        # Check inventory was deducted
        inventory = Inventory.objects.get(
            warehouse_id=warehouse.id,
            product_id=product.id
        )
        assert inventory.quantity == 98  # 100 - 2

    def test_create_order_with_discount(self, store, warehouse, create_product, admin_user):
        """Test creating order with item discount."""
        product = create_product(name='測試商品', sku='SALE002', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'discount_amount': 50,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 3,
                    'unit_price': 100,
                    'discount_amount': 20,
                }
            ],
            'payments': [
                {
                    'method': 'CASH',
                    'amount': 244,
                }
            ]
        }

        order = SalesService.create_order(order_data, admin_user)

        # Item subtotal: (3 * 100) - 20 = 280
        assert order.subtotal == Decimal('280')
        assert order.discount_amount == Decimal('50')

    def test_create_order_with_customer(self, store, warehouse, create_product, create_customer, admin_user):
        """Test creating order with customer."""
        product = create_product(name='測試商品', sku='SALE003', sale_price=Decimal('1000'))
        customer = create_customer(name='測試會員')

        # Store initial customer stats
        initial_spending = customer.total_spending
        initial_orders = customer.total_orders

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'customer_id': customer.id,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 1,
                    'unit_price': 1000,
                }
            ],
            'payments': [
                {
                    'method': 'CASH',
                    'amount': 1050,
                }
            ]
        }

        order = SalesService.create_order(order_data, admin_user)

        assert order.customer_id == customer.id

        # Refresh customer to get updated stats
        customer.refresh_from_db()
        assert customer.total_orders == initial_orders + 1

    def test_create_order_multiple_payments(self, store, warehouse, create_product, admin_user):
        """Test creating order with multiple payment methods."""
        product = create_product(name='測試商品', sku='SALE004', sale_price=Decimal('500'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 2,
                    'unit_price': 500,
                }
            ],
            'payments': [
                {
                    'method': 'CASH',
                    'amount': 500,
                },
                {
                    'method': 'CREDIT_CARD',
                    'amount': 550,
                    'reference_number': 'CC12345678',
                }
            ]
        }

        order = SalesService.create_order(order_data, admin_user)

        assert order.payments.count() == 2
        assert order.payments.filter(method='CASH').exists()
        assert order.payments.filter(method='CREDIT_CARD').exists()


@pytest.mark.django_db
class TestSalesServiceVoidOrder:
    """Tests for SalesService.void_order method."""

    def test_void_order_success(self, store, warehouse, create_product, admin_user):
        """Test voiding an order."""
        product = create_product(name='測試商品', sku='VOID001', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Create order
        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 5,
                    'unit_price': 100,
                }
            ],
            'payments': [
                {'method': 'CASH', 'amount': 525}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)

        # Check inventory after order
        inventory = Inventory.objects.get(
            warehouse_id=warehouse.id,
            product_id=product.id
        )
        assert inventory.quantity == 95

        # Void the order
        voided_order = SalesService.void_order(order, '客戶取消', admin_user)

        assert voided_order.status == 'VOIDED'
        assert voided_order.void_reason == '客戶取消'

        # Check inventory was restored
        inventory.refresh_from_db()
        assert inventory.quantity == 100

    def test_void_already_voided_order(self, store, warehouse, create_product, admin_user):
        """Test voiding an already voided order raises error."""
        product = create_product(name='測試商品', sku='VOID002', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 100}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 105}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        SalesService.void_order(order, '取消', admin_user)

        # Try to void again
        with pytest.raises(InvalidOperationError):
            SalesService.void_order(order, '再次取消', admin_user)

    def test_void_cancelled_order(self, store, warehouse):
        """Test voiding a cancelled order raises error."""
        order = Order.objects.create(
            order_number='ORD123456',
            store=store,
            warehouse=warehouse,
            status='CANCELLED',
            subtotal=Decimal('100'),
            total_amount=Decimal('105')
        )

        with pytest.raises(InvalidOperationError):
            SalesService.void_order(order, '作廢', None)


@pytest.mark.django_db
class TestSalesServiceCompleteRefund:
    """Tests for SalesService.complete_refund method."""

    def test_complete_refund_success(self, store, warehouse, create_product, admin_user):
        """Test completing a refund."""
        product = create_product(name='測試商品', sku='REF001', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Create order
        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 3, 'unit_price': 100}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 315}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        order_item = order.items.first()

        # Check inventory after order
        inventory = Inventory.objects.get(
            warehouse_id=warehouse.id,
            product_id=product.id
        )
        assert inventory.quantity == 97

        # Create refund
        refund = Refund.objects.create(
            refund_number='REF20260101001',
            order=order,
            refund_amount=Decimal('100'),
            reason='商品瑕疵',
            status='PENDING'
        )
        RefundItem.objects.create(
            refund=refund,
            order_item=order_item,
            quantity=1
        )

        # Complete refund
        completed_refund = SalesService.complete_refund(refund, admin_user)

        assert completed_refund.status == 'COMPLETED'
        assert completed_refund.completed_at is not None

        # Check inventory was restored
        inventory.refresh_from_db()
        assert inventory.quantity == 98

        # Check order item refunded quantity was updated
        order_item.refresh_from_db()
        assert order_item.refunded_quantity == 1


@pytest.mark.django_db
class TestInvoiceServiceGenerateNumber:
    """Tests for InvoiceService.generate_invoice_number method."""

    def test_generate_invoice_number_format(self):
        """Test invoice number is generated in correct format."""
        from apps.sales.services import InvoiceService

        number = InvoiceService.generate_invoice_number()

        # Should be XX-12345678 format
        assert len(number) == 11
        assert number[2] == '-'
        assert number[:2].isalpha()
        assert number[3:].isdigit()

    def test_generate_invoice_number_unique(self):
        """Test invoice numbers are unique."""
        from apps.sales.services import InvoiceService

        numbers = [InvoiceService.generate_invoice_number() for _ in range(100)]
        # While not guaranteed unique, collisions should be extremely rare
        assert len(set(numbers)) >= 95  # Allow some flexibility


@pytest.mark.django_db
class TestInvoiceServiceCreateInvoice:
    """Tests for InvoiceService.create_invoice method."""

    def test_create_invoice_b2c(self, store, warehouse, create_product, admin_user):
        """Test creating B2C invoice."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Invoice Test', sku='INV001', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 2, 'unit_price': 100}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 210}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)

        invoice = InvoiceService.create_invoice(
            order_id=order.id,
            invoice_type='B2C',
            user=admin_user
        )

        assert invoice.order_id == order.id
        assert invoice.invoice_type == 'B2C'
        assert invoice.status == 'PENDING'
        assert invoice.items.count() == 1

    def test_create_invoice_b2b(self, store, warehouse, create_product, admin_user):
        """Test creating B2B invoice with buyer info."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Invoice Test B2B', sku='INV002', sale_price=Decimal('500'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 500}
            ],
            'payments': [
                {'method': 'CREDIT_CARD', 'amount': 525}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)

        invoice = InvoiceService.create_invoice(
            order_id=order.id,
            invoice_type='B2B',
            buyer_tax_id='12345678',
            buyer_name='測試公司',
            user=admin_user
        )

        assert invoice.invoice_type == 'B2B'
        assert invoice.buyer_tax_id == '12345678'
        assert invoice.buyer_name == '測試公司'

    def test_create_invoice_with_carrier(self, store, warehouse, create_product, admin_user):
        """Test creating invoice with carrier (電子載具)."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Carrier Test', sku='INV003', sale_price=Decimal('200'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 200}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 210}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)

        invoice = InvoiceService.create_invoice(
            order_id=order.id,
            invoice_type='B2C',
            carrier_type='MOBILE',
            carrier_id='/ABC1234',
            user=admin_user
        )

        assert invoice.carrier_type == 'MOBILE'
        assert invoice.carrier_id == '/ABC1234'

    def test_create_invoice_order_not_found(self, admin_user):
        """Test creating invoice for non-existent order."""
        from apps.sales.services import InvoiceService

        with pytest.raises(InvalidOperationError, match='找不到此訂單'):
            InvoiceService.create_invoice(order_id=99999, user=admin_user)

    def test_create_invoice_duplicate(self, store, warehouse, create_product, admin_user):
        """Test creating duplicate invoice raises error."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Duplicate Test', sku='INV004', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=20,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 100}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 105}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)

        # Create first invoice
        InvoiceService.create_invoice(order_id=order.id, user=admin_user)

        # Try to create second invoice
        with pytest.raises(InvalidOperationError, match='此訂單已開立發票'):
            InvoiceService.create_invoice(order_id=order.id, user=admin_user)

    def test_create_invoice_invalid_status(self, store, warehouse):
        """Test creating invoice for order with invalid status."""
        from apps.sales.services import InvoiceService

        order = Order.objects.create(
            order_number='ORD999999',
            store=store,
            warehouse=warehouse,
            status='CANCELLED',
            subtotal=Decimal('100'),
            total_amount=Decimal('105')
        )

        with pytest.raises(InvalidOperationError, match='訂單狀態不允許開立發票'):
            InvoiceService.create_invoice(order_id=order.id)


@pytest.mark.django_db
class TestInvoiceServiceIssueInvoice:
    """Tests for InvoiceService.issue_invoice method."""

    def test_issue_invoice_success(self, store, warehouse, create_product, admin_user):
        """Test issuing a pending invoice."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Issue Test', sku='INV005', sale_price=Decimal('150'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=40,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 150}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 158}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        invoice = InvoiceService.create_invoice(order_id=order.id, user=admin_user)

        issued_invoice = InvoiceService.issue_invoice(invoice, admin_user)

        assert issued_invoice.status == 'ISSUED'
        assert issued_invoice.issued_at is not None

    def test_issue_invoice_already_issued(self, store, warehouse, create_product, admin_user):
        """Test issuing already issued invoice raises error."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Double Issue Test', sku='INV006', sale_price=Decimal('100'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=25,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 100}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 105}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        invoice = InvoiceService.create_invoice(order_id=order.id, user=admin_user)
        InvoiceService.issue_invoice(invoice, admin_user)

        with pytest.raises(InvalidOperationError, match='發票狀態不允許開立'):
            InvoiceService.issue_invoice(invoice, admin_user)


@pytest.mark.django_db
class TestInvoiceServiceVoidInvoice:
    """Tests for InvoiceService.void_invoice method."""

    def test_void_invoice_success(self, store, warehouse, create_product, admin_user):
        """Test voiding an issued invoice."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Void Test', sku='INV007', sale_price=Decimal('300'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=35,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 300}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 315}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        invoice = InvoiceService.create_invoice(order_id=order.id, user=admin_user)
        InvoiceService.issue_invoice(invoice, admin_user)

        voided_invoice = InvoiceService.void_invoice(invoice, '輸入錯誤', admin_user)

        assert voided_invoice.status == 'VOIDED'
        assert voided_invoice.void_reason == '輸入錯誤'
        assert voided_invoice.voided_at is not None

    def test_void_invoice_pending(self, store, warehouse, create_product, admin_user):
        """Test voiding a pending invoice raises error."""
        from apps.sales.services import InvoiceService
        from apps.inventory.services import InventoryService

        product = create_product(name='Void Pending Test', sku='INV008', sale_price=Decimal('200'))

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=15,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        order_data = {
            'store_id': store.id,
            'warehouse_id': warehouse.id,
            'items': [
                {'product_id': product.id, 'quantity': 1, 'unit_price': 200}
            ],
            'payments': [
                {'method': 'CASH', 'amount': 210}
            ]
        }
        order = SalesService.create_order(order_data, admin_user)
        invoice = InvoiceService.create_invoice(order_id=order.id, user=admin_user)

        with pytest.raises(InvalidOperationError, match='只有已開立的發票可以作廢'):
            InvoiceService.void_invoice(invoice, '取消', admin_user)
