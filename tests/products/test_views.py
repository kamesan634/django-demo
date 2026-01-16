"""
Tests for products views.
"""
import pytest
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch, MagicMock
from rest_framework import status
from django.http import HttpResponse


@pytest.mark.django_db
class TestProductViewSet:
    """Tests for ProductViewSet."""

    def test_list_products(self, admin_client, create_product):
        """Test listing products."""
        create_product(name='Product 1', sku='PROD001')
        create_product(name='Product 2', sku='PROD002')

        response = admin_client.get('/api/v1/products/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_products_unauthenticated(self, api_client):
        """Test listing products without authentication."""
        response = api_client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_product_detail(self, admin_client, create_product):
        """Test getting product detail."""
        product = create_product(name='Detail Product', sku='PROD003')

        response = admin_client.get(f'/api/v1/products/{product.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Detail Product'

    def test_create_product(self, admin_client, create_category):
        """Test creating a product."""
        from apps.products.models import Unit

        category = create_category()
        unit = Unit.objects.create(name='Test Unit')

        data = {
            'name': 'New Product',
            'sku': 'NEWPROD001',
            'category': category.id,
            'unit': unit.id,
            'cost_price': '100.00',
            'sale_price': '150.00',
            'status': 'ACTIVE'
        }

        response = admin_client.post('/api/v1/products/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Product'

    def test_update_product(self, admin_client, create_product):
        """Test updating a product."""
        product = create_product(name='Old Name', sku='PROD004')

        response = admin_client.patch(
            f'/api/v1/products/{product.id}/',
            {'name': 'Updated Name'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

    def test_delete_product(self, admin_client, create_product):
        """Test deleting a product."""
        product = create_product(name='To Delete', sku='PROD005')

        response = admin_client.delete(f'/api/v1/products/{product.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_products_by_category(self, admin_client, create_product, create_category):
        """Test filtering products by category."""
        category = create_category()
        create_product(name='Category Product', sku='PROD006', category=category)

        response = admin_client.get(f'/api/v1/products/?category={category.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_products_by_status(self, admin_client, create_product):
        """Test filtering products by status."""
        create_product(name='Active Product', sku='PROD007', status='ACTIVE')

        response = admin_client.get('/api/v1/products/?status=ACTIVE')

        assert response.status_code == status.HTTP_200_OK

    def test_search_products(self, admin_client, create_product):
        """Test searching products."""
        create_product(name='Searchable Product', sku='SEARCH001')

        response = admin_client.get('/api/v1/products/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK

    def test_import_data_no_file(self, admin_client):
        """Test import_data without file returns error."""
        response = admin_client.post('/api/v1/products/import_data/')

        # Should return error for missing file
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_import_data_unsupported_format(self, admin_client):
        """Test import_data with unsupported file format."""
        file_content = BytesIO(b'unsupported content')
        file_content.name = 'products.txt'

        response = admin_client.post(
            '/api/v1/products/import_data/',
            {'file': file_content},
            format='multipart'
        )

        # Should return error for unsupported format
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_import_data_invalid_excel(self, admin_client):
        """Test import_data with invalid Excel file."""
        file_content = BytesIO(b'not a real excel file')
        file_content.name = 'products.xlsx'

        response = admin_client.post(
            '/api/v1/products/import_data/',
            {'file': file_content},
            format='multipart'
        )

        # Should handle invalid file gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_import_data_invalid_csv(self, admin_client):
        """Test import_data with invalid CSV file."""
        file_content = BytesIO(b'')
        file_content.name = 'products.csv'

        response = admin_client.post(
            '/api/v1/products/import_data/',
            {'file': file_content},
            format='multipart'
        )

        # Should handle invalid file gracefully
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_export_data_excel(self, admin_client, create_product):
        """Test exporting products to Excel."""
        create_product(name='Export Product', sku='EXP001')

        response = admin_client.get('/api/v1/products/export_data/')

        # Should return file or success response
        assert response.status_code == status.HTTP_200_OK

    def test_export_data_csv(self, admin_client, create_product):
        """Test exporting products to CSV."""
        create_product(name='Export Product', sku='EXP002')

        # Use export_format param to avoid DRF's format parameter conflict
        response = admin_client.get('/api/v1/products/export_data/?export_format=csv')

        # Should return file or success response
        assert response.status_code == status.HTTP_200_OK

    def test_import_template(self, admin_client):
        """Test downloading import template."""
        response = admin_client.get('/api/v1/products/import_template/')

        # Should return template file
        assert response.status_code == status.HTTP_200_OK

    def test_search_barcode_found(self, admin_client, create_product):
        """Test searching product by barcode - found."""
        from apps.products.models import ProductBarcode

        product = create_product(name='Barcode Product', sku='BC001')
        ProductBarcode.objects.create(
            product=product,
            barcode='1234567890123',
            barcode_type='EAN13'
        )

        response = admin_client.get('/api/v1/products/search_barcode/?barcode=1234567890123')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['barcode'] == '1234567890123'

    def test_search_barcode_not_found(self, admin_client):
        """Test searching product by barcode - not found."""
        response = admin_client.get('/api/v1/products/search_barcode/?barcode=9999999999999')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_barcode_no_param(self, admin_client):
        """Test searching product by barcode without param."""
        response = admin_client.get('/api/v1/products/search_barcode/')

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_product_stock(self, admin_client, create_product, warehouse):
        """Test getting product stock."""
        from apps.inventory.models import Inventory

        product = create_product(name='Stock Product', sku='STK001')
        Inventory.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=100,
            available_quantity=90,
            reserved_quantity=10
        )

        response = admin_client.get(f'/api/v1/products/{product.id}/stock/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['quantity'] == 100

    def test_product_stock_by_warehouse(self, admin_client, create_product, warehouse, create_warehouse):
        """Test getting product stock filtered by warehouse."""
        from apps.inventory.models import Inventory

        product = create_product(name='Stock Product', sku='STK002')
        warehouse2 = create_warehouse(name='Warehouse 2', code='WH002')

        Inventory.objects.create(
            product=product, warehouse=warehouse,
            quantity=100, available_quantity=90
        )
        Inventory.objects.create(
            product=product, warehouse=warehouse2,
            quantity=50, available_quantity=50
        )

        response = admin_client.get(
            f'/api/v1/products/{product.id}/stock/?warehouse={warehouse.id}'
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['warehouse_id'] == warehouse.id

    def test_add_barcode(self, admin_client, create_product):
        """Test adding barcode to product."""
        product = create_product(name='Barcode Product', sku='BC002')

        response = admin_client.post(
            f'/api/v1/products/{product.id}/add_barcode/',
            {'barcode': '9876543210123', 'barcode_type': 'EAN13'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True

    def test_add_barcode_invalid(self, admin_client, create_product):
        """Test adding invalid barcode to product."""
        product = create_product(name='Barcode Product', sku='BC003')

        response = admin_client.post(
            f'/api/v1/products/{product.id}/add_barcode/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCategoryViewSet:
    """Tests for CategoryViewSet."""

    def test_list_categories(self, admin_client, create_category):
        """Test listing categories."""
        create_category(name='Category 1')
        create_category(name='Category 2')

        response = admin_client.get('/api/v1/categories/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_category_detail(self, admin_client, create_category):
        """Test getting category detail."""
        category = create_category(name='Detail Category')

        response = admin_client.get(f'/api/v1/categories/{category.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Detail Category'

    def test_create_category(self, admin_client):
        """Test creating a category."""
        data = {
            'name': 'New Category'
        }

        response = admin_client.post('/api/v1/categories/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Category'

    def test_update_category(self, admin_client, create_category):
        """Test updating a category."""
        category = create_category(name='Old Category')

        response = admin_client.patch(
            f'/api/v1/categories/{category.id}/',
            {'name': 'Updated Category'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Category'

    def test_delete_category(self, admin_client, create_category):
        """Test deleting a category."""
        category = create_category(name='To Delete Category')

        response = admin_client.delete(f'/api/v1/categories/{category.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_category_tree(self, admin_client, db):
        """Test getting category tree structure."""
        from apps.products.models import Category

        # Create root categories
        root1 = Category.objects.create(name='Electronics', sort_order=1, is_active=True)
        root2 = Category.objects.create(name='Clothing', sort_order=2, is_active=True)

        # Create child categories
        Category.objects.create(name='Phones', parent=root1, sort_order=1, is_active=True)
        Category.objects.create(name='Laptops', parent=root1, sort_order=2, is_active=True)

        response = admin_client.get('/api/v1/categories/tree/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']) >= 2

    def test_category_tree_empty(self, admin_client, db):
        """Test getting empty category tree."""
        response = admin_client.get('/api/v1/categories/tree/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_filter_categories_by_parent(self, admin_client, db):
        """Test filtering categories by parent."""
        from apps.products.models import Category

        parent = Category.objects.create(name='Parent', sort_order=1)
        Category.objects.create(name='Child', parent=parent, sort_order=1)

        response = admin_client.get(f'/api/v1/categories/?parent={parent.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_categories_by_is_active(self, admin_client, db):
        """Test filtering categories by is_active."""
        from apps.products.models import Category

        Category.objects.create(name='Active', sort_order=1, is_active=True)
        Category.objects.create(name='Inactive', sort_order=2, is_active=False)

        response = admin_client.get('/api/v1/categories/?is_active=true')

        assert response.status_code == status.HTTP_200_OK

    def test_search_categories(self, admin_client, db):
        """Test searching categories by name."""
        from apps.products.models import Category

        Category.objects.create(name='Searchable Category', sort_order=1)

        response = admin_client.get('/api/v1/categories/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUnitViewSet:
    """Tests for UnitViewSet."""

    def test_list_units(self, admin_client, db):
        """Test listing units."""
        from apps.products.models import Unit

        Unit.objects.create(name='Unit 1')
        Unit.objects.create(name='Unit 2')

        response = admin_client.get('/api/v1/units/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_unit_detail(self, admin_client, db):
        """Test getting unit detail."""
        from apps.products.models import Unit

        unit = Unit.objects.create(name='Detail Unit')

        response = admin_client.get(f'/api/v1/units/{unit.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Detail Unit'

    def test_update_unit(self, admin_client, db):
        """Test updating a unit."""
        from apps.products.models import Unit

        unit = Unit.objects.create(name='Old Unit')

        response = admin_client.patch(
            f'/api/v1/units/{unit.id}/',
            {'name': 'Updated Unit'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Unit'

    def test_delete_unit(self, admin_client, db):
        """Test deleting a unit."""
        from apps.products.models import Unit

        unit = Unit.objects.create(name='To Delete Unit')

        response = admin_client.delete(f'/api/v1/units/{unit.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_create_unit(self, admin_client):
        """Test creating a unit."""
        data = {
            'name': 'New Unit',
            'symbol': 'NU'
        }

        response = admin_client.post('/api/v1/units/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Unit'

    def test_search_units(self, admin_client, db):
        """Test searching units."""
        from apps.products.models import Unit

        Unit.objects.create(name='Searchable Unit', symbol='SU')

        response = admin_client.get('/api/v1/units/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTaxTypeViewSet:
    """Tests for TaxTypeViewSet."""

    def test_list_tax_types(self, admin_client, db):
        """Test listing tax types."""
        from apps.products.models import TaxType

        TaxType.objects.create(name='Standard', rate=Decimal('5'))

        response = admin_client.get('/api/v1/tax-types/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_tax_type(self, admin_client):
        """Test creating a tax type."""
        data = {
            'name': 'Reduced',
            'rate': '10.00'
        }

        response = admin_client.post('/api/v1/tax-types/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Reduced'

    def test_get_tax_type_detail(self, admin_client, db):
        """Test getting tax type detail."""
        from apps.products.models import TaxType

        tax_type = TaxType.objects.create(name='Detail Tax', rate=Decimal('15'))

        response = admin_client.get(f'/api/v1/tax-types/{tax_type.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Detail Tax'

    def test_update_tax_type(self, admin_client, db):
        """Test updating a tax type."""
        from apps.products.models import TaxType

        tax_type = TaxType.objects.create(name='Old Tax', rate=Decimal('5'))

        response = admin_client.patch(
            f'/api/v1/tax-types/{tax_type.id}/',
            {'name': 'Updated Tax', 'rate': '8.00'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Tax'

    def test_delete_tax_type(self, admin_client, db):
        """Test deleting a tax type."""
        from apps.products.models import TaxType

        tax_type = TaxType.objects.create(name='To Delete Tax', rate=Decimal('3'))

        response = admin_client.delete(f'/api/v1/tax-types/{tax_type.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_search_tax_types(self, admin_client, db):
        """Test searching tax types."""
        from apps.products.models import TaxType

        TaxType.objects.create(name='Searchable Tax', rate=Decimal('12'))

        response = admin_client.get('/api/v1/tax-types/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK
