"""
Pytest configuration and shared fixtures.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com',
        display_name='Test User',
        is_superuser=False,
        **kwargs
    ):
        from apps.accounts.models import User
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            display_name=display_name,
            is_superuser=is_superuser,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """Create a regular user."""
    return create_user()


@pytest.fixture
def admin_user(create_user, create_role):
    """Create an admin user with ADMIN role."""
    admin_role = create_role(name='系統管理員', code='ADMIN')
    return create_user(
        username='admin',
        email='admin@example.com',
        display_name='Admin User',
        is_superuser=True,
        is_staff=True,
        role=admin_role
    )


@pytest.fixture
def auth_client(api_client, user):
    """Return an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an authenticated admin API client."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def create_role(db):
    """Factory fixture to create roles."""
    def _create_role(name='Test Role', code='TEST_ROLE', **kwargs):
        from apps.accounts.models import Role
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={'name': name, **kwargs}
        )
        return role
    return _create_role


@pytest.fixture
def create_store(db):
    """Factory fixture to create stores."""
    def _create_store(name='Test Store', code='TEST001', **kwargs):
        from apps.stores.models import Store
        store, _ = Store.objects.get_or_create(
            code=code,
            defaults={'name': name, 'status': 'ACTIVE', **kwargs}
        )
        return store
    return _create_store


@pytest.fixture
def store(create_store):
    """Create a default store."""
    return create_store()


@pytest.fixture
def create_warehouse(db, store):
    """Factory fixture to create warehouses."""
    def _create_warehouse(name='Test Warehouse', code='WH-TEST', **kwargs):
        from apps.stores.models import Warehouse
        warehouse, _ = Warehouse.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'store': kwargs.pop('store', store),
                'warehouse_type': 'STORE',
                'is_default': True,
                **kwargs
            }
        )
        return warehouse
    return _create_warehouse


@pytest.fixture
def warehouse(create_warehouse):
    """Create a default warehouse."""
    return create_warehouse()


@pytest.fixture
def create_category(db):
    """Factory fixture to create categories."""
    def _create_category(name='Test Category', **kwargs):
        from apps.products.models import Category
        category, _ = Category.objects.get_or_create(
            name=name,
            defaults={'sort_order': 1, **kwargs}
        )
        return category
    return _create_category


@pytest.fixture
def category(create_category):
    """Create a default category."""
    return create_category()


@pytest.fixture
def create_product(db, category):
    """Factory fixture to create products."""
    counter = [0]

    def _create_product(name='Test Product', sku=None, **kwargs):
        from apps.products.models import Product
        from decimal import Decimal

        counter[0] += 1
        if sku is None:
            sku = f'TEST{counter[0]:04d}'

        product, _ = Product.objects.get_or_create(
            sku=sku,
            defaults={
                'name': name,
                'category': kwargs.pop('category', category),
                'sale_price': Decimal('100.00'),
                'cost_price': Decimal('50.00'),
                'status': 'ACTIVE',
                **kwargs
            }
        )
        return product
    return _create_product


@pytest.fixture
def product(create_product):
    """Create a default product."""
    return create_product()


@pytest.fixture
def create_customer(db):
    """Factory fixture to create customers."""
    counter = [0]

    def _create_customer(name='Test Customer', **kwargs):
        from apps.customers.models import Customer

        counter[0] += 1
        member_no = kwargs.pop('member_no', f'M{counter[0]:06d}')
        phone = kwargs.pop('phone', f'09{counter[0]:08d}')

        customer, _ = Customer.objects.get_or_create(
            member_no=member_no,
            defaults={
                'name': name,
                'phone': phone,
                **kwargs
            }
        )
        return customer
    return _create_customer


@pytest.fixture
def customer(create_customer):
    """Create a default customer."""
    return create_customer()
