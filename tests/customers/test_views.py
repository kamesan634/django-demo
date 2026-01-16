"""
Tests for customers views.
"""
import pytest
from decimal import Decimal
from rest_framework import status


@pytest.mark.django_db
class TestCustomerViewSet:
    """Tests for CustomerViewSet."""

    def test_list_customers(self, admin_client, create_customer):
        """Test listing customers."""
        create_customer(name='Customer 1')
        create_customer(name='Customer 2')

        response = admin_client.get('/api/v1/customers/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_list_customers_unauthenticated(self, api_client):
        """Test listing customers without authentication."""
        response = api_client.get('/api/v1/customers/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_customer_detail(self, admin_client, create_customer):
        """Test getting customer detail."""
        customer = create_customer(name='Test Customer')

        response = admin_client.get(f'/api/v1/customers/{customer.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Customer'

    def test_create_customer(self, admin_client):
        """Test creating a customer."""
        data = {
            'name': 'New Customer',
            'phone': '0912345678',
            'email': 'new@example.com'
        }

        response = admin_client.post('/api/v1/customers/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Customer'

    def test_update_customer(self, admin_client, create_customer):
        """Test updating a customer."""
        customer = create_customer(name='Old Name')

        data = {
            'name': 'Updated Name',
            'phone': customer.phone
        }

        response = admin_client.patch(f'/api/v1/customers/{customer.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

    def test_delete_customer(self, admin_client, create_customer):
        """Test deleting a customer."""
        customer = create_customer(name='To Delete')

        response = admin_client.delete(f'/api/v1/customers/{customer.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_search_customers_by_name(self, admin_client, create_customer):
        """Test searching customers by name."""
        create_customer(name='John Doe')
        create_customer(name='Jane Smith')

        response = admin_client.get('/api/v1/customers/?search=John')

        assert response.status_code == status.HTTP_200_OK

    def test_search_customers_by_phone(self, admin_client, create_customer):
        """Test searching customers by phone."""
        create_customer(name='Phone Customer', phone='0987654321')

        response = admin_client.get('/api/v1/customers/?search=0987654321')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_customers_by_level(self, admin_client, db):
        """Test filtering customers by level."""
        from apps.customers.models import Customer, CustomerLevel

        level = CustomerLevel.objects.create(
            name='VIP',
            min_spending=Decimal('5000'),
            discount_rate=Decimal('10')
        )

        Customer.objects.create(
            member_no='M999001',
            name='VIP Customer',
            phone='0911111111',
            level=level
        )

        response = admin_client.get(f'/api/v1/customers/?level={level.id}')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCustomerLevelViewSet:
    """Tests for CustomerLevelViewSet."""

    def test_list_customer_levels(self, admin_client, db):
        """Test listing customer levels."""
        from apps.customers.models import CustomerLevel

        CustomerLevel.objects.create(
            name='Bronze',
            min_spending=Decimal('0'),
            discount_rate=Decimal('0')
        )

        response = admin_client.get('/api/v1/customer-levels/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_customer_level(self, admin_client):
        """Test creating a customer level."""
        data = {
            'name': 'Silver',
            'min_spending': '1000.00',
            'discount_rate': '5.00'
        }

        response = admin_client.post('/api/v1/customer-levels/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Silver'

    def test_update_customer_level(self, admin_client, db):
        """Test updating a customer level."""
        from apps.customers.models import CustomerLevel

        level = CustomerLevel.objects.create(
            name='Old Level',
            min_spending=Decimal('100'),
            discount_rate=Decimal('2')
        )

        data = {
            'name': 'Updated Level',
            'min_spending': '200.00',
            'discount_rate': '3.00'
        }

        response = admin_client.put(f'/api/v1/customer-levels/{level.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Level'

    def test_delete_customer_level(self, admin_client, db):
        """Test deleting a customer level."""
        from apps.customers.models import CustomerLevel

        level = CustomerLevel.objects.create(
            name='To Delete',
            min_spending=Decimal('0'),
            discount_rate=Decimal('0')
        )

        response = admin_client.delete(f'/api/v1/customer-levels/{level.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestCustomerPointsActions:
    """Tests for customer points related actions."""

    def test_get_customer_points(self, admin_client, create_customer):
        """Test getting customer points and history."""
        customer = create_customer(name='Points Customer')

        response = admin_client.get(f'/api/v1/customers/{customer.id}/points/')

        assert response.status_code == status.HTTP_200_OK

    def test_add_customer_points(self, admin_client, create_customer):
        """Test adding points to a customer."""
        customer = create_customer(name='Add Points Customer')

        data = {
            'points': 100,
            'description': 'Bonus points'
        }

        response = admin_client.post(f'/api/v1/customers/{customer.id}/add_points/', data)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCustomerSearchAction:
    """Tests for customer search action."""

    def test_search_by_phone(self, admin_client, create_customer):
        """Test searching customer by phone number."""
        customer = create_customer(name='Phone Search', phone='0900111222')

        response = admin_client.get('/api/v1/customers/search/?phone=0900111222')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['name'] == 'Phone Search'

    def test_search_by_member_no(self, admin_client, db):
        """Test searching customer by member number."""
        from apps.customers.models import Customer

        customer = Customer.objects.create(
            member_no='SEARCH001',
            name='Member Search',
            phone='0900333444'
        )

        response = admin_client.get('/api/v1/customers/search/?member_no=SEARCH001')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['name'] == 'Member Search'

    def test_search_missing_params(self, admin_client):
        """Test search without phone or member_no returns error."""
        response = admin_client.get('/api/v1/customers/search/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_customer_not_found(self, admin_client):
        """Test search for non-existent customer."""
        response = admin_client.get('/api/v1/customers/search/?phone=9999999999')

        assert response.status_code == status.HTTP_404_NOT_FOUND
