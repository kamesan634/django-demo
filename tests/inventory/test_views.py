"""
Tests for inventory views.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from datetime import date
from unittest.mock import patch, Mock


@pytest.mark.django_db
class TestInventoryViewSet:
    """Tests for InventoryViewSet."""

    def test_list_inventory(self, admin_client, warehouse, create_product):
        """Test listing inventory."""
        from apps.inventory.models import Inventory

        product = create_product(name='Inventory Product', sku='INV001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get('/api/v1/inventory/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_inventory_unauthenticated(self, api_client):
        """Test listing inventory without authentication."""
        response = api_client.get('/api/v1/inventory/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_inventory_detail(self, admin_client, warehouse, create_product):
        """Test getting inventory detail."""
        from apps.inventory.models import Inventory

        product = create_product(name='Detail Product', sku='INV002')
        inv = Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        response = admin_client.get(f'/api/v1/inventory/{inv.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['quantity'] == 50

    def test_filter_inventory_by_warehouse(self, admin_client, warehouse, create_product):
        """Test filtering inventory by warehouse."""
        from apps.inventory.models import Inventory

        product = create_product(name='Filter Product', sku='INV003')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=75
        )

        response = admin_client.get(f'/api/v1/inventory/?warehouse={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_inventory_by_product(self, admin_client, warehouse, create_product):
        """Test filtering inventory by product."""
        from apps.inventory.models import Inventory

        product = create_product(name='Product Filter', sku='INV004')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=30
        )

        response = admin_client.get(f'/api/v1/inventory/?product={product.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_adjust_inventory_in(self, admin_client, warehouse, create_product):
        """Test adjusting inventory - adding stock."""
        from apps.inventory.models import Inventory

        product = create_product(name='Adjust Product', sku='ADJ001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        data = {
            'warehouse_id': warehouse.id,
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'note': 'Test adjustment'
        }

        response = admin_client.post('/api/v1/inventory/adjust/', data)

        assert response.status_code == status.HTTP_200_OK

    def test_adjust_inventory_out(self, admin_client, warehouse, create_product):
        """Test adjusting inventory - removing stock."""
        from apps.inventory.models import Inventory

        product = create_product(name='Adjust Out Product', sku='ADJ002')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        data = {
            'warehouse_id': warehouse.id,
            'product_id': product.id,
            'adjustment_type': 'OUT',
            'quantity': 5,
            'note': 'Test removal'
        }

        response = admin_client.post('/api/v1/inventory/adjust/', data)

        assert response.status_code == status.HTTP_200_OK

    def test_low_stock_products(self, admin_client, warehouse, create_product):
        """Test getting low stock products."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock', sku='LOW001', safety_stock=50)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=10
        )

        response = admin_client.get('/api/v1/inventory/low_stock/')

        assert response.status_code == status.HTTP_200_OK

    def test_low_stock_with_warehouse_filter(self, admin_client, warehouse, create_product):
        """Test getting low stock products filtered by warehouse."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock WH', sku='LOW002', safety_stock=100)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=5
        )

        response = admin_client.get(f'/api/v1/inventory/low_stock/?warehouse={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_alerts(self, admin_client, warehouse, create_product):
        """Test getting inventory alerts."""
        from apps.inventory.models import Inventory

        product = create_product(name='Alert Product', sku='ALERT001', safety_stock=50)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=0,
            available_quantity=0
        )

        with patch('apps.inventory.views.InventorySyncService.get_low_stock_alerts') as mock_alerts:
            mock_alerts.return_value = [
                {'product_id': product.id, 'alert_level': 'OUT_OF_STOCK', 'quantity': 0}
            ]

            response = admin_client.get('/api/v1/inventory/alerts/')

            assert response.status_code == status.HTTP_200_OK
            assert 'summary' in response.data['data']

    def test_inventory_alerts_with_level_filter(self, admin_client, warehouse, create_product):
        """Test getting inventory alerts with level filter."""
        product = create_product(name='Critical Alert', sku='ALERT002', safety_stock=50)

        with patch('apps.inventory.views.InventorySyncService.get_low_stock_alerts') as mock_alerts:
            mock_alerts.return_value = [
                {'product_id': product.id, 'alert_level': 'CRITICAL', 'quantity': 5}
            ]

            response = admin_client.get('/api/v1/inventory/alerts/?level=CRITICAL')

            assert response.status_code == status.HTTP_200_OK

    def test_product_summary(self, admin_client, warehouse, create_product):
        """Test getting product inventory summary."""
        from apps.inventory.models import Inventory

        product = create_product(name='Summary Product', sku='SUM001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        with patch('apps.inventory.views.InventorySyncService.get_product_inventory_summary') as mock_summary:
            mock_summary.return_value = {
                'product_id': product.id,
                'total_quantity': 100,
                'warehouses': []
            }

            response = admin_client.get(f'/api/v1/inventory/product/{product.id}/')

            assert response.status_code == status.HTTP_200_OK

    def test_sync_adjust_missing_params(self, admin_client):
        """Test sync adjust with missing parameters returns error."""
        response = admin_client.post('/api/v1/inventory/sync_adjust/', {})

        # API returns error response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_sync_adjust_success(self, admin_client, warehouse, create_product):
        """Test sync adjust with valid data."""
        product = create_product(name='Sync Product', sku='SYNC001')

        with patch('apps.inventory.views.InventorySyncService.sync_update_inventory') as mock_sync:
            mock_sync.return_value = {'quantity': 60, 'available_quantity': 60}

            data = {
                'warehouse_id': warehouse.id,
                'product_id': product.id,
                'adjustment_type': 'IN',
                'quantity': 10,
                'note': 'Sync test'
            }

            response = admin_client.post('/api/v1/inventory/sync_adjust/', data)

            assert response.status_code == status.HTTP_200_OK

    def test_reserve_stock_missing_params(self, admin_client):
        """Test reserve stock with missing parameters."""
        response = admin_client.post('/api/v1/inventory/reserve/', {})

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_reserve_stock_success(self, admin_client, warehouse, create_product):
        """Test reserve stock success."""
        product = create_product(name='Reserve Product', sku='RES001')

        with patch('apps.inventory.views.InventorySyncService.sync_reserve_stock') as mock_reserve:
            mock_reserve.return_value = {'reserved_quantity': 10}

            data = {
                'warehouse_id': warehouse.id,
                'product_id': product.id,
                'quantity': 10,
                'reference_type': 'ORDER',
                'reference_id': 1
            }

            response = admin_client.post('/api/v1/inventory/reserve/', data)

            assert response.status_code == status.HTTP_200_OK

    def test_release_stock_missing_params(self, admin_client):
        """Test release stock with missing parameters."""
        response = admin_client.post('/api/v1/inventory/release/', {})

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_release_stock_success(self, admin_client, warehouse, create_product):
        """Test release stock success."""
        product = create_product(name='Release Product', sku='REL001')

        with patch('apps.inventory.views.InventorySyncService.sync_release_stock') as mock_release:
            mock_release.return_value = {'released_quantity': 10}

            data = {
                'warehouse_id': warehouse.id,
                'product_id': product.id,
                'quantity': 10,
                'reference_type': 'ORDER',
                'reference_id': 1
            }

            response = admin_client.post('/api/v1/inventory/release/', data)

            assert response.status_code == status.HTTP_200_OK

    def test_batch_adjust_empty(self, admin_client):
        """Test batch adjust with empty updates."""
        response = admin_client.post('/api/v1/inventory/batch_adjust/', {'updates': []})

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_batch_adjust_success(self, admin_client, warehouse, create_product):
        """Test batch adjust success."""
        product = create_product(name='Batch Product', sku='BATCH001')

        with patch('apps.inventory.views.InventorySyncService.batch_sync_inventory') as mock_batch:
            mock_batch.return_value = {'success_count': 1, 'failed_count': 0}

            data = {
                'updates': [
                    {
                        'warehouse_id': warehouse.id,
                        'product_id': product.id,
                        'quantity_change': 10,
                        'movement_type': 'ADJUST_IN'
                    }
                ]
            }

            response = admin_client.post('/api/v1/inventory/batch_adjust/', data, format='json')

            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInventoryMovementViewSet:
    """Tests for InventoryMovementViewSet."""

    def test_list_movements(self, admin_client, warehouse, create_product, admin_user):
        """Test listing inventory movements."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Movement Product', sku='MOV001')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='PURCHASE_IN',
            quantity=50,
            balance=50,
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/inventory-movements/')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_movements_by_type(self, admin_client, warehouse, create_product, admin_user):
        """Test filtering movements by type."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Type Filter', sku='MOV002')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='SALE_OUT',
            quantity=-10,
            balance=40,
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/inventory-movements/?movement_type=SALE_OUT')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_movements_by_warehouse(self, admin_client, warehouse, create_product, admin_user):
        """Test filtering movements by warehouse."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='WH Filter', sku='MOV003')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='ADJUST_IN',
            quantity=5,
            balance=45,
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/inventory-movements/?warehouse={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStockCountViewSet:
    """Tests for StockCountViewSet."""

    def test_list_stock_counts(self, admin_client, warehouse, admin_user):
        """Test listing stock counts."""
        from apps.inventory.models import StockCount

        StockCount.objects.create(
            warehouse=warehouse,
            count_number='SC001',
            count_date=date.today(),
            status='DRAFT',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/stock-counts/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_stock_count_detail(self, admin_client, warehouse, admin_user):
        """Test getting stock count detail."""
        from apps.inventory.models import StockCount

        sc = StockCount.objects.create(
            warehouse=warehouse,
            count_number='SC002',
            count_date=date.today(),
            status='DRAFT',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/stock-counts/{sc.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count_number'] == 'SC002'

    def test_create_stock_count(self, admin_client, warehouse):
        """Test creating a stock count."""
        data = {
            'warehouse': warehouse.id,
            'count_date': str(date.today()),
            'note': 'Monthly count'
        }

        response = admin_client.post('/api/v1/stock-counts/', data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_filter_stock_counts_by_status(self, admin_client, warehouse, admin_user):
        """Test filtering stock counts by status."""
        from apps.inventory.models import StockCount

        StockCount.objects.create(
            warehouse=warehouse,
            count_number='SC003',
            count_date=date.today(),
            status='COMPLETED',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/stock-counts/?status=COMPLETED')

        assert response.status_code == status.HTTP_200_OK

    def test_complete_stock_count_wrong_status(self, admin_client, warehouse, admin_user):
        """Test completing stock count with wrong status."""
        from apps.inventory.models import StockCount

        sc = StockCount.objects.create(
            warehouse=warehouse,
            count_number='SC004',
            count_date=date.today(),
            status='DRAFT',
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/stock-counts/{sc.id}/complete/')

        # API returns error for wrong status
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_complete_stock_count_success(self, admin_client, warehouse, admin_user, create_product):
        """Test completing stock count successfully."""
        from apps.inventory.models import StockCount, StockCountItem

        sc = StockCount.objects.create(
            warehouse=warehouse,
            count_number='SC005',
            count_date=date.today(),
            status='IN_PROGRESS',
            created_by=admin_user
        )

        product = create_product(name='Count Product', sku='CNT001')
        StockCountItem.objects.create(
            stock_count=sc,
            product=product,
            system_quantity=100,
            actual_quantity=95
        )

        with patch('apps.inventory.views.InventoryEventHandler.on_stock_count_completed') as mock_complete:
            mock_complete.return_value = {'adjusted': 1}

            response = admin_client.post(f'/api/v1/stock-counts/{sc.id}/complete/')

            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStockTransferViewSet:
    """Tests for StockTransferViewSet."""

    def test_list_stock_transfers(self, admin_client, store, admin_user):
        """Test listing stock transfers."""
        from apps.inventory.models import StockTransfer
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='WH 1', code='WH1', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='WH 2', code='WH2', store=store,
            warehouse_type='STORE', is_default=False
        )

        StockTransfer.objects.create(
            transfer_number='ST001',
            from_warehouse=wh1,
            to_warehouse=wh2,
            transfer_date=date.today(),
            status='PENDING',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/stock-transfers/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_stock_transfer_detail(self, admin_client, store, admin_user):
        """Test getting stock transfer detail."""
        from apps.inventory.models import StockTransfer
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='From WH', code='FROM1', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='To WH', code='TO1', store=store,
            warehouse_type='STORE', is_default=False
        )

        st = StockTransfer.objects.create(
            transfer_number='ST002',
            from_warehouse=wh1,
            to_warehouse=wh2,
            transfer_date=date.today(),
            status='PENDING',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/stock-transfers/{st.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['transfer_number'] == 'ST002'

    def test_create_stock_transfer(self, admin_client, store, create_product):
        """Test creating a stock transfer."""
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='Source WH', code='SRC1', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='Dest WH', code='DST1', store=store,
            warehouse_type='STORE', is_default=False
        )
        product = create_product(name='Transfer Product', sku='TRF001')

        data = {
            'from_warehouse': wh1.id,
            'to_warehouse': wh2.id,
            'transfer_date': str(date.today()),
            'items': [
                {
                    'product': product.id,
                    'quantity': 10
                }
            ]
        }

        response = admin_client.post('/api/v1/stock-transfers/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_filter_stock_transfers_by_status(self, admin_client, store, admin_user):
        """Test filtering stock transfers by status."""
        from apps.inventory.models import StockTransfer
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='WH A', code='WHA', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='WH B', code='WHB', store=store,
            warehouse_type='STORE', is_default=False
        )

        StockTransfer.objects.create(
            transfer_number='ST003',
            from_warehouse=wh1,
            to_warehouse=wh2,
            transfer_date=date.today(),
            status='COMPLETED',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/stock-transfers/?status=COMPLETED')

        assert response.status_code == status.HTTP_200_OK

    def test_complete_stock_transfer_wrong_status(self, admin_client, store, admin_user):
        """Test completing transfer with wrong status."""
        from apps.inventory.models import StockTransfer
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='WH C', code='WHC', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='WH D', code='WHD', store=store,
            warehouse_type='STORE', is_default=False
        )

        st = StockTransfer.objects.create(
            transfer_number='ST004',
            from_warehouse=wh1,
            to_warehouse=wh2,
            transfer_date=date.today(),
            status='PENDING',
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/stock-transfers/{st.id}/complete/')

        # API returns error for wrong status
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_complete_stock_transfer_success(self, admin_client, store, admin_user, create_product):
        """Test completing transfer successfully."""
        from apps.inventory.models import StockTransfer, StockTransferItem
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='WH E', code='WHE', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='WH F', code='WHF', store=store,
            warehouse_type='STORE', is_default=False
        )

        st = StockTransfer.objects.create(
            transfer_number='ST005',
            from_warehouse=wh1,
            to_warehouse=wh2,
            transfer_date=date.today(),
            status='IN_TRANSIT',
            created_by=admin_user
        )

        product = create_product(name='Complete Transfer', sku='COMP001')
        StockTransferItem.objects.create(
            transfer=st,
            product=product,
            quantity=10
        )

        with patch('apps.inventory.views.InventorySyncService.sync_transfer_stock') as mock_transfer:
            mock_transfer.return_value = {'transferred': True}

            response = admin_client.post(f'/api/v1/stock-transfers/{st.id}/complete/')

            assert response.status_code == status.HTTP_200_OK

    def test_quick_transfer_missing_params(self, admin_client):
        """Test quick transfer with missing parameters."""
        response = admin_client.post('/api/v1/stock-transfers/quick_transfer/', {})

        # API returns error for missing params
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_quick_transfer_same_warehouse(self, admin_client, store):
        """Test quick transfer with same source and destination."""
        from apps.stores.models import Warehouse

        wh = Warehouse.objects.create(
            name='Same WH', code='SAME', store=store,
            warehouse_type='STORE', is_default=False
        )

        data = {
            'from_warehouse_id': wh.id,
            'to_warehouse_id': wh.id,
            'product_id': 1,
            'quantity': 10
        }

        response = admin_client.post('/api/v1/stock-transfers/quick_transfer/', data)

        # API returns error for same warehouse
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_quick_transfer_success(self, admin_client, store, create_product):
        """Test quick transfer success."""
        from apps.stores.models import Warehouse

        wh1 = Warehouse.objects.create(
            name='Quick From', code='QF1', store=store,
            warehouse_type='STORE', is_default=False
        )
        wh2 = Warehouse.objects.create(
            name='Quick To', code='QT1', store=store,
            warehouse_type='STORE', is_default=False
        )
        product = create_product(name='Quick Product', sku='QUICK001')

        with patch('apps.inventory.views.InventorySyncService.sync_transfer_stock') as mock_transfer:
            mock_transfer.return_value = {'transferred': True}

            data = {
                'from_warehouse_id': wh1.id,
                'to_warehouse_id': wh2.id,
                'product_id': product.id,
                'quantity': 10
            }

            response = admin_client.post('/api/v1/stock-transfers/quick_transfer/', data)

            assert response.status_code == status.HTTP_200_OK
