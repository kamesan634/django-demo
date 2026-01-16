"""
Tests for sales API endpoints.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from apps.sales.models import Order, OrderItem, Payment, Refund


@pytest.mark.django_db
class TestOrderAPI:
    """Tests for order API endpoints (read-only)."""

    def test_list_orders(self, admin_client, store, warehouse):
        """Test listing orders."""
        Order.objects.create(
            order_number='ORD20260101001',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )

        response = admin_client.get('/api/v1/orders/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_order_detail(self, admin_client, store, warehouse):
        """Test getting order detail."""
        order = Order.objects.create(
            order_number='ORD20260101002',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00')
        )

        response = admin_client.get(f'/api/v1/orders/{order.id}/')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_orders_by_status(self, admin_client, store, warehouse):
        """Test filtering orders by status."""
        Order.objects.create(
            order_number='ORD20260101003',
            store=store,
            warehouse=warehouse,
            status='PENDING',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        Order.objects.create(
            order_number='ORD20260101004',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )

        response = admin_client.get('/api/v1/orders/?status=PENDING')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_orders_by_store(self, admin_client, store, warehouse):
        """Test filtering orders by store."""
        Order.objects.create(
            order_number='ORD20260101005',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )

        response = admin_client.get(f'/api/v1/orders/?store={store.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_search_orders_by_order_number(self, admin_client, store, warehouse):
        """Test searching orders by order number."""
        Order.objects.create(
            order_number='ORD20260101006',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )

        response = admin_client.get('/api/v1/orders/?search=ORD20260101006')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrderWithItems:
    """Tests for order with items."""

    def test_order_detail_includes_items(self, admin_client, store, warehouse, create_product):
        """Test that order detail includes items."""
        product = create_product(name='訂單商品', sale_price=Decimal('50.00'))
        order = Order.objects.create(
            order_number='ORD20260101007',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            unit_price=Decimal('50.00'),
            subtotal=Decimal('100.00')
        )

        response = admin_client.get(f'/api/v1/orders/{order.id}/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRefundAPI:
    """Tests for refund API endpoints."""

    def test_list_refunds(self, admin_client, store, warehouse):
        """Test listing refunds."""
        order = Order.objects.create(
            order_number='ORD20260101008',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        Refund.objects.create(
            refund_number='REF20260101001',
            order=order,
            refund_amount=Decimal('50.00'),
            reason='商品瑕疵'
        )

        response = admin_client.get('/api/v1/refunds/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_refund(self, admin_client, store, warehouse):
        """Test creating a refund."""
        order = Order.objects.create(
            order_number='ORD20260101009',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00')
        )

        response = admin_client.post('/api/v1/refunds/', {
            'order': order.id,
            'refund_amount': '100.00',
            'reason': '測試退貨'
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_refund_detail(self, admin_client, store, warehouse):
        """Test getting refund detail."""
        order = Order.objects.create(
            order_number='ORD20260101010',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        refund = Refund.objects.create(
            refund_number='REF20260101002',
            order=order,
            refund_amount=Decimal('50.00'),
            reason='測試'
        )

        response = admin_client.get(f'/api/v1/refunds/{refund.id}/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrderPermissions:
    """Tests for order API permissions."""

    def test_unauthenticated_cannot_list_orders(self, api_client):
        """Test that unauthenticated users cannot list orders."""
        response = api_client.get('/api/v1/orders/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_can_list_orders(self, auth_client, store, warehouse):
        """Test that authenticated users can list orders."""
        Order.objects.create(
            order_number='ORD20260101011',
            store=store,
            warehouse=warehouse,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )

        response = auth_client.get('/api/v1/orders/')

        assert response.status_code == status.HTTP_200_OK
