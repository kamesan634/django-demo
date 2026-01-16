"""
Tests for products API endpoints.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from apps.products.models import Product, Category, ProductBarcode


@pytest.mark.django_db
class TestProductAPI:
    """Tests for product API endpoints."""

    def test_list_products(self, admin_client, create_product):
        """Test listing products."""
        create_product(name='商品1', sku='P001')
        create_product(name='商品2', sku='P002')

        response = admin_client.get('/api/v1/products/')

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert len(results) >= 2

    def test_get_product_detail(self, admin_client, create_product):
        """Test getting product detail."""
        product = create_product(name='詳情商品', sku='DETAIL001')

        response = admin_client.get(f'/api/v1/products/{product.id}/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('data', response.data)
        assert data['name'] == '詳情商品'

    def test_create_product(self, admin_client, create_category):
        """Test creating a product."""
        category = create_category(name='新分類')

        response = admin_client.post('/api/v1/products/', {
            'name': '新商品',
            'sku': 'NEW001',
            'category': category.id,
            'sale_price': '199.00',
            'cost_price': '100.00',
            'status': 'ACTIVE'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert Product.objects.filter(sku='NEW001').exists()

    def test_update_product(self, admin_client, create_product):
        """Test updating a product."""
        product = create_product(name='原名稱', sku='UPD001')

        response = admin_client.patch(f'/api/v1/products/{product.id}/', {
            'name': '新名稱'
        })

        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.name == '新名稱'

    def test_delete_product(self, admin_client, create_product):
        """Test deleting a product."""
        product = create_product(sku='DEL001')

        response = admin_client.delete(f'/api/v1/products/{product.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_products_by_status(self, admin_client, create_product):
        """Test filtering products by status."""
        create_product(name='啟用商品', sku='ACT001', status='ACTIVE')
        create_product(name='停用商品', sku='INA001', status='INACTIVE')

        response = admin_client.get('/api/v1/products/?status=ACTIVE')

        assert response.status_code == status.HTTP_200_OK
        # Response format: {'success': True, 'data': [...], 'meta': {...}}
        results = response.data.get('data', response.data.get('results', []))
        # All results should have ACTIVE status
        for item in results:
            assert item['status'] == 'ACTIVE'

    def test_search_products(self, admin_client, create_product):
        """Test searching products by name."""
        create_product(name='可口可樂', sku='COKE001')
        create_product(name='雪碧', sku='SPRITE001')

        response = admin_client.get('/api/v1/products/?search=可樂')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCategoryAPI:
    """Tests for category API endpoints."""

    def test_list_categories(self, admin_client, create_category):
        """Test listing categories."""
        create_category(name='分類1')
        create_category(name='分類2')

        response = admin_client.get('/api/v1/categories/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_category(self, admin_client):
        """Test creating a category."""
        response = admin_client.post('/api/v1/categories/', {
            'name': '新分類',
            'sort_order': 1
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.filter(name='新分類').exists()

    def test_create_subcategory(self, admin_client, create_category):
        """Test creating a subcategory."""
        parent = create_category(name='父分類')

        response = admin_client.post('/api/v1/categories/', {
            'name': '子分類',
            'parent': parent.id,
            'sort_order': 1
        })

        assert response.status_code == status.HTTP_201_CREATED
        subcategory = Category.objects.get(name='子分類')
        assert subcategory.parent == parent


@pytest.mark.django_db
class TestProductBarcodeAPI:
    """Tests for product barcode operations."""

    def test_search_by_barcode(self, admin_client, create_product):
        """Test searching product by barcode."""
        product = create_product(name='條碼商品', sku='BAR001')
        ProductBarcode.objects.create(
            product=product,
            barcode='4710000000001',
            is_primary=True
        )

        response = admin_client.get('/api/v1/products/?search=4710000000001')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProductPermissions:
    """Tests for product API permissions."""

    def test_unauthenticated_cannot_create(self, api_client):
        """Test that unauthenticated users cannot create products."""
        response = api_client.post('/api/v1/products/', {
            'name': '未授權商品',
            'sku': 'UNAUTH001',
            'sale_price': '100.00'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_can_list(self, auth_client, create_product):
        """Test that authenticated users can list products."""
        create_product()

        response = auth_client.get('/api/v1/products/')

        assert response.status_code == status.HTTP_200_OK
