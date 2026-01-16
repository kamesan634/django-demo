"""
Tests for reports services.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.utils import timezone

from apps.reports.services import ScheduledReportService, CustomReportBuilder


@pytest.fixture
def mock_custom_report():
    """Create a mock custom report."""
    report = Mock()
    report.report_type = 'SALES'
    report.filters = {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
    report.columns = [
        {'key': 'order_number', 'label': '訂單編號'},
        {'key': 'total_amount', 'label': '總額'},
    ]
    report.sort_by = 'created_at'
    report.sort_order = 'DESC'
    report.name = 'Test Sales Report'
    return report


@pytest.fixture
def mock_schedule():
    """Create a mock schedule."""
    schedule = Mock()
    schedule.name = 'Daily Sales Report'
    schedule.report_type = 'SALES_DAILY'
    schedule.export_format = 'CSV'
    schedule.recipients = ['test@example.com']
    schedule.custom_report = None
    return schedule


@pytest.fixture
def mock_execution():
    """Create a mock execution."""
    execution = Mock()
    execution.recipients_notified = None
    return execution


class TestCustomReportBuilder:
    """Tests for CustomReportBuilder."""

    def test_get_available_columns_sales(self):
        """Test getting available columns for sales report."""
        columns = CustomReportBuilder.get_available_columns('SALES')
        assert len(columns) > 0
        keys = [col['key'] for col in columns]
        assert 'order_number' in keys
        assert 'total_amount' in keys

    def test_get_available_columns_inventory(self):
        """Test getting available columns for inventory report."""
        columns = CustomReportBuilder.get_available_columns('INVENTORY')
        assert len(columns) > 0
        keys = [col['key'] for col in columns]
        assert 'product__sku' in keys
        assert 'quantity' in keys

    def test_get_available_columns_customer(self):
        """Test getting available columns for customer report."""
        columns = CustomReportBuilder.get_available_columns('CUSTOMER')
        assert len(columns) > 0
        # Check that columns exist (regardless of specific key names)
        assert len(columns) >= 3

    def test_get_available_columns_product(self):
        """Test getting available columns for product report."""
        columns = CustomReportBuilder.get_available_columns('PRODUCT')
        assert len(columns) > 0
        keys = [col['key'] for col in columns]
        assert 'sku' in keys
        assert 'name' in keys

    def test_get_available_columns_purchase(self):
        """Test getting available columns for purchase report."""
        columns = CustomReportBuilder.get_available_columns('PURCHASE')
        assert len(columns) > 0
        keys = [col['key'] for col in columns]
        assert 'po_number' in keys
        assert 'supplier__name' in keys

    def test_get_available_columns_unknown_type(self):
        """Test getting columns for unknown report type returns empty."""
        columns = CustomReportBuilder.get_available_columns('UNKNOWN')
        assert columns == []

    def test_get_available_filters_sales(self):
        """Test getting available filters for sales report."""
        filters = CustomReportBuilder.get_available_filters('SALES')
        assert len(filters) > 0
        keys = [f['key'] for f in filters]
        assert 'start_date' in keys
        assert 'end_date' in keys

    def test_get_available_filters_inventory(self):
        """Test getting available filters for inventory report."""
        filters = CustomReportBuilder.get_available_filters('INVENTORY')
        assert len(filters) > 0
        keys = [f['key'] for f in filters]
        assert 'warehouse_id' in keys

    def test_get_available_filters_customer(self):
        """Test getting available filters for customer report."""
        filters = CustomReportBuilder.get_available_filters('CUSTOMER')
        assert len(filters) > 0
        keys = [f['key'] for f in filters]
        assert 'level_id' in keys
        assert 'is_active' in keys

    def test_get_available_filters_product(self):
        """Test getting available filters for product report."""
        filters = CustomReportBuilder.get_available_filters('PRODUCT')
        assert len(filters) > 0
        keys = [f['key'] for f in filters]
        assert 'category_id' in keys
        assert 'status' in keys

    def test_get_available_filters_purchase(self):
        """Test getting available filters for purchase report."""
        filters = CustomReportBuilder.get_available_filters('PURCHASE')
        assert len(filters) > 0
        keys = [f['key'] for f in filters]
        assert 'start_date' in keys
        assert 'supplier_id' in keys

    def test_get_available_filters_unknown_type(self):
        """Test getting filters for unknown report type returns empty."""
        filters = CustomReportBuilder.get_available_filters('UNKNOWN')
        assert filters == []

    def test_validate_columns_valid(self):
        """Test validating valid columns."""
        columns = [{'key': 'order_number'}, {'key': 'total_amount'}]
        assert CustomReportBuilder.validate_columns('SALES', columns) is True

    def test_validate_columns_invalid(self):
        """Test validating invalid columns."""
        columns = [{'key': 'invalid_column'}]
        assert CustomReportBuilder.validate_columns('SALES', columns) is False

    def test_validate_columns_empty(self):
        """Test validating empty columns."""
        assert CustomReportBuilder.validate_columns('SALES', []) is True

    def test_validate_filters_valid(self):
        """Test validating valid filters."""
        filters = {'start_date': '2024-01-01', 'end_date': '2024-01-31'}
        assert CustomReportBuilder.validate_filters('SALES', filters) is True

    def test_validate_filters_invalid(self):
        """Test validating invalid filters."""
        filters = {'invalid_filter': 'value'}
        assert CustomReportBuilder.validate_filters('SALES', filters) is False

    def test_validate_filters_empty(self):
        """Test validating empty filters."""
        assert CustomReportBuilder.validate_filters('SALES', {}) is True


class TestScheduledReportServiceGetDefaultColumns:
    """Tests for ScheduledReportService._get_default_columns."""

    def test_get_default_columns_sales_daily(self):
        """Test getting default columns for daily sales report."""
        columns = ScheduledReportService._get_default_columns('SALES_DAILY')
        assert len(columns) == 4
        keys = [col['key'] for col in columns]
        assert 'date' in keys
        assert 'order_count' in keys

    def test_get_default_columns_sales_summary(self):
        """Test getting default columns for sales summary report."""
        columns = ScheduledReportService._get_default_columns('SALES_SUMMARY')
        assert len(columns) == 4
        keys = [col['key'] for col in columns]
        assert 'store__name' in keys

    def test_get_default_columns_inventory_status(self):
        """Test getting default columns for inventory status report."""
        columns = ScheduledReportService._get_default_columns('INVENTORY_STATUS')
        assert len(columns) == 6
        keys = [col['key'] for col in columns]
        assert 'product__sku' in keys

    def test_get_default_columns_low_stock(self):
        """Test getting default columns for low stock report."""
        columns = ScheduledReportService._get_default_columns('LOW_STOCK')
        assert len(columns) == 5
        keys = [col['key'] for col in columns]
        assert 'available_quantity' in keys

    def test_get_default_columns_purchase_summary(self):
        """Test getting default columns for purchase summary report."""
        columns = ScheduledReportService._get_default_columns('PURCHASE_SUMMARY')
        assert len(columns) == 3
        keys = [col['key'] for col in columns]
        assert 'supplier__name' in keys

    def test_get_default_columns_unknown(self):
        """Test getting default columns for unknown type returns empty."""
        columns = ScheduledReportService._get_default_columns('UNKNOWN')
        assert columns == []


@pytest.mark.django_db
class TestScheduledReportServiceBuiltinReports:
    """Tests for ScheduledReportService built-in report execution."""

    def test_execute_builtin_report_sales_daily(self, store, warehouse, admin_user):
        """Test executing sales daily built-in report."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='ORD001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        data = ScheduledReportService._execute_builtin_report('SALES_DAILY')
        assert isinstance(data, list)

    def test_execute_builtin_report_sales_summary(self, store, warehouse, admin_user):
        """Test executing sales summary built-in report."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='ORD002',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('2000'),
            total_amount=Decimal('2100'),
            created_by=admin_user
        )

        data = ScheduledReportService._execute_builtin_report('SALES_SUMMARY')
        assert isinstance(data, list)

    def test_execute_builtin_report_inventory_status(self, warehouse, create_product):
        """Test executing inventory status built-in report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Test Product', sku='INVSTAT001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        data = ScheduledReportService._execute_builtin_report('INVENTORY_STATUS')
        assert isinstance(data, list)

    def test_execute_builtin_report_low_stock(self, warehouse, create_product):
        """Test executing low stock built-in report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Low Stock Product', sku='LOWSTOCK001', safety_stock=50)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=10,
            available_quantity=10
        )

        data = ScheduledReportService._execute_builtin_report('LOW_STOCK')
        assert isinstance(data, list)

    def test_execute_builtin_report_purchase_summary(self, warehouse, admin_user):
        """Test executing purchase summary built-in report."""
        from apps.purchasing.models import Supplier, PurchaseOrder

        supplier = Supplier.objects.create(
            code='SUP001',
            name='Test Supplier',
            contact_name='Contact',
            phone='0912345678'
        )

        PurchaseOrder.objects.create(
            po_number='PO001',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('5000'),
            created_by=admin_user
        )

        data = ScheduledReportService._execute_builtin_report('PURCHASE_SUMMARY')
        assert isinstance(data, list)

    def test_execute_builtin_report_unknown(self):
        """Test executing unknown report type returns empty list."""
        data = ScheduledReportService._execute_builtin_report('UNKNOWN')
        assert data == []


@pytest.mark.django_db
class TestScheduledReportServiceCustomReports:
    """Tests for ScheduledReportService custom report execution."""

    def test_execute_custom_report_sales(self, store, warehouse, admin_user):
        """Test executing sales custom report."""
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

        custom_report = Mock()
        custom_report.report_type = 'SALES'
        custom_report.filters = {}
        custom_report.sort_by = None
        custom_report.sort_order = None

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert isinstance(data, list)

    def test_execute_custom_report_inventory(self, warehouse, create_product):
        """Test executing inventory custom report."""
        from apps.inventory.models import Inventory

        product = create_product(name='Inv Report Product', sku='INVRPT001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=50
        )

        custom_report = Mock()
        custom_report.report_type = 'INVENTORY'
        custom_report.filters = {'warehouse_id': warehouse.id}

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert isinstance(data, list)

    def test_execute_custom_report_customer(self, create_customer):
        """Test executing customer custom report."""
        create_customer(name='Report Customer')

        custom_report = Mock()
        custom_report.report_type = 'CUSTOMER'
        custom_report.filters = {}

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert isinstance(data, list)

    def test_execute_custom_report_product(self, create_product, create_category):
        """Test executing product custom report."""
        category = create_category()
        create_product(name='Product Report', sku='PRODRPT001', category=category)

        custom_report = Mock()
        custom_report.report_type = 'PRODUCT'
        custom_report.filters = {'category_id': category.id}

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert isinstance(data, list)

    def test_execute_custom_report_purchase(self, warehouse, admin_user):
        """Test executing purchase custom report."""
        from apps.purchasing.models import Supplier, PurchaseOrder

        supplier = Supplier.objects.create(
            code='SUP002',
            name='Test Supplier 2',
            contact_name='Contact',
            phone='0912345679'
        )

        PurchaseOrder.objects.create(
            po_number='PO002',
            supplier=supplier,
            warehouse=warehouse,
            status='APPROVED',
            total_amount=Decimal('3000'),
            created_by=admin_user
        )

        custom_report = Mock()
        custom_report.report_type = 'PURCHASE'
        custom_report.filters = {'supplier_id': supplier.id}

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert isinstance(data, list)

    def test_execute_custom_report_unknown_type(self):
        """Test executing custom report with unknown type."""
        custom_report = Mock()
        custom_report.report_type = 'UNKNOWN'
        custom_report.filters = {}

        data = ScheduledReportService._execute_custom_report(custom_report)
        assert data == []


@pytest.mark.django_db
class TestScheduledReportServiceDataMethods:
    """Tests for ScheduledReportService data retrieval methods."""

    def test_get_sales_data_with_filters(self, store, warehouse, admin_user):
        """Test getting sales data with filters."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='SALES001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        report = Mock()
        report.sort_by = 'total_amount'
        report.sort_order = 'DESC'

        filters = {
            'start_date': str(date.today() - timedelta(days=7)),
            'end_date': str(date.today()),
            'store_id': store.id
        }

        data = ScheduledReportService._get_sales_data(filters, report)
        assert isinstance(data, list)

    def test_get_sales_data_without_sort(self, store, warehouse, admin_user):
        """Test getting sales data without sorting."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='SALES002',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        report = Mock()
        report.sort_by = None
        report.sort_order = None

        data = ScheduledReportService._get_sales_data({}, report)
        assert isinstance(data, list)

    def test_get_sales_data_with_asc_sort(self, store, warehouse, admin_user):
        """Test getting sales data with ascending sort."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='SALES003',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('800'),
            total_amount=Decimal('840'),
            created_by=admin_user
        )

        report = Mock()
        report.sort_by = 'created_at'
        report.sort_order = 'ASC'

        data = ScheduledReportService._get_sales_data({}, report)
        assert isinstance(data, list)

    def test_get_inventory_data_with_filters(self, warehouse, create_product, create_category):
        """Test getting inventory data with filters."""
        from apps.inventory.models import Inventory

        category = create_category()
        product = create_product(name='Inv Data Product', sku='INVDATA001', category=category)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=100
        )

        report = Mock()
        filters = {
            'warehouse_id': warehouse.id,
            'category_id': category.id
        }

        data = ScheduledReportService._get_inventory_data(filters, report)
        assert isinstance(data, list)

    def test_get_customer_data_with_filters(self, create_customer):
        """Test getting customer data with filters."""
        from apps.customers.models import CustomerLevel

        level = CustomerLevel.objects.create(
            name='VIP',
            min_spending=Decimal('5000'),
            discount_rate=Decimal('10')
        )

        create_customer(name='VIP Customer', level=level)

        report = Mock()
        filters = {
            'level_id': level.id,
            'is_active': True
        }

        data = ScheduledReportService._get_customer_data(filters, report)
        assert isinstance(data, list)

    def test_get_product_data_with_filters(self, create_product, create_category):
        """Test getting product data with filters."""
        category = create_category()
        create_product(name='Filter Product', sku='FILTPROD001', category=category, status='ACTIVE')

        report = Mock()
        filters = {
            'category_id': category.id,
            'status': 'ACTIVE'
        }

        data = ScheduledReportService._get_product_data(filters, report)
        assert isinstance(data, list)

    def test_get_purchase_data_with_filters(self, warehouse, admin_user):
        """Test getting purchase data with date filters."""
        from apps.purchasing.models import Supplier, PurchaseOrder

        supplier = Supplier.objects.create(
            code='SUP003',
            name='Supplier for Filter',
            contact_name='Contact',
            phone='0912345680'
        )

        PurchaseOrder.objects.create(
            po_number='PO003',
            supplier=supplier,
            warehouse=warehouse,
            status='COMPLETED',
            total_amount=Decimal('2000'),
            created_by=admin_user
        )

        report = Mock()
        filters = {
            'start_date': str(date.today() - timedelta(days=30)),
            'end_date': str(date.today()),
            'supplier_id': supplier.id
        }

        data = ScheduledReportService._get_purchase_data(filters, report)
        assert isinstance(data, list)

    def test_get_sales_daily_data(self, store, warehouse, admin_user):
        """Test getting daily sales data."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='DAILY001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1500'),
            total_amount=Decimal('1575'),
            created_by=admin_user
        )

        filters = {
            'start_date': str(date.today() - timedelta(days=7)),
            'end_date': str(date.today())
        }

        data = ScheduledReportService._get_sales_daily_data(filters)
        assert isinstance(data, list)

    def test_get_sales_summary_data(self, store, warehouse, admin_user):
        """Test getting sales summary data."""
        from apps.sales.models import Order

        Order.objects.create(
            order_number='SUMM001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('2500'),
            total_amount=Decimal('2625'),
            created_by=admin_user
        )

        filters = {
            'start_date': str(date.today() - timedelta(days=30)),
            'end_date': str(date.today())
        }

        data = ScheduledReportService._get_sales_summary_data(filters)
        assert isinstance(data, list)

    def test_get_inventory_status_data(self, warehouse, create_product):
        """Test getting inventory status data."""
        from apps.inventory.models import Inventory

        product = create_product(name='Status Product', sku='STAT001')
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=200
        )

        data = ScheduledReportService._get_inventory_status_data({})
        assert isinstance(data, list)

    def test_get_low_stock_data(self, warehouse, create_product):
        """Test getting low stock data."""
        from apps.inventory.models import Inventory

        product = create_product(name='Very Low Stock', sku='VLOW001', safety_stock=100)
        Inventory.objects.create(
            warehouse=warehouse,
            product=product,
            quantity=5,
            available_quantity=5
        )

        data = ScheduledReportService._get_low_stock_data({})
        assert isinstance(data, list)


class TestScheduledReportServiceNotification:
    """Tests for ScheduledReportService notification functionality."""

    def test_notify_recipients(self, mock_schedule, mock_execution):
        """Test notifying recipients."""
        mock_schedule.recipients = ['user1@example.com', 'user2@example.com']

        ScheduledReportService._notify_recipients(
            mock_schedule, mock_execution, '/path/to/file.csv'
        )

        mock_execution.save.assert_called_once()
        assert mock_execution.recipients_notified == mock_schedule.recipients

    def test_notify_recipients_empty_list(self, mock_schedule, mock_execution):
        """Test notifying with empty recipients list."""
        mock_schedule.recipients = []

        ScheduledReportService._notify_recipients(
            mock_schedule, mock_execution, '/path/to/file.csv'
        )

        mock_execution.save.assert_called_once()
        assert mock_execution.recipients_notified == []

    def test_notify_recipients_none(self, mock_schedule, mock_execution):
        """Test notifying with None recipients."""
        mock_schedule.recipients = None

        ScheduledReportService._notify_recipients(
            mock_schedule, mock_execution, '/path/to/file.csv'
        )

        mock_execution.save.assert_called_once()


@pytest.mark.django_db
class TestScheduledReportServiceExecuteReport:
    """Tests for ScheduledReportService.execute_report method."""

    def test_execute_report_builtin_csv(self, store, warehouse, admin_user):
        """Test executing built-in report with CSV format."""
        from apps.sales.models import Order
        from apps.reports.models import ScheduledReport, ReportExecution

        Order.objects.create(
            order_number='EXEC001',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1050'),
            created_by=admin_user
        )

        schedule = ScheduledReport.objects.create(
            name='Test Builtin Report',
            report_type='SALES_DAILY',
            frequency='DAILY',
            run_time='08:00:00',
            export_format='CSV',
            status='ACTIVE',
            created_by=admin_user
        )

        execution = ReportExecution.objects.create(
            scheduled_report=schedule,
            status='RUNNING'
        )

        with patch('apps.core.export.ExportService.to_csv') as mock_csv:
            mock_response = Mock()
            mock_response.content = b'test,data\n1,2'
            mock_csv.return_value = mock_response

            result = ScheduledReportService.execute_report(schedule, execution)

            assert 'file_path' in result
            assert 'record_count' in result
            assert 'generated_at' in result

    def test_execute_report_custom_excel(self, store, warehouse, admin_user):
        """Test executing custom report with Excel format."""
        from apps.sales.models import Order
        from apps.reports.models import ScheduledReport, ReportExecution, CustomReport

        Order.objects.create(
            order_number='EXEC002',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('2000'),
            total_amount=Decimal('2100'),
            created_by=admin_user
        )

        custom_report = CustomReport.objects.create(
            name='Custom Sales Report',
            report_type='SALES',
            columns=[
                {'key': 'order_number', 'label': '訂單編號'},
                {'key': 'total_amount', 'label': '總額'}
            ],
            created_by=admin_user
        )

        schedule = ScheduledReport.objects.create(
            name='Test Custom Report',
            report_type='SALES_DAILY',
            frequency='WEEKLY',
            run_time='09:00:00',
            export_format='EXCEL',
            custom_report=custom_report,
            status='ACTIVE',
            created_by=admin_user
        )

        execution = ReportExecution.objects.create(
            scheduled_report=schedule,
            status='RUNNING'
        )

        with patch('apps.core.export.ExportService.to_excel') as mock_excel:
            mock_response = Mock()
            mock_response.content = b'excel content'
            mock_excel.return_value = mock_response

            result = ScheduledReportService.execute_report(schedule, execution)

            assert 'file_path' in result
            assert result['file_path'].endswith('.xlsx')

    def test_execute_report_with_recipients(self, store, warehouse, admin_user):
        """Test executing report with notification recipients."""
        from apps.sales.models import Order
        from apps.reports.models import ScheduledReport, ReportExecution

        Order.objects.create(
            order_number='EXEC003',
            store=store,
            warehouse=warehouse,
            status='COMPLETED',
            subtotal=Decimal('500'),
            total_amount=Decimal('525'),
            created_by=admin_user
        )

        schedule = ScheduledReport.objects.create(
            name='Report With Recipients',
            report_type='SALES_DAILY',
            frequency='DAILY',
            run_time='07:00:00',
            export_format='CSV',
            recipients=['admin@example.com', 'manager@example.com'],
            status='ACTIVE',
            created_by=admin_user
        )

        execution = ReportExecution.objects.create(
            scheduled_report=schedule,
            status='RUNNING'
        )

        with patch('apps.core.export.ExportService.to_csv') as mock_csv:
            mock_response = Mock()
            mock_response.content = b'test,data'
            mock_csv.return_value = mock_response

            result = ScheduledReportService.execute_report(schedule, execution)

            assert 'file_path' in result
            execution.refresh_from_db()
            assert execution.recipients_notified == schedule.recipients


class TestScheduledReportServiceGenerateExportFile:
    """Tests for ScheduledReportService._generate_export_file method."""

    def test_generate_export_file_csv(self, tmp_path):
        """Test generating CSV export file."""
        data = [{'col1': 'val1', 'col2': 'val2'}]
        columns = [('col1', 'Column 1'), ('col2', 'Column 2')]

        with patch('apps.core.export.ExportService.to_csv') as mock_csv:
            mock_response = Mock()
            mock_response.content = b'col1,col2\nval1,val2'
            mock_csv.return_value = mock_response

            result = ScheduledReportService._generate_export_file(
                data=data,
                filename='test_report',
                export_format='CSV',
                columns=columns,
                title='Test Report',
                export_dir=str(tmp_path)
            )

            assert result.endswith('.csv')
            mock_csv.assert_called_once()

    def test_generate_export_file_excel(self, tmp_path):
        """Test generating Excel export file."""
        data = [{'col1': 'val1', 'col2': 'val2'}]
        columns = [('col1', 'Column 1'), ('col2', 'Column 2')]

        with patch('apps.core.export.ExportService.to_excel') as mock_excel:
            mock_response = Mock()
            mock_response.content = b'excel binary content'
            mock_excel.return_value = mock_response

            result = ScheduledReportService._generate_export_file(
                data=data,
                filename='test_report',
                export_format='EXCEL',
                columns=columns,
                title='Test Report',
                export_dir=str(tmp_path)
            )

            assert result.endswith('.xlsx')
            mock_excel.assert_called_once()

    def test_generate_export_file_pdf(self, tmp_path):
        """Test generating PDF export file."""
        data = [{'col1': 'val1', 'col2': 'val2'}]
        columns = [('col1', 'Column 1'), ('col2', 'Column 2')]

        with patch('apps.core.export.ExportService.to_pdf') as mock_pdf:
            mock_response = Mock()
            mock_response.content = b'%PDF-1.4 content'
            mock_pdf.return_value = mock_response

            result = ScheduledReportService._generate_export_file(
                data=data,
                filename='test_report',
                export_format='PDF',
                columns=columns,
                title='Test Report',
                export_dir=str(tmp_path)
            )

            assert result.endswith('.pdf')
            mock_pdf.assert_called_once()
