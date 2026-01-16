"""
Tests for stores views.
"""
import pytest
from decimal import Decimal
from rest_framework import status


@pytest.mark.django_db
class TestStoreViewSet:
    """Tests for StoreViewSet."""

    def test_list_stores(self, admin_client, create_store):
        """Test listing stores."""
        create_store(name='Store 1', code='S001')
        create_store(name='Store 2', code='S002')

        response = admin_client.get('/api/v1/stores/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_list_stores_unauthenticated(self, api_client):
        """Test listing stores without authentication."""
        response = api_client.get('/api/v1/stores/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_store_detail(self, admin_client, create_store):
        """Test getting store detail."""
        store = create_store(name='Test Store', code='S003')

        response = admin_client.get(f'/api/v1/stores/{store.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Store'
        assert response.data['code'] == 'S003'

    def test_create_store(self, admin_client):
        """Test creating a store."""
        data = {
            'name': 'New Store',
            'code': 'NEW001',
            'address': '123 Test St',
            'phone': '0212345678',
            'status': 'ACTIVE'
        }

        response = admin_client.post('/api/v1/stores/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Store'

    def test_update_store(self, admin_client, create_store):
        """Test updating a store."""
        store = create_store(name='Old Name', code='S004')

        data = {
            'name': 'Updated Name',
            'code': 'S004',
            'status': 'ACTIVE'
        }

        response = admin_client.put(f'/api/v1/stores/{store.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

    def test_partial_update_store(self, admin_client, create_store):
        """Test partial update of a store."""
        store = create_store(name='Original', code='S005')

        response = admin_client.patch(f'/api/v1/stores/{store.id}/', {'name': 'Patched'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Patched'

    def test_delete_store(self, admin_client, create_store):
        """Test deleting a store."""
        store = create_store(name='To Delete', code='S006')

        response = admin_client.delete(f'/api/v1/stores/{store.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_stores_by_status(self, admin_client, create_store):
        """Test filtering stores by status."""
        create_store(name='Active Store', code='S007', status='ACTIVE')

        response = admin_client.get('/api/v1/stores/?status=ACTIVE')

        assert response.status_code == status.HTTP_200_OK

    def test_store_summary(self, admin_client, create_store):
        """Test getting store summary."""
        store = create_store(name='Summary Store', code='S008')

        response = admin_client.get(f'/api/v1/stores/{store.id}/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert 'store_id' in response.data['data']
        assert response.data['data']['store_name'] == 'Summary Store'

    def test_store_warehouses(self, admin_client, create_store, create_warehouse):
        """Test getting store warehouses."""
        store = create_store(name='WH Store', code='S009')
        create_warehouse(name='Store WH 1', code='SWH001', store=store)
        create_warehouse(name='Store WH 2', code='SWH002', store=store)

        response = admin_client.get(f'/api/v1/stores/{store.id}/warehouses/')

        assert response.status_code == status.HTTP_200_OK

    def test_search_stores(self, admin_client, create_store):
        """Test searching stores by name."""
        create_store(name='Searchable Store', code='SEARCH01')

        response = admin_client.get('/api/v1/stores/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestWarehouseViewSet:
    """Tests for WarehouseViewSet."""

    def test_list_warehouses(self, admin_client, create_warehouse):
        """Test listing warehouses."""
        create_warehouse(name='Warehouse 1', code='WH001')

        response = admin_client.get('/api/v1/warehouses/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_warehouse_detail(self, admin_client, create_warehouse):
        """Test getting warehouse detail."""
        warehouse = create_warehouse(name='Test WH', code='WH002')

        response = admin_client.get(f'/api/v1/warehouses/{warehouse.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test WH'

    def test_create_warehouse(self, admin_client, store):
        """Test creating a warehouse."""
        data = {
            'name': 'New Warehouse',
            'code': 'WH003',
            'store': store.id,
            'warehouse_type': 'STORE',
            'is_default': False
        }

        response = admin_client.post('/api/v1/warehouses/', data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_update_warehouse(self, admin_client, create_warehouse):
        """Test updating a warehouse."""
        warehouse = create_warehouse(name='Old WH', code='WH004')

        data = {
            'name': 'Updated WH',
            'code': 'WH004',
            'store': warehouse.store.id,
            'warehouse_type': 'STORE',
            'is_default': False
        }

        response = admin_client.put(f'/api/v1/warehouses/{warehouse.id}/', data)

        assert response.status_code == status.HTTP_200_OK

    def test_delete_warehouse(self, admin_client, create_warehouse):
        """Test deleting a warehouse."""
        warehouse = create_warehouse(name='To Delete WH', code='WH005')

        response = admin_client.delete(f'/api/v1/warehouses/{warehouse.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_warehouses_by_store(self, admin_client, store, create_warehouse):
        """Test filtering warehouses by store."""
        create_warehouse(name='Filter WH', code='WH006', store=store)

        response = admin_client.get(f'/api/v1/warehouses/?store={store.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_warehouses_by_type(self, admin_client, create_warehouse):
        """Test filtering warehouses by type."""
        create_warehouse(name='Store WH', code='WH007', warehouse_type='STORE')

        response = admin_client.get('/api/v1/warehouses/?warehouse_type=STORE')

        assert response.status_code == status.HTTP_200_OK

    def test_set_default_warehouse(self, admin_client, create_warehouse):
        """Test setting a warehouse as default."""
        warehouse = create_warehouse(name='Default WH', code='WH008', is_default=False)

        response = admin_client.post(f'/api/v1/warehouses/{warehouse.id}/set_default/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_search_warehouses(self, admin_client, create_warehouse):
        """Test searching warehouses."""
        create_warehouse(name='Searchable Warehouse', code='WHSEARCH01')

        response = admin_client.get('/api/v1/warehouses/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_warehouses_by_is_active(self, admin_client, create_warehouse):
        """Test filtering warehouses by is_active."""
        create_warehouse(name='Active WH', code='WH009', is_active=True)

        response = admin_client.get('/api/v1/warehouses/?is_active=true')

        assert response.status_code == status.HTTP_200_OK
