"""
Report services for scheduled and custom reports.
F08-008: 自訂報表
F08-009: 排程報表
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q

logger = logging.getLogger(__name__)


class ScheduledReportService:
    """Service for executing scheduled reports."""

    EXPORT_DIR = 'scheduled_reports'

    @classmethod
    def execute_report(cls, schedule, execution) -> Dict:
        """
        Execute a scheduled report and generate output file.

        Args:
            schedule: ScheduledReport instance
            execution: ReportExecution instance

        Returns:
            Dict with file_path and other metadata
        """
        from apps.core.export import ExportService
        from apps.reports.models import CustomReport

        # Determine report type and get data
        if schedule.custom_report:
            # Execute custom report
            data = cls._execute_custom_report(schedule.custom_report)
            report_name = schedule.custom_report.name
            columns = schedule.custom_report.columns
        else:
            # Execute built-in report type
            data = cls._execute_builtin_report(schedule.report_type)
            report_name = schedule.name
            columns = cls._get_default_columns(schedule.report_type)

        # Generate export file
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{schedule.name}_{timestamp}'

        # Ensure export directory exists
        export_dir = os.path.join(settings.MEDIA_ROOT, cls.EXPORT_DIR)
        os.makedirs(export_dir, exist_ok=True)

        # Build column tuples for export
        column_tuples = [(col.get('key', col.get('field')), col.get('label', col.get('header')))
                        for col in columns] if columns else None

        # Generate file based on format
        file_path = cls._generate_export_file(
            data=data,
            filename=filename,
            export_format=schedule.export_format,
            columns=column_tuples,
            title=report_name,
            export_dir=export_dir
        )

        # Send notifications if recipients configured
        if schedule.recipients:
            cls._notify_recipients(schedule, execution, file_path)

        return {
            'file_path': file_path,
            'record_count': len(data),
            'generated_at': timezone.now().isoformat()
        }

    @classmethod
    def _execute_custom_report(cls, custom_report) -> List[Dict]:
        """Execute a custom report and return data."""
        from apps.sales.models import Order
        from apps.inventory.models import Inventory
        from apps.customers.models import Customer
        from apps.products.models import Product
        from apps.purchasing.models import PurchaseOrder

        report_type = custom_report.report_type
        filters = custom_report.filters or {}

        if report_type == 'SALES':
            return cls._get_sales_data(filters, custom_report)
        elif report_type == 'INVENTORY':
            return cls._get_inventory_data(filters, custom_report)
        elif report_type == 'CUSTOMER':
            return cls._get_customer_data(filters, custom_report)
        elif report_type == 'PRODUCT':
            return cls._get_product_data(filters, custom_report)
        elif report_type == 'PURCHASE':
            return cls._get_purchase_data(filters, custom_report)
        else:
            return []

    @classmethod
    def _execute_builtin_report(cls, report_type: str) -> List[Dict]:
        """Execute a built-in report type."""
        # Default to last 30 days for built-in reports
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        filters = {'start_date': str(start_date), 'end_date': str(end_date)}

        if report_type == 'SALES_DAILY':
            return cls._get_sales_daily_data(filters)
        elif report_type == 'SALES_SUMMARY':
            return cls._get_sales_summary_data(filters)
        elif report_type == 'INVENTORY_STATUS':
            return cls._get_inventory_status_data(filters)
        elif report_type == 'LOW_STOCK':
            return cls._get_low_stock_data(filters)
        elif report_type == 'PURCHASE_SUMMARY':
            return cls._get_purchase_summary_data(filters)
        else:
            return []

    @classmethod
    def _get_sales_data(cls, filters: Dict, report) -> List[Dict]:
        """Get sales report data."""
        from apps.sales.models import Order

        qs = Order.objects.filter(status='COMPLETED')

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])
        if filters.get('store_id'):
            qs = qs.filter(store_id=filters['store_id'])

        if report.sort_by:
            order_by = f"-{report.sort_by}" if report.sort_order == 'DESC' else report.sort_by
            qs = qs.order_by(order_by)

        return list(qs.values(
            'order_number', 'store__name', 'customer__name',
            'subtotal', 'discount_amount', 'total_amount',
            'status', 'created_at'
        )[:5000])

    @classmethod
    def _get_inventory_data(cls, filters: Dict, report) -> List[Dict]:
        """Get inventory report data."""
        from apps.inventory.models import Inventory

        qs = Inventory.objects.select_related('warehouse', 'product')

        if filters.get('warehouse_id'):
            qs = qs.filter(warehouse_id=filters['warehouse_id'])
        if filters.get('category_id'):
            qs = qs.filter(product__category_id=filters['category_id'])

        return list(qs.values(
            'product__sku', 'product__name', 'warehouse__name',
            'quantity', 'reserved_quantity', 'available_quantity',
            'product__safety_stock'
        )[:5000])

    @classmethod
    def _get_customer_data(cls, filters: Dict, report) -> List[Dict]:
        """Get customer report data."""
        from apps.customers.models import Customer

        qs = Customer.objects.select_related('level')

        if filters.get('level_id'):
            qs = qs.filter(level_id=filters['level_id'])
        if filters.get('is_active') is not None:
            qs = qs.filter(is_active=filters['is_active'])

        return list(qs.values(
            'member_no', 'name', 'phone', 'email',
            'level__name', 'total_spending', 'points',
            'is_active', 'created_at'
        )[:5000])

    @classmethod
    def _get_product_data(cls, filters: Dict, report) -> List[Dict]:
        """Get product report data."""
        from apps.products.models import Product

        qs = Product.objects.select_related('category', 'unit')

        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])

        return list(qs.values(
            'sku', 'name', 'category__name', 'unit__name',
            'cost_price', 'sale_price', 'status'
        )[:5000])

    @classmethod
    def _get_purchase_data(cls, filters: Dict, report) -> List[Dict]:
        """Get purchase report data."""
        from apps.purchasing.models import PurchaseOrder

        qs = PurchaseOrder.objects.select_related('supplier', 'warehouse')

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])
        if filters.get('supplier_id'):
            qs = qs.filter(supplier_id=filters['supplier_id'])

        return list(qs.values(
            'po_number', 'supplier__name', 'warehouse__name',
            'status', 'total_amount', 'created_at'
        )[:5000])

    @classmethod
    def _get_sales_daily_data(cls, filters: Dict) -> List[Dict]:
        """Get daily sales summary."""
        from apps.sales.models import Order
        from django.db.models.functions import TruncDate

        qs = Order.objects.filter(status='COMPLETED')

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])

        return list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                order_count=Count('id'),
                total_sales=Sum('total_amount'),
                avg_amount=Avg('total_amount')
            )
            .order_by('date')
        )

    @classmethod
    def _get_sales_summary_data(cls, filters: Dict) -> List[Dict]:
        """Get sales summary by store."""
        from apps.sales.models import Order

        qs = Order.objects.filter(status='COMPLETED')

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])

        return list(
            qs.values('store__name')
            .annotate(
                order_count=Count('id'),
                total_sales=Sum('total_amount'),
                avg_amount=Avg('total_amount')
            )
            .order_by('-total_sales')
        )

    @classmethod
    def _get_inventory_status_data(cls, filters: Dict) -> List[Dict]:
        """Get current inventory status."""
        from apps.inventory.models import Inventory

        return list(
            Inventory.objects.select_related('product', 'warehouse')
            .values(
                'product__sku', 'product__name', 'warehouse__name',
                'quantity', 'reserved_quantity', 'available_quantity',
                'product__safety_stock'
            )
            .order_by('product__name')[:5000]
        )

    @classmethod
    def _get_low_stock_data(cls, filters: Dict) -> List[Dict]:
        """Get low stock items."""
        from apps.inventory.models import Inventory

        return list(
            Inventory.objects.filter(available_quantity__lt=F('product__safety_stock'))
            .select_related('product', 'warehouse')
            .values(
                'product__sku', 'product__name', 'warehouse__name',
                'quantity', 'available_quantity', 'product__safety_stock'
            )
            .order_by('available_quantity')[:1000]
        )

    @classmethod
    def _get_purchase_summary_data(cls, filters: Dict) -> List[Dict]:
        """Get purchase summary by supplier."""
        from apps.purchasing.models import PurchaseOrder

        qs = PurchaseOrder.objects.all()

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])

        return list(
            qs.values('supplier__name')
            .annotate(
                po_count=Count('id'),
                total_amount=Sum('total_amount')
            )
            .order_by('-total_amount')
        )

    @classmethod
    def _get_default_columns(cls, report_type: str) -> List[Dict]:
        """Get default columns for built-in report types."""
        column_configs = {
            'SALES_DAILY': [
                {'key': 'date', 'label': '日期'},
                {'key': 'order_count', 'label': '訂單數'},
                {'key': 'total_sales', 'label': '銷售總額'},
                {'key': 'avg_amount', 'label': '平均單價'},
            ],
            'SALES_SUMMARY': [
                {'key': 'store__name', 'label': '門市'},
                {'key': 'order_count', 'label': '訂單數'},
                {'key': 'total_sales', 'label': '銷售總額'},
                {'key': 'avg_amount', 'label': '平均單價'},
            ],
            'INVENTORY_STATUS': [
                {'key': 'product__sku', 'label': '商品編號'},
                {'key': 'product__name', 'label': '商品名稱'},
                {'key': 'warehouse__name', 'label': '倉庫'},
                {'key': 'quantity', 'label': '庫存數量'},
                {'key': 'available_quantity', 'label': '可用數量'},
                {'key': 'product__safety_stock', 'label': '安全庫存'},
            ],
            'LOW_STOCK': [
                {'key': 'product__sku', 'label': '商品編號'},
                {'key': 'product__name', 'label': '商品名稱'},
                {'key': 'warehouse__name', 'label': '倉庫'},
                {'key': 'available_quantity', 'label': '可用數量'},
                {'key': 'product__safety_stock', 'label': '安全庫存'},
            ],
            'PURCHASE_SUMMARY': [
                {'key': 'supplier__name', 'label': '供應商'},
                {'key': 'po_count', 'label': '採購單數'},
                {'key': 'total_amount', 'label': '採購總額'},
            ],
        }
        return column_configs.get(report_type, [])

    @classmethod
    def _generate_export_file(
        cls,
        data: List[Dict],
        filename: str,
        export_format: str,
        columns: List[tuple],
        title: str,
        export_dir: str
    ) -> str:
        """Generate export file and return file path."""
        from apps.core.export import ExportService

        # Generate file based on format
        if export_format == 'EXCEL':
            response = ExportService.to_excel(data, filename, columns, title)
            ext = 'xlsx'
        elif export_format == 'PDF':
            response = ExportService.to_pdf(data, filename, columns, title)
            ext = 'pdf'
        else:  # CSV
            response = ExportService.to_csv(data, filename, columns)
            ext = 'csv'

        # Save to file
        file_path = os.path.join(export_dir, f'{filename}.{ext}')

        with open(file_path, 'wb') as f:
            f.write(response.content)

        # Return relative path
        return os.path.join(cls.EXPORT_DIR, f'{filename}.{ext}')

    @classmethod
    def _notify_recipients(cls, schedule, execution, file_path: str):
        """Send notification to recipients."""
        # This would integrate with email service or notification system
        # For now, just log the notification
        recipients = schedule.recipients or []

        for recipient in recipients:
            logger.info(f"Notifying {recipient} about report: {schedule.name}")

            # In production, send email here:
            # EmailService.send_report_notification(
            #     to=recipient,
            #     report_name=schedule.name,
            #     file_path=file_path
            # )

        execution.recipients_notified = recipients
        execution.save(update_fields=['recipients_notified'])


class CustomReportBuilder:
    """
    Builder for creating and validating custom report configurations.
    F08-008: 自訂報表
    """

    AVAILABLE_COLUMNS = {
        'SALES': [
            {'key': 'order_number', 'label': '訂單編號', 'type': 'string'},
            {'key': 'store__name', 'label': '門市', 'type': 'string'},
            {'key': 'customer__name', 'label': '客戶', 'type': 'string'},
            {'key': 'subtotal', 'label': '小計', 'type': 'decimal'},
            {'key': 'discount_amount', 'label': '折扣', 'type': 'decimal'},
            {'key': 'total_amount', 'label': '總額', 'type': 'decimal'},
            {'key': 'status', 'label': '狀態', 'type': 'string'},
            {'key': 'created_at', 'label': '建立時間', 'type': 'datetime'},
        ],
        'INVENTORY': [
            {'key': 'product__sku', 'label': '商品編號', 'type': 'string'},
            {'key': 'product__name', 'label': '商品名稱', 'type': 'string'},
            {'key': 'warehouse__name', 'label': '倉庫', 'type': 'string'},
            {'key': 'quantity', 'label': '庫存數量', 'type': 'integer'},
            {'key': 'reserved_quantity', 'label': '保留數量', 'type': 'integer'},
            {'key': 'available_quantity', 'label': '可用數量', 'type': 'integer'},
            {'key': 'product__safety_stock', 'label': '安全庫存', 'type': 'integer'},
        ],
        'CUSTOMER': [
            {'key': 'member_no', 'label': '會員編號', 'type': 'string'},
            {'key': 'name', 'label': '姓名', 'type': 'string'},
            {'key': 'phone', 'label': '電話', 'type': 'string'},
            {'key': 'email', 'label': 'Email', 'type': 'string'},
            {'key': 'level__name', 'label': '會員等級', 'type': 'string'},
            {'key': 'total_spending', 'label': '累計消費', 'type': 'decimal'},
            {'key': 'points', 'label': '點數餘額', 'type': 'integer'},
            {'key': 'is_active', 'label': '狀態', 'type': 'boolean'},
        ],
        'PRODUCT': [
            {'key': 'sku', 'label': '商品編號', 'type': 'string'},
            {'key': 'name', 'label': '商品名稱', 'type': 'string'},
            {'key': 'category__name', 'label': '分類', 'type': 'string'},
            {'key': 'unit__name', 'label': '單位', 'type': 'string'},
            {'key': 'cost_price', 'label': '成本價', 'type': 'decimal'},
            {'key': 'sale_price', 'label': '售價', 'type': 'decimal'},
            {'key': 'status', 'label': '狀態', 'type': 'string'},
        ],
        'PURCHASE': [
            {'key': 'po_number', 'label': '採購單號', 'type': 'string'},
            {'key': 'supplier__name', 'label': '供應商', 'type': 'string'},
            {'key': 'warehouse__name', 'label': '倉庫', 'type': 'string'},
            {'key': 'status', 'label': '狀態', 'type': 'string'},
            {'key': 'total_amount', 'label': '總額', 'type': 'decimal'},
            {'key': 'created_at', 'label': '建立時間', 'type': 'datetime'},
        ],
    }

    AVAILABLE_FILTERS = {
        'SALES': [
            {'key': 'start_date', 'label': '開始日期', 'type': 'date'},
            {'key': 'end_date', 'label': '結束日期', 'type': 'date'},
            {'key': 'store_id', 'label': '門市', 'type': 'select', 'source': 'stores'},
            {'key': 'customer_id', 'label': '客戶', 'type': 'select', 'source': 'customers'},
        ],
        'INVENTORY': [
            {'key': 'warehouse_id', 'label': '倉庫', 'type': 'select', 'source': 'warehouses'},
            {'key': 'category_id', 'label': '分類', 'type': 'select', 'source': 'categories'},
        ],
        'CUSTOMER': [
            {'key': 'level_id', 'label': '會員等級', 'type': 'select', 'source': 'customer_levels'},
            {'key': 'is_active', 'label': '狀態', 'type': 'select', 'options': [True, False]},
        ],
        'PRODUCT': [
            {'key': 'category_id', 'label': '分類', 'type': 'select', 'source': 'categories'},
            {'key': 'status', 'label': '狀態', 'type': 'select', 'options': ['ACTIVE', 'INACTIVE', 'DISCONTINUED']},
        ],
        'PURCHASE': [
            {'key': 'start_date', 'label': '開始日期', 'type': 'date'},
            {'key': 'end_date', 'label': '結束日期', 'type': 'date'},
            {'key': 'supplier_id', 'label': '供應商', 'type': 'select', 'source': 'suppliers'},
            {'key': 'status', 'label': '狀態', 'type': 'select', 'options': ['DRAFT', 'APPROVED', 'COMPLETED']},
        ],
    }

    @classmethod
    def get_available_columns(cls, report_type: str) -> List[Dict]:
        """Get available columns for a report type."""
        return cls.AVAILABLE_COLUMNS.get(report_type, [])

    @classmethod
    def get_available_filters(cls, report_type: str) -> List[Dict]:
        """Get available filters for a report type."""
        return cls.AVAILABLE_FILTERS.get(report_type, [])

    @classmethod
    def validate_columns(cls, report_type: str, columns: List[Dict]) -> bool:
        """Validate that columns are valid for the report type."""
        available = {col['key'] for col in cls.AVAILABLE_COLUMNS.get(report_type, [])}
        for col in columns:
            if col.get('key') not in available:
                return False
        return True

    @classmethod
    def validate_filters(cls, report_type: str, filters: Dict) -> bool:
        """Validate that filters are valid for the report type."""
        available = {f['key'] for f in cls.AVAILABLE_FILTERS.get(report_type, [])}
        for key in filters.keys():
            if key not in available:
                return False
        return True
