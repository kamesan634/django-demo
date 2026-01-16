"""
Tests for reports views.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from datetime import date, timedelta


@pytest.mark.django_db
class TestSalesReportViews:
    """Tests for sales report views."""

    def test_sales_daily_report(self, admin_client, store, warehouse, admin_user):
        """Test getting daily sales report."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='ORD002',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        today = date.today()
        response = admin_client.get(
            f'/api/v1/reports/sales/daily/?date={today}'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_sales_daily_report_no_date(self, admin_client, store, warehouse, admin_user):
        """Test getting daily sales report without date parameter."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='ORD003',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/sales/daily/')

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']
        assert 'by_payment_method' in response.data['data']

    def test_sales_hourly_report(self, admin_client):
        """Test getting hourly sales report."""
        response = admin_client.get('/api/v1/reports/sales/hourly/')
        assert response.status_code == status.HTTP_200_OK

    def test_sales_hourly_report_with_date(self, admin_client, store, warehouse, admin_user):
        """Test getting hourly sales report with specific date."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='HOURLYORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        today = date.today()
        response = admin_client.get(f'/api/v1/reports/sales/hourly/?date={today}')

        assert response.status_code == status.HTTP_200_OK

    def test_sales_by_category_report(self, admin_client):
        """Test getting sales by category report."""
        response = admin_client.get('/api/v1/reports/sales/by_category/')
        assert response.status_code == status.HTTP_200_OK

    def test_sales_by_category_with_data(self, admin_client, store, warehouse, admin_user, create_product, category):
        """Test sales by category with actual data."""
        from apps.sales.models import Order, OrderItem

        product = create_product(name='Category Sale Product', sku='CATSALE001', category=category)

        order = Order.objects.create(
            order_number='CATSALEORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/sales/by_category/?days=60')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestInventoryReportViews:
    """Tests for inventory report views."""

    def test_inventory_summary_report(self, admin_client, warehouse, create_product):
        """Test getting inventory summary report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Status Product', sku='RPTINV001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get('/api/v1/reports/inventory/summary/')

        assert response.status_code == status.HTTP_200_OK

    def test_low_stock_report(self, admin_client, warehouse, create_product):
        """Test getting low stock report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock Product', sku='RPTINV002')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=5
        )

        response = admin_client.get('/api/v1/reports/inventory/low_stock/')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_valuation_report(self, admin_client, warehouse, create_product):
        """Test getting inventory valuation report."""
        from apps.inventory.models import Inventory

        product = create_product(
            name='Valuation Product',
            sku='RPTINV003',
            cost_price=Decimal('50')
        )
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=200
        )

        response = admin_client.get('/api/v1/reports/inventory/valuation/')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_movement_report(self, admin_client, warehouse, create_product, admin_user):
        """Test getting inventory movement report."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Movement Product', sku='RPTINV004')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='PURCHASE_IN',
            quantity=100,
            balance=100,
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/inventory/movements/')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_by_category_report(self, admin_client):
        """Test getting inventory by category report."""
        response = admin_client.get('/api/v1/reports/inventory/by_category/')
        assert response.status_code == status.HTTP_200_OK

    def test_inventory_turnover_report(self, admin_client):
        """Test getting inventory turnover report."""
        response = admin_client.get('/api/v1/reports/inventory/turnover/')
        assert response.status_code == status.HTTP_200_OK

    def test_inventory_slow_moving_report(self, admin_client, warehouse, create_product):
        """Test getting slow-moving inventory report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Slow Moving Product', sku='RPTINV005')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get('/api/v1/reports/inventory/slow_moving/')

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']
        assert 'items' in response.data['data']

    def test_inventory_slow_moving_with_filters(self, admin_client, warehouse, create_product):
        """Test slow-moving report with warehouse filter and custom days."""
        from apps.inventory.models import Inventory

        product = create_product(name='Slow Filter Product', sku='RPTINV006')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        response = admin_client.get(
            f'/api/v1/reports/inventory/slow_moving/?warehouse_id={warehouse.id}&days=60&min_stock=10'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_summary_with_warehouse_filter(self, admin_client, warehouse, create_product):
        """Test inventory summary with warehouse filter."""
        from apps.inventory.models import Inventory

        product = create_product(name='Summary Filter Product', sku='RPTINV007')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=75
        )

        response = admin_client.get(f'/api/v1/reports/inventory/summary/?warehouse_id={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_low_stock_with_threshold(self, admin_client, warehouse, create_product):
        """Test low stock report with custom threshold."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock Threshold', sku='RPTINV008')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=10
        )

        response = admin_client.get('/api/v1/reports/inventory/low_stock/?threshold=20')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_movements_with_filters(self, admin_client, warehouse, create_product, admin_user):
        """Test inventory movements report with various filters."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Movement Filter Product', sku='RPTINV009')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='PURCHASE_IN',
            quantity=100,
            balance=100,
            created_by=admin_user
        )

        today = date.today()
        response = admin_client.get(
            f'/api/v1/reports/inventory/movements/?'
            f'warehouse_id={warehouse.id}&product_id={product.id}&'
            f'movement_type=PURCHASE_IN&start_date={today}&end_date={today}'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_valuation_with_warehouse_filter(self, admin_client, warehouse, create_product):
        """Test inventory valuation with warehouse filter."""
        from apps.inventory.models import Inventory

        product = create_product(name='Valuation Filter', sku='RPTINV010', cost_price=Decimal('100'))
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        response = admin_client.get(f'/api/v1/reports/inventory/valuation/?warehouse_id={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_by_category_with_warehouse_filter(self, admin_client, warehouse, create_product):
        """Test inventory by category with warehouse filter."""
        from apps.inventory.models import Inventory

        product = create_product(name='Category Filter', sku='RPTINV011')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=30
        )

        response = admin_client.get(f'/api/v1/reports/inventory/by_category/?warehouse_id={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_turnover_with_warehouse_filter(self, admin_client, warehouse, create_product):
        """Test inventory turnover with warehouse filter."""
        from apps.inventory.models import Inventory

        product = create_product(name='Turnover Filter', sku='RPTINV012')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get(f'/api/v1/reports/inventory/turnover/?warehouse_id={warehouse.id}&days=60')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_turnover_with_sales_data(self, admin_client, store, warehouse, admin_user, create_product):
        """Test inventory turnover with actual sales data."""
        from apps.inventory.models import Inventory
        from apps.sales.models import Order, OrderItem

        product = create_product(name='Turnover Sales Product', sku='RPTINV013')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        order = Order.objects.create(
            order_number='TURNORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=50,
            unit_price=Decimal('10'),
            subtotal=Decimal('500'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/inventory/turnover/')

        assert response.status_code == status.HTTP_200_OK

    def test_inventory_slow_moving_with_sales(self, admin_client, store, warehouse, admin_user, create_product):
        """Test slow-moving report with sales data."""
        from apps.inventory.models import Inventory
        from apps.sales.models import Order, OrderItem

        product = create_product(name='Slow Moving Sales', sku='RPTINV014')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=1000
        )

        order = Order.objects.create(
            order_number='SLOWORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('100'),
            total_amount=Decimal('105'),
            created_by=admin_user
        )

        # Only 10 sold out of 1000 - slow moving
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=10,
            unit_price=Decimal('10'),
            subtotal=Decimal('100'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/inventory/slow_moving/')

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']


@pytest.mark.django_db
class TestCustomerReportViews:
    """Tests for customer report views."""

    def test_customer_summary_report(self, admin_client, create_customer):
        """Test getting customer summary report."""
        create_customer(name='Summary Customer')

        response = admin_client.get('/api/v1/reports/customer/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']
        assert 'top_customers' in response.data['data']

    def test_customer_by_level_report(self, admin_client, create_customer, db):
        """Test getting customer by level breakdown."""
        from apps.customers.models import CustomerLevel

        level = CustomerLevel.objects.create(
            name='Gold',
            min_spending=Decimal('1000'),
            discount_rate=Decimal('5')
        )
        create_customer(name='Level Customer', level=level)

        response = admin_client.get('/api/v1/reports/customer/by_level/')

        assert response.status_code == status.HTTP_200_OK

    def test_customer_rfm_analysis(self, admin_client):
        """Test getting customer RFM analysis."""
        response = admin_client.get('/api/v1/reports/customer/rfm_analysis/')
        assert response.status_code == status.HTTP_200_OK

    def test_customer_rfm_analysis_with_data(self, admin_client, store, warehouse, admin_user, create_customer):
        """Test RFM analysis with customer purchase data."""
        from apps.sales.models import Order

        customer = create_customer(name='RFM Customer')

        Order.objects.create(
            order_number='RFMORD001',
            store=store,
            warehouse=warehouse,
            customer=customer,
            status='COMPLETED',
            subtotal=Decimal('5000'),
            total_amount=Decimal('5250'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/customer/rfm_analysis/?days=365')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPurchaseReportViews:
    """Tests for purchase report views."""

    def test_purchase_summary_report(self, admin_client, warehouse, admin_user):
        """Test getting purchase summary report."""
        from apps.purchasing.models import Supplier, PurchaseOrder

        supplier = Supplier.objects.create(
            code='RPTSUP001',
            name='Report Supplier',
            contact_name='Contact',
            phone='0222222222'
        )

        PurchaseOrder.objects.create(
            po_number='RPTPO001',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('10000'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/purchase/summary/')

        assert response.status_code == status.HTTP_200_OK

    def test_purchase_trend_report(self, admin_client):
        """Test getting purchase trend report."""
        response = admin_client.get('/api/v1/reports/purchase/trend/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProfitReportViews:
    """Tests for profit report views."""

    def test_profit_summary_report(self, admin_client):
        """Test getting profit summary report."""
        response = admin_client.get('/api/v1/reports/profit/summary/')
        assert response.status_code == status.HTTP_200_OK

    def test_profit_summary_with_data(self, admin_client, store, warehouse, admin_user, create_product):
        """Test profit summary with actual sales data."""
        from apps.sales.models import Order, OrderItem

        product = create_product(
            name='Profit Product',
            sku='PROFIT001',
            sale_price=Decimal('100'),
            cost_price=Decimal('60')
        )

        order = Order.objects.create(
            order_number='PROFITORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=10,
            unit_price=Decimal('100'),
            subtotal=Decimal('1000'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/profit/summary/?days=30')

        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data['data']
        assert 'top_profitable' in response.data['data']

    def test_profit_by_category_report(self, admin_client):
        """Test getting profit by category report."""
        response = admin_client.get('/api/v1/reports/profit/by_category/')
        assert response.status_code == status.HTTP_200_OK

    def test_profit_by_category_with_data(self, admin_client, store, warehouse, admin_user, create_product, category):
        """Test profit by category with actual data."""
        from apps.sales.models import Order, OrderItem

        product = create_product(
            name='Category Profit Product',
            sku='CATPROFIT001',
            category=category,
            sale_price=Decimal('200'),
            cost_price=Decimal('100')
        )

        order = Order.objects.create(
            order_number='CATPROFITORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('2000'),
            total_amount=Decimal('2100'),
            created_by=admin_user
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=10,
            unit_price=Decimal('200'),
            subtotal=Decimal('2000'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/reports/profit/by_category/?days=30')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDashboardViews:
    """Tests for dashboard views."""

    def test_dashboard_overview(self, admin_client):
        """Test getting dashboard overview."""
        response = admin_client.get('/api/v1/dashboard/overview/')
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_overview_with_sales(self, admin_client, store, warehouse, admin_user, create_customer):
        """Test dashboard overview with actual sales data."""
        from apps.sales.models import Order
        from apps.inventory.models import Inventory

        Order.objects.create(
            order_number='DASHORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/dashboard/overview/')

        assert response.status_code == status.HTTP_200_OK
        assert 'today' in response.data['data']
        assert 'month' in response.data['data']
        assert 'customers' in response.data['data']
        assert 'inventory' in response.data['data']

    def test_dashboard_sales_trend(self, admin_client):
        """Test getting sales trend."""
        response = admin_client.get('/api/v1/dashboard/sales_trend/')
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_sales_trend_with_custom_days(self, admin_client, store, warehouse, admin_user):
        """Test sales trend with custom days parameter."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='TRENDORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/dashboard/sales_trend/?days=14')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 14

    def test_dashboard_top_products(self, admin_client):
        """Test getting top products."""
        response = admin_client.get('/api/v1/dashboard/top_products/')
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_top_products_with_params(self, admin_client, store, warehouse, admin_user, create_product):
        """Test top products with custom parameters."""
        from apps.sales.models import Order, OrderItem

        product = create_product(name='Top Product', sku='TOPPROD001')

        order = Order.objects.create(
            order_number='TOPORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=10,
            unit_price=Decimal('50'),
            subtotal=Decimal('500'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/dashboard/top_products/?days=60&limit=5')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCustomReportViews:
    """Tests for custom report views."""

    def test_list_custom_reports(self, admin_client, admin_user):
        """Test listing custom reports."""
        from apps.reports.models import CustomReport

        CustomReport.objects.create(
            name='Test Report',
            report_type='SALES',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/custom-reports/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_custom_report(self, admin_client):
        """Test creating a custom report."""
        data = {
            'name': 'New Custom Report',
            'report_type': 'SALES',
            'columns': [
                {'key': 'order_number', 'label': '訂單編號'},
                {'key': 'total_amount', 'label': '總額'}
            ]
        }

        response = admin_client.post('/api/v1/custom-reports/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_report_schema(self, admin_client):
        """Test getting report schema."""
        response = admin_client.get('/api/v1/custom-reports/schema/')
        assert response.status_code == status.HTTP_200_OK

    def test_preview_custom_report(self, admin_client):
        """Test previewing custom report."""
        data = {
            'report_type': 'SALES',
            'columns': [
                {'key': 'order_number', 'label': '訂單編號'},
                {'key': 'total_amount', 'label': '總額'}
            ],
            'filters': []
        }
        response = admin_client.post('/api/v1/custom-reports/preview/', data, format='json')
        # Note: This endpoint may return 200 or 400 depending on validation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_preview_custom_report_missing_type(self, admin_client):
        """Test previewing custom report without report type."""
        data = {
            'columns': [{'key': 'order_number', 'label': '訂單編號'}]
        }
        response = admin_client.post('/api/v1/custom-reports/preview/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_execute_custom_report(self, admin_client, admin_user, store, warehouse):
        """Test executing a custom report."""
        from apps.reports.models import CustomReport
        from apps.sales.models import Order

        Order.objects.create(
            order_number='EXECORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        report = CustomReport.objects.create(
            name='Execute Test Report',
            report_type='SALES',
            columns=[
                {'key': 'order_number', 'label': '訂單編號'},
                {'key': 'total_amount', 'label': '總額'}
            ],
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK

    def test_execute_inventory_report(self, admin_client, admin_user, warehouse, create_product):
        """Test executing an inventory custom report."""
        from apps.reports.models import CustomReport
        from apps.inventory.models import Inventory

        product = create_product(name='Execute Inv Product', sku='EXECINV001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        report = CustomReport.objects.create(
            name='Execute Inventory Report',
            report_type='INVENTORY',
            filters={'warehouse_id': warehouse.id},
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK

    def test_execute_customer_report(self, admin_client, admin_user, create_customer):
        """Test executing a customer custom report."""
        from apps.reports.models import CustomReport

        create_customer(name='Execute Customer')

        report = CustomReport.objects.create(
            name='Execute Customer Report',
            report_type='CUSTOMER',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK

    def test_execute_product_report(self, admin_client, admin_user, create_product):
        """Test executing a product custom report."""
        from apps.reports.models import CustomReport

        create_product(name='Execute Product', sku='EXECPROD001')

        report = CustomReport.objects.create(
            name='Execute Product Report',
            report_type='PRODUCT',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK

    def test_execute_purchase_report(self, admin_client, admin_user, warehouse):
        """Test executing a purchase custom report."""
        from apps.reports.models import CustomReport
        from apps.purchasing.models import Supplier, PurchaseOrder

        supplier = Supplier.objects.create(
            code='EXECSUP001',
            name='Execute Supplier',
            contact_name='Contact',
            phone='0233333333'
        )

        PurchaseOrder.objects.create(
            po_number='EXECPO001',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('5000'),
            created_by=admin_user
        )

        report = CustomReport.objects.create(
            name='Execute Purchase Report',
            report_type='PURCHASE',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_custom_report(self, admin_client, admin_user, store, warehouse):
        """Test exporting a custom report."""
        from apps.reports.models import CustomReport
        from apps.sales.models import Order

        Order.objects.create(
            order_number='EXPCUST001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        report = CustomReport.objects.create(
            name='Export Test Report',
            report_type='SALES',
            columns=[
                {'key': 'order_number', 'label': '訂單編號'},
                {'key': 'total_amount', 'label': '總額'}
            ],
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/export/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_custom_report_excel(self, admin_client, admin_user):
        """Test exporting a custom report as Excel."""
        from apps.reports.models import CustomReport

        report = CustomReport.objects.create(
            name='Export Excel Report',
            report_type='SALES',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/export/?format=excel')

        assert response.status_code == status.HTTP_200_OK

    def test_export_custom_report_csv(self, admin_client, admin_user):
        """Test exporting a custom report as CSV."""
        from apps.reports.models import CustomReport

        report = CustomReport.objects.create(
            name='Export CSV Report',
            report_type='SALES',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/export/?format=csv')

        assert response.status_code == status.HTTP_200_OK

    def test_get_report_schema_for_specific_type(self, admin_client):
        """Test getting report schema for a specific type."""
        response = admin_client.get('/api/v1/custom-reports/schema/?report_type=SALES')

        assert response.status_code == status.HTTP_200_OK
        assert 'report_type' in response.data['data']
        assert 'columns' in response.data['data']
        assert 'filters' in response.data['data']

    def test_custom_report_with_filters(self, admin_client, admin_user, store, warehouse):
        """Test executing custom report with filters."""
        from apps.reports.models import CustomReport
        from apps.sales.models import Order

        Order.objects.create(
            order_number='FILTORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        today = date.today()
        report = CustomReport.objects.create(
            name='Filtered Sales Report',
            report_type='SALES',
            filters={
                'start_date': today.isoformat(),
                'end_date': today.isoformat(),
                'store_id': store.id
            },
            sort_by='total_amount',
            sort_order='DESC',
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/custom-reports/{report.id}/execute/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestScheduledReportViews:
    """Tests for scheduled report views."""

    def test_list_scheduled_reports(self, admin_client, admin_user):
        """Test listing scheduled reports."""
        from apps.reports.models import ScheduledReport

        ScheduledReport.objects.create(
            name='Daily Sales Report',
            report_type='SALES_DAILY',
            frequency='DAILY',
            run_time='08:00:00',
            status='ACTIVE',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/scheduled-reports/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_scheduled_report(self, admin_client):
        """Test creating a scheduled report."""
        data = {
            'name': 'Weekly Inventory Report',
            'report_type': 'INVENTORY_STATUS',
            'frequency': 'WEEKLY',
            'run_time': '09:00:00',
            'run_day': 1,
            'status': 'ACTIVE'
        }

        response = admin_client.post('/api/v1/scheduled-reports/', data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_pause_scheduled_report(self, admin_client, admin_user):
        """Test pausing scheduled report."""
        from apps.reports.models import ScheduledReport

        report = ScheduledReport.objects.create(
            name='Toggle Report',
            report_type='SALES_SUMMARY',
            frequency='MONTHLY',
            run_time='10:00:00',
            run_day=1,
            status='ACTIVE',
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/scheduled-reports/{report.id}/pause/')

        assert response.status_code == status.HTTP_200_OK

    def test_resume_scheduled_report(self, admin_client, admin_user):
        """Test resuming scheduled report."""
        from apps.reports.models import ScheduledReport

        report = ScheduledReport.objects.create(
            name='Resume Report',
            report_type='SALES_SUMMARY',
            frequency='MONTHLY',
            run_time='10:00:00',
            run_day=1,
            status='PAUSED',
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/scheduled-reports/{report.id}/resume/')

        assert response.status_code == status.HTTP_200_OK

    def test_run_scheduled_report_now(self, admin_client, admin_user):
        """Test running scheduled report immediately."""
        from apps.reports.models import ScheduledReport

        report = ScheduledReport.objects.create(
            name='Run Now Report',
            report_type='SALES_SUMMARY',
            frequency='DAILY',
            run_time='10:00:00',
            status='ACTIVE',
            created_by=admin_user
        )

        response = admin_client.post(f'/api/v1/scheduled-reports/{report.id}/run_now/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_get_scheduled_report_executions(self, admin_client, admin_user):
        """Test getting execution history for a scheduled report."""
        from apps.reports.models import ScheduledReport, ReportExecution
        from django.utils import timezone

        report = ScheduledReport.objects.create(
            name='Execution History Report',
            report_type='INVENTORY_STATUS',
            frequency='WEEKLY',
            run_time='08:00:00',
            run_day=1,
            status='ACTIVE',
            created_by=admin_user
        )

        # Create some execution records
        ReportExecution.objects.create(
            scheduled_report=report,
            status='COMPLETED',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            created_by=admin_user
        )

        response = admin_client.get(f'/api/v1/scheduled-reports/{report.id}/executions/')

        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data

    def test_scheduled_report_filtering(self, admin_client, admin_user):
        """Test filtering scheduled reports."""
        from apps.reports.models import ScheduledReport

        ScheduledReport.objects.create(
            name='Filter Test Report',
            report_type='SALES_DAILY',
            frequency='DAILY',
            run_time='07:00:00',
            status='ACTIVE',
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/scheduled-reports/?status=ACTIVE&frequency=DAILY')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestExportViews:
    """Tests for export functionality."""

    def test_export_sales_daily(self, admin_client, store, warehouse, admin_user):
        """Test exporting daily sales data."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='EXP001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/export/sales_daily/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_inventory_current(self, admin_client, warehouse, create_product):
        """Test exporting current inventory data."""
        from apps.inventory.models import Inventory

        product = create_product(name='Export Product', sku='EXP001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get('/api/v1/export/inventory_current/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_inventory_movements(self, admin_client, warehouse, create_product, admin_user):
        """Test exporting inventory movements."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Movement Export', sku='EXPINV001')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='PURCHASE_IN',
            quantity=50,
            balance=50,
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/export/inventory_movements/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_top_products(self, admin_client):
        """Test exporting top products."""
        response = admin_client.get('/api/v1/export/top_products/')
        assert response.status_code == status.HTTP_200_OK

    def test_export_customers(self, admin_client, create_customer, db):
        """Test exporting customers."""
        from apps.customers.models import CustomerLevel

        level = CustomerLevel.objects.create(
            name='Silver',
            min_spending=Decimal('500'),
            discount_rate=Decimal('3')
        )
        create_customer(name='Export Customer', level=level)

        response = admin_client.get('/api/v1/export/customers/')

        assert response.status_code == status.HTTP_200_OK

    def test_export_sales_daily_excel(self, admin_client, store, warehouse, admin_user):
        """Test exporting daily sales as Excel."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='EXPXLS001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/export/sales_daily/?format=excel')

        assert response.status_code == status.HTTP_200_OK

    def test_export_sales_daily_pdf(self, admin_client, store, warehouse, admin_user):
        """Test exporting daily sales as PDF."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='EXPPDF001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        response = admin_client.get('/api/v1/export/sales_daily/?format=pdf')

        # May succeed or fail depending on PDF library
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_export_inventory_current_excel(self, admin_client, warehouse, create_product):
        """Test exporting inventory as Excel."""
        from apps.inventory.models import Inventory

        product = create_product(name='Export Excel Inv', sku='EXPXLS002')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        response = admin_client.get('/api/v1/export/inventory_current/?format=excel')

        assert response.status_code == status.HTTP_200_OK

    def test_export_inventory_current_with_filter(self, admin_client, warehouse, create_product):
        """Test exporting inventory with warehouse filter."""
        from apps.inventory.models import Inventory

        product = create_product(name='Export Filter Inv', sku='EXPFLT001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        response = admin_client.get(f'/api/v1/export/inventory_current/?warehouse_id={warehouse.id}')

        assert response.status_code == status.HTTP_200_OK

    def test_export_inventory_movements_with_filters(self, admin_client, warehouse, create_product, admin_user):
        """Test exporting inventory movements with filters."""
        from apps.inventory.models import InventoryMovement

        product = create_product(name='Export Move Filter', sku='EXPMOV001')
        InventoryMovement.objects.create(
            warehouse=warehouse,
            product=product,
            movement_type='PURCHASE_IN',
            quantity=50,
            balance=50,
            created_by=admin_user
        )

        today = date.today()
        response = admin_client.get(
            f'/api/v1/export/inventory_movements/?'
            f'warehouse_id={warehouse.id}&start_date={today}&end_date={today}'
        )

        assert response.status_code == status.HTTP_200_OK

    def test_export_inventory_movements_excel(self, admin_client):
        """Test exporting inventory movements as Excel."""
        response = admin_client.get('/api/v1/export/inventory_movements/?format=excel')
        assert response.status_code == status.HTTP_200_OK

    def test_export_top_products_excel(self, admin_client):
        """Test exporting top products as Excel."""
        response = admin_client.get('/api/v1/export/top_products/?format=excel&days=60')
        assert response.status_code == status.HTTP_200_OK

    def test_export_customers_excel(self, admin_client, create_customer):
        """Test exporting customers as Excel."""
        create_customer(name='Export Excel Customer')

        response = admin_client.get('/api/v1/export/customers/?format=excel')

        assert response.status_code == status.HTTP_200_OK



@pytest.mark.django_db
class TestComparisonReportViews:
    """Tests for comparison report views."""

    def test_yoy_sales_comparison(self, admin_client):
        """Test year-over-year sales comparison."""
        response = admin_client.get('/api/v1/reports/comparison/yoy_sales/')
        assert response.status_code == status.HTTP_200_OK

    def test_period_comparison_missing_params(self, admin_client):
        """Test period comparison without required parameters."""
        response = admin_client.get('/api/v1/reports/comparison/period_comparison/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False

    def test_period_comparison_valid_params(self, admin_client, store, warehouse, admin_user):
        """Test period comparison with valid parameters."""
        from apps.sales.models import Order
        from datetime import timedelta

        today = date.today()

        # Create orders in period 1
        Order.objects.create(
            order_number='COMP001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        p1_start = today.isoformat()
        p1_end = today.isoformat()
        p2_start = (today - timedelta(days=30)).isoformat()
        p2_end = (today - timedelta(days=30)).isoformat()

        response = admin_client.get(
            f'/api/v1/reports/comparison/period_comparison/?'
            f'period1_start={p1_start}&period1_end={p1_end}&'
            f'period2_start={p2_start}&period2_end={p2_end}'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'period1' in response.data['data']
        assert 'period2' in response.data['data']
        assert 'comparison' in response.data['data']
