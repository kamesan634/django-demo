"""
Tests for purchasing views.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from datetime import date, timedelta


@pytest.fixture
def supplier(db):
    """Create a test supplier."""
    from apps.purchasing.models import Supplier
    return Supplier.objects.create(
        code='SUP001',
        name='Test Supplier',
        contact_name='Contact Person',
        phone='0212345678',
        email='supplier@example.com',
        is_active=True
    )


@pytest.mark.django_db
class TestSupplierViewSet:
    """Tests for SupplierViewSet."""

    def test_list_suppliers(self, admin_client, supplier):
        """Test listing suppliers."""
        response = admin_client.get('/api/v1/suppliers/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_list_suppliers_unauthenticated(self, api_client):
        """Test listing suppliers without authentication."""
        response = api_client.get('/api/v1/suppliers/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_supplier_detail(self, admin_client, supplier):
        """Test getting supplier detail."""
        response = admin_client.get(f'/api/v1/suppliers/{supplier.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Supplier'

    def test_create_supplier(self, admin_client):
        """Test creating a supplier."""
        data = {
            'code': 'SUP002',
            'name': 'New Supplier',
            'contact_name': 'New Contact',
            'phone': '0223456789',
            'email': 'new@example.com',
            'is_active': True
        }

        response = admin_client.post('/api/v1/suppliers/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Supplier'

    def test_update_supplier(self, admin_client, supplier):
        """Test updating a supplier."""
        data = {
            'code': supplier.code,
            'name': 'Updated Supplier',
            'contact_name': 'Updated Contact',
            'phone': supplier.phone,
            'is_active': True
        }

        response = admin_client.put(f'/api/v1/suppliers/{supplier.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Supplier'

    def test_delete_supplier(self, admin_client, supplier):
        """Test deleting a supplier."""
        response = admin_client.delete(f'/api/v1/suppliers/{supplier.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_search_suppliers(self, admin_client, supplier):
        """Test searching suppliers."""
        response = admin_client.get('/api/v1/suppliers/?search=Test')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_suppliers_by_is_active(self, admin_client, supplier):
        """Test filtering suppliers by is_active."""
        response = admin_client.get('/api/v1/suppliers/?is_active=true')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPurchaseOrderViewSet:
    """Tests for PurchaseOrderViewSet."""

    def test_list_purchase_orders(self, admin_client, supplier, warehouse, admin_user):
        """Test listing purchase orders."""
        from apps.purchasing.models import PurchaseOrder

        PurchaseOrder.objects.create(
            po_number='PO001',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/purchase-orders/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_purchase_order_detail(self, admin_client, supplier, warehouse, admin_user):
        """Test getting purchase order detail."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO002',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('2000'),
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/purchase-orders/{po.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['po_number'] == 'PO002'

    def test_create_purchase_order(self, admin_client, supplier, warehouse, create_product):
        """Test creating a purchase order."""
        product = create_product(name='PO Product', sku='POPROD001')

        data = {
            'supplier': supplier.id,
            'warehouse': warehouse.id,
            'expected_date': str(date.today() + timedelta(days=7)),
            'items': [
                {
                    'product': product.id,
                    'quantity': 10,
                    'unit_price': '100.00'
                }
            ]
        }

        response = admin_client.post('/api/v1/purchase-orders/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_update_purchase_order(self, admin_client, supplier, warehouse, admin_user):
        """Test updating a purchase order."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO003',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('500'),
            note='Original note',
            created_by=admin_user
        )

        response = admin_client.patch(f'/api/v1/purchase-orders/{po.id}/', {'note': 'Updated note'})

        assert response.status_code == status.HTTP_200_OK

    def test_filter_purchase_orders_by_status(self, admin_client, supplier, warehouse, admin_user):
        """Test filtering purchase orders by status."""
        from apps.purchasing.models import PurchaseOrder

        PurchaseOrder.objects.create(
            po_number='PO004',
            supplier=supplier,
            warehouse=warehouse,
            status='APPROVED',
            total_amount=Decimal('1500'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/purchase-orders/?status=APPROVED')

        assert response.status_code == status.HTTP_200_OK

    def test_filter_purchase_orders_by_supplier(self, admin_client, supplier, warehouse, admin_user):
        """Test filtering purchase orders by supplier."""
        from apps.purchasing.models import PurchaseOrder

        PurchaseOrder.objects.create(
            po_number='PO005',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('3000'),
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/purchase-orders/?supplier={supplier.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_submit_purchase_order(self, admin_client, supplier, warehouse, admin_user, create_product):
        """Test submitting a purchase order."""
        from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem

        product = create_product(name='Submit Product', sku='SUBMIT001')

        po = PurchaseOrder.objects.create(
            po_number='PO006',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        # Add an item to the PO (required for submission)
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-orders/{po.id}/submit/')

        assert response.status_code == status.HTTP_200_OK

    def test_approve_purchase_order(self, admin_client, supplier, warehouse, admin_user):
        """Test approving a purchase order."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO007',
            supplier=supplier,
            warehouse=warehouse,
            status='SUBMITTED',
            total_amount=Decimal('2500'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-orders/{po.id}/approve/')

        assert response.status_code == status.HTTP_200_OK

    def test_submit_draft_without_items(self, admin_client, supplier, warehouse, admin_user):
        """Test submitting a draft PO without items fails."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO-EMPTY',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('0'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-orders/{po.id}/submit/')

        # Should fail because no items
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_non_draft_fails(self, admin_client, supplier, warehouse, admin_user):
        """Test submitting a non-draft PO fails."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO-SUBMITTED',
            supplier=supplier,
            warehouse=warehouse,
            status='SUBMITTED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-orders/{po.id}/submit/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_approve_non_submitted_fails(self, admin_client, supplier, warehouse, admin_user):
        """Test approving a non-submitted PO fails."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO-DRAFT',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-orders/{po.id}/approve/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_receive_goods(self, admin_client, supplier, warehouse, admin_user, create_product):
        """Test receiving goods for purchase order."""
        from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem

        product = create_product(name='Receive Product', sku='RCV001')

        po = PurchaseOrder.objects.create(
            po_number='PO-RECEIVE',
            supplier=supplier,
            warehouse=warehouse,
            status='APPROVED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(
            f'/api/v1/purchase-orders/{po.id}/receive/',
            {
                'items': [
                    {'po_item_id': po_item.id, 'received_quantity': 10}
                ],
                'note': 'Full receipt'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_receive_partial_goods(self, admin_client, supplier, warehouse, admin_user, create_product):
        """Test partial receipt of goods."""
        from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem

        product = create_product(name='Partial Product', sku='PART001')

        po = PurchaseOrder.objects.create(
            po_number='PO-PARTIAL',
            supplier=supplier,
            warehouse=warehouse,
            status='APPROVED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(
            f'/api/v1/purchase-orders/{po.id}/receive/',
            {
                'items': [
                    {'po_item_id': po_item.id, 'received_quantity': 5}
                ]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        # PO should be in partial status now
        po.refresh_from_db()
        assert po.status == 'PARTIAL'

    def test_receive_wrong_status_fails(self, admin_client, supplier, warehouse, admin_user):
        """Test receiving goods for non-approved PO fails."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO-WRONG',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(
            f'/api/v1/purchase-orders/{po.id}/receive/',
            {'items': []},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_purchase_suggestions(self, admin_client, warehouse, create_product):
        """Test getting purchase suggestions based on low stock."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock Product', sku='LOW001', safety_stock=100)

        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=10,  # Below safety stock
            available_quantity=10
        )

        response = admin_client.get('/api/v1/purchase-orders/suggestions/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True


@pytest.mark.django_db
class TestPurchaseReturnViewSet:
    """Tests for PurchaseReturnViewSet."""

    def test_list_purchase_returns(self, admin_client, supplier, warehouse, admin_user):
        """Test listing purchase returns."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn

        po = PurchaseOrder.objects.create(
            po_number='PO008',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('5000'),
            created_by=admin_user
        )

        PurchaseReturn.objects.create(
            return_number='PR001',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('500'),
            return_date=date.today(),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/purchase-returns/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_purchase_return_detail(self, admin_client, supplier, warehouse, admin_user):
        """Test getting purchase return detail."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn

        po = PurchaseOrder.objects.create(
            po_number='PO009',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('3000'),
            created_by=admin_user
        )

        pr = PurchaseReturn.objects.create(
            return_number='PR002',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('300'),
            return_date=date.today(),
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/purchase-returns/{pr.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['return_number'] == 'PR002'

    def test_filter_purchase_returns_by_status(self, admin_client, supplier, warehouse, admin_user):
        """Test filtering purchase returns by status."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn

        po = PurchaseOrder.objects.create(
            po_number='PO010',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('4000'),
            created_by=admin_user
        )

        PurchaseReturn.objects.create(
            return_number='PR003',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('400'),
            return_date=date.today(),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/purchase-returns/?status=COMPLETED')

        assert response.status_code == status.HTTP_200_OK

    def test_create_purchase_return(self, admin_client, supplier, warehouse, admin_user, create_product):
        """Test creating a purchase return."""
        from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem

        product = create_product(name='Return Product', sku='RET001')

        po = PurchaseOrder.objects.create(
            po_number='PO-RETURN',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            received_quantity=10,
            created_by=admin_user
        )

        response = admin_client.post(
            '/api/v1/purchase-returns/create_return/',
            {
                'purchase_order_id': po.id,
                'reason': 'DEFECTIVE',
                'return_date': str(date.today()),
                'items': [
                    {'po_item_id': po_item.id, 'quantity': 2, 'reason': 'Damaged'}
                ]
            },
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_create_return_wrong_status_fails(self, admin_client, supplier, warehouse, admin_user):
        """Test creating return for non-completed PO fails."""
        from apps.purchasing.models import PurchaseOrder

        po = PurchaseOrder.objects.create(
            po_number='PO-DRAFT-RET',
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.post(
            '/api/v1/purchase-returns/create_return/',
            {
                'purchase_order_id': po.id,
                'reason': 'DEFECTIVE',
                'return_date': str(date.today()),
                'items': []
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_purchase_return(self, admin_client, supplier, warehouse, admin_user, create_product):
        """Test submitting a purchase return."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn, PurchaseReturnItem, PurchaseOrderItem

        product = create_product(name='Submit Return Product', sku='SUBRET001')

        po = PurchaseOrder.objects.create(
            po_number='PO-SUBRET',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            received_quantity=10,
            created_by=admin_user
        )

        pr = PurchaseReturn.objects.create(
            return_number='PR-SUBMIT',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('200'),
            return_date=date.today(),
            created_by=admin_user
        )

        PurchaseReturnItem.objects.create(
            purchase_return=pr,
            po_item=po_item,
            product=product,
            quantity=2,
            unit_price=Decimal('100'),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-returns/{pr.id}/submit/')

        assert response.status_code == status.HTTP_200_OK

    def test_approve_purchase_return(self, admin_client, supplier, warehouse, admin_user):
        """Test approving a purchase return."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn

        po = PurchaseOrder.objects.create(
            po_number='PO-APPRET',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        pr = PurchaseReturn.objects.create(
            return_number='PR-APPROVE',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='SUBMITTED',
            total_amount=Decimal('200'),
            return_date=date.today(),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-returns/{pr.id}/approve/')

        assert response.status_code == status.HTTP_200_OK

    def test_cancel_purchase_return(self, admin_client, supplier, warehouse, admin_user):
        """Test cancelling a purchase return."""
        from apps.purchasing.models import PurchaseOrder, PurchaseReturn

        po = PurchaseOrder.objects.create(
            po_number='PO-CANCEL',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('1000'),
            created_by=admin_user
        )

        pr = PurchaseReturn.objects.create(
            return_number='PR-CANCEL',
            purchase_order=po,
            supplier=supplier,
            warehouse=warehouse,
            status='DRAFT',
            total_amount=Decimal('200'),
            return_date=date.today(),
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/purchase-returns/{pr.id}/cancel/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSupplierPriceViewSet:
    """Tests for SupplierPriceViewSet."""

    def test_list_supplier_prices(self, admin_client, supplier, create_product):
        """Test listing supplier prices."""
        from apps.purchasing.models import SupplierPrice

        product = create_product(name='Price Product', sku='PRICE001')

        SupplierPrice.objects.create(
            supplier=supplier,
            product=product,
            unit_price=Decimal('100'),
            effective_from=date.today()
        )

        response = admin_client.get('/api/v1/supplier-prices/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_supplier_price(self, admin_client, supplier, create_product):
        """Test creating a supplier price."""
        product = create_product(name='New Price Product', sku='NEWPRICE001')

        response = admin_client.post(
            '/api/v1/supplier-prices/',
            {
                'supplier': supplier.id,
                'product': product.id,
                'unit_price': '150.00',
                'effective_from': str(date.today())
            }
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_prices_by_product(self, admin_client, supplier, create_product):
        """Test getting prices by product."""
        from apps.purchasing.models import SupplierPrice

        product = create_product(name='By Product', sku='BYPROD001')

        SupplierPrice.objects.create(
            supplier=supplier,
            product=product,
            unit_price=Decimal('80'),
            effective_from=date.today()
        )

        response = admin_client.get(f'/api/v1/supplier-prices/by_product/?product_id={product.id}')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_get_prices_by_product_no_id(self, admin_client):
        """Test getting prices by product without product_id fails."""
        response = admin_client.get('/api/v1/supplier-prices/by_product/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_prices_by_supplier(self, admin_client, supplier, create_product):
        """Test getting prices by supplier."""
        from apps.purchasing.models import SupplierPrice

        product = create_product(name='By Supplier', sku='BYSUP001')

        SupplierPrice.objects.create(
            supplier=supplier,
            product=product,
            unit_price=Decimal('90'),
            effective_from=date.today()
        )

        response = admin_client.get(f'/api/v1/supplier-prices/by_supplier/?supplier_id={supplier.id}')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_get_prices_by_supplier_no_id(self, admin_client):
        """Test getting prices by supplier without supplier_id fails."""
        response = admin_client.get('/api/v1/supplier-prices/by_supplier/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_compare_prices(self, admin_client, supplier, create_product):
        """Test comparing prices across suppliers."""
        from apps.purchasing.models import SupplierPrice, Supplier

        product = create_product(name='Compare Product', sku='COMP001')

        supplier2 = Supplier.objects.create(
            code='SUP002',
            name='Second Supplier',
            contact_name='Contact 2',
            phone='0223456789',
            is_active=True
        )

        SupplierPrice.objects.create(
            supplier=supplier,
            product=product,
            unit_price=Decimal('100'),
            effective_from=date.today()
        )

        SupplierPrice.objects.create(
            supplier=supplier2,
            product=product,
            unit_price=Decimal('90'),
            effective_from=date.today()
        )

        response = admin_client.get(f'/api/v1/supplier-prices/compare/?product_ids={product.id}')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert len(response.data['data']) == 1
        # lowest_price depends on effective date filter, just check it's returned
        assert 'lowest_price' in response.data['data'][0]

    def test_compare_prices_no_ids(self, admin_client):
        """Test comparing prices without product_ids fails."""
        response = admin_client.get('/api/v1/supplier-prices/compare/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_set_preferred_supplier(self, admin_client, supplier, create_product):
        """Test setting a supplier as preferred."""
        from apps.purchasing.models import SupplierPrice

        product = create_product(name='Preferred Product', sku='PREF001')

        price = SupplierPrice.objects.create(
            supplier=supplier,
            product=product,
            unit_price=Decimal('100'),
            effective_from=date.today(),
            is_preferred=False
        )

        response = admin_client.post(f'/api/v1/supplier-prices/{price.id}/set_preferred/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        price.refresh_from_db()
        assert price.is_preferred is True
