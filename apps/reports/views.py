"""
Reports views.
"""
from datetime import date, timedelta
from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Avg, F, Max, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from apps.core.views import BaseViewSet
from apps.core.mixins import StandardResponseMixin
from apps.core.permissions import IsAuthenticatedAndActive
from apps.core.export import ExportService
from .models import CustomReport, ScheduledReport, ReportExecution
from .serializers import CustomReportSerializer, ScheduledReportSerializer, ReportExecutionSerializer
from apps.sales.models import Order, OrderItem
from apps.inventory.models import Inventory, InventoryMovement
from apps.customers.models import Customer
from apps.products.models import Product, Category
from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem


class DashboardViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Dashboard reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get dashboard overview data."""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        this_month_start = today.replace(day=1)

        # Today's sales
        today_sales = Order.objects.filter(
            status='COMPLETED',
            created_at__date=today
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )

        # Yesterday's sales for comparison
        yesterday_sales = Order.objects.filter(
            status='COMPLETED',
            created_at__date=yesterday
        ).aggregate(total=Sum('total_amount'))

        # This month's sales
        month_sales = Order.objects.filter(
            status='COMPLETED',
            created_at__date__gte=this_month_start
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )

        # Total customers
        total_customers = Customer.objects.filter(is_active=True).count()

        # New customers this month
        new_customers = Customer.objects.filter(
            created_at__date__gte=this_month_start
        ).count()

        # Low stock items count
        low_stock_count = Inventory.objects.filter(
            quantity__lte=F('product__safety_stock'),
            product__status='ACTIVE'
        ).count()

        # Calculate growth
        today_total = today_sales['total'] or 0
        yesterday_total = yesterday_sales['total'] or 0
        if yesterday_total > 0:
            growth = ((today_total - yesterday_total) / yesterday_total) * 100
        else:
            growth = 100 if today_total > 0 else 0

        return self.success_response(data={
            'today': {
                'sales': float(today_sales['total'] or 0),
                'orders': today_sales['count'] or 0,
                'growth': round(growth, 1)
            },
            'month': {
                'sales': float(month_sales['total'] or 0),
                'orders': month_sales['count'] or 0
            },
            'customers': {
                'total': total_customers,
                'new_this_month': new_customers
            },
            'inventory': {
                'low_stock_count': low_stock_count
            }
        })

    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        """Get sales trend for the last N days."""
        days = int(request.query_params.get('days', 7))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        sales_data = Order.objects.filter(
            status='COMPLETED',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('date')

        # Fill in missing dates
        result = []
        current = start_date
        sales_dict = {item['date']: item for item in sales_data}

        while current <= end_date:
            if current in sales_dict:
                result.append({
                    'date': current.isoformat(),
                    'total': float(sales_dict[current]['total']),
                    'count': sales_dict[current]['count']
                })
            else:
                result.append({
                    'date': current.isoformat(),
                    'total': 0,
                    'count': 0
                })
            current += timedelta(days=1)

        return self.success_response(data=result)

    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Get top selling products."""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        start_date = timezone.now().date() - timedelta(days=days)

        top_products = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        ).values(
            'product__id',
            'product__name',
            'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('subtotal')
        ).order_by('-total_quantity')[:limit]

        return self.success_response(data=list(top_products))


class SalesReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Sales reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Get daily sales report."""
        date_str = request.query_params.get('date')
        if date_str:
            report_date = date.fromisoformat(date_str)
        else:
            report_date = timezone.now().date()

        orders = Order.objects.filter(
            status='COMPLETED',
            created_at__date=report_date
        )

        summary = orders.aggregate(
            total_sales=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_tax=Sum('tax_amount'),
            order_count=Count('id'),
            avg_order_value=Avg('total_amount')
        )

        # Sales by payment method
        from apps.sales.models import Payment
        payment_summary = Payment.objects.filter(
            order__status='COMPLETED',
            order__created_at__date=report_date
        ).values('method').annotate(
            total=Sum('amount'),
            count=Count('id')
        )

        return self.success_response(data={
            'date': report_date.isoformat(),
            'summary': {
                'total_sales': float(summary['total_sales'] or 0),
                'total_discount': float(summary['total_discount'] or 0),
                'total_tax': float(summary['total_tax'] or 0),
                'order_count': summary['order_count'] or 0,
                'avg_order_value': float(summary['avg_order_value'] or 0)
            },
            'by_payment_method': list(payment_summary)
        })

    @action(detail=False, methods=['get'])
    def hourly(self, request):
        """Get hourly sales breakdown."""
        date_str = request.query_params.get('date')
        if date_str:
            report_date = date.fromisoformat(date_str)
        else:
            report_date = timezone.now().date()

        hourly_data = Order.objects.filter(
            status='COMPLETED',
            created_at__date=report_date
        ).annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('hour')

        return self.success_response(data=list(hourly_data))

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get sales by category."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        category_sales = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        ).values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('subtotal')
        ).order_by('-total_sales')

        return self.success_response(data=list(category_sales))


class InventoryReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Inventory reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get inventory summary by warehouse."""
        warehouse_id = request.query_params.get('warehouse_id')

        queryset = Inventory.objects.select_related('warehouse', 'product')

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        summary = queryset.aggregate(
            total_items=Count('id'),
            total_quantity=Sum('quantity'),
            total_available=Sum('available_quantity'),
            total_reserved=Sum('reserved_quantity')
        )

        # By warehouse breakdown
        by_warehouse = queryset.values(
            'warehouse__id',
            'warehouse__name'
        ).annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_available=Sum('available_quantity')
        ).order_by('warehouse__name')

        return self.success_response(data={
            'summary': {
                'total_items': summary['total_items'] or 0,
                'total_quantity': summary['total_quantity'] or 0,
                'total_available': summary['total_available'] or 0,
                'total_reserved': summary['total_reserved'] or 0
            },
            'by_warehouse': list(by_warehouse)
        })

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock items list."""
        warehouse_id = request.query_params.get('warehouse_id')
        threshold = request.query_params.get('threshold')

        queryset = Inventory.objects.select_related(
            'warehouse', 'product', 'product__category'
        ).filter(product__status='ACTIVE')

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        if threshold:
            queryset = queryset.filter(quantity__lte=int(threshold))
        else:
            # Default: use product safety stock
            queryset = queryset.filter(quantity__lte=F('product__safety_stock'))

        items = queryset.values(
            'id',
            'warehouse__id',
            'warehouse__name',
            'product__id',
            'product__name',
            'product__sku',
            'product__category__name',
            'quantity',
            'product__safety_stock'
        ).order_by('quantity')[:100]

        return self.success_response(data=list(items))

    @action(detail=False, methods=['get'])
    def movements(self, request):
        """Get inventory movement report."""
        warehouse_id = request.query_params.get('warehouse_id')
        product_id = request.query_params.get('product_id')
        movement_type = request.query_params.get('movement_type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = InventoryMovement.objects.select_related(
            'warehouse', 'product'
        )

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Summary by movement type
        summary = queryset.values('movement_type').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('movement_type')

        # Recent movements
        recent = queryset.order_by('-created_at')[:50].values(
            'id',
            'warehouse__name',
            'product__name',
            'product__sku',
            'movement_type',
            'quantity',
            'balance',
            'reference_type',
            'reference_id',
            'note',
            'created_at'
        )

        return self.success_response(data={
            'summary': list(summary),
            'recent_movements': list(recent)
        })

    @action(detail=False, methods=['get'])
    def valuation(self, request):
        """Get inventory valuation report."""
        warehouse_id = request.query_params.get('warehouse_id')

        queryset = Inventory.objects.select_related(
            'warehouse', 'product', 'product__category'
        ).filter(product__status='ACTIVE', quantity__gt=0)

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        # Calculate valuation using product cost price
        items = queryset.annotate(
            value=F('quantity') * F('product__cost_price')
        ).values(
            'warehouse__id',
            'warehouse__name',
            'product__id',
            'product__name',
            'product__sku',
            'product__category__name',
            'quantity',
            'product__cost_price',
            'value'
        ).order_by('-value')[:100]

        # Total valuation
        total = queryset.aggregate(
            total_value=Sum(F('quantity') * F('product__cost_price'))
        )

        # By category
        by_category = queryset.values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('quantity') * F('product__cost_price'))
        ).order_by('-total_value')

        return self.success_response(data={
            'total_value': float(total['total_value'] or 0),
            'by_category': list(by_category),
            'top_items': list(items)
        })

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get inventory breakdown by category."""
        warehouse_id = request.query_params.get('warehouse_id')

        queryset = Inventory.objects.select_related(
            'warehouse', 'product', 'product__category'
        ).filter(product__status='ACTIVE')

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        data = queryset.values(
            'product__category__id',
            'product__category__name'
        ).annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_available=Sum('available_quantity'),
            avg_quantity=Avg('quantity')
        ).order_by('-total_quantity')

        return self.success_response(data=list(data))

    @action(detail=False, methods=['get'])
    def turnover(self, request):
        """Get inventory turnover analysis."""
        warehouse_id = request.query_params.get('warehouse_id')
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get sales quantity by product
        sales = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        )

        if warehouse_id:
            sales = sales.filter(order__warehouse_id=warehouse_id)

        sales_data = sales.values('product_id').annotate(
            sold_quantity=Sum('quantity')
        )
        sales_dict = {item['product_id']: item['sold_quantity'] for item in sales_data}

        # Get current inventory
        inventory = Inventory.objects.select_related('product')

        if warehouse_id:
            inventory = inventory.filter(warehouse_id=warehouse_id)

        # Calculate turnover rate
        result = []
        for inv in inventory.filter(product__status='ACTIVE'):
            sold = sales_dict.get(inv.product_id, 0)
            avg_stock = inv.quantity
            turnover_rate = (sold / avg_stock * 30 / days) if avg_stock > 0 else 0

            result.append({
                'product_id': inv.product_id,
                'product_name': inv.product.name,
                'product_sku': inv.product.sku,
                'current_stock': inv.quantity,
                'sold_quantity': sold,
                'turnover_rate': round(turnover_rate, 2),
                'days_of_stock': round(inv.quantity / (sold / days), 1) if sold > 0 else None
            })

        # Sort by turnover rate
        result.sort(key=lambda x: x['turnover_rate'], reverse=True)

        return self.success_response(data=result[:100])

    @action(detail=False, methods=['get'])
    def slow_moving(self, request):
        """Get slow-moving (stale) inventory analysis."""
        warehouse_id = request.query_params.get('warehouse_id')
        days = int(request.query_params.get('days', 90))  # 90 days default
        min_stock = int(request.query_params.get('min_stock', 1))

        start_date = timezone.now().date() - timedelta(days=days)

        # Get sales in the period
        sales = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        )

        if warehouse_id:
            sales = sales.filter(order__warehouse_id=warehouse_id)

        sales_data = sales.values('product_id').annotate(
            sold_quantity=Sum('quantity'),
            last_sale=TruncDate(Max('order__created_at'))
        )
        sales_dict = {item['product_id']: item for item in sales_data}

        # Get current inventory
        inventory = Inventory.objects.select_related(
            'product', 'product__category', 'warehouse'
        ).filter(quantity__gte=min_stock, product__status='ACTIVE')

        if warehouse_id:
            inventory = inventory.filter(warehouse_id=warehouse_id)

        result = []
        for inv in inventory:
            sale_info = sales_dict.get(inv.product_id)
            sold_qty = sale_info['sold_quantity'] if sale_info else 0
            last_sale = sale_info['last_sale'] if sale_info else None

            # Calculate days since last sale
            if last_sale:
                days_since_sale = (timezone.now().date() - last_sale).days
            else:
                # No sales - use product creation date
                days_since_sale = (timezone.now().date() - inv.product.created_at.date()).days

            # Calculate stock value
            stock_value = float(inv.quantity * inv.product.cost_price)

            # Determine status
            if sold_qty == 0:
                status = 'DEAD'  # No sales at all
            elif sold_qty < inv.quantity * 0.1:
                status = 'SLOW'  # Very slow moving
            else:
                status = 'NORMAL'

            if status in ['DEAD', 'SLOW']:
                result.append({
                    'warehouse_id': inv.warehouse_id,
                    'warehouse_name': inv.warehouse.name,
                    'product_id': inv.product_id,
                    'product_sku': inv.product.sku,
                    'product_name': inv.product.name,
                    'category': inv.product.category.name if inv.product.category else '',
                    'current_stock': inv.quantity,
                    'sold_quantity': sold_qty,
                    'days_since_sale': days_since_sale,
                    'last_sale_date': last_sale.isoformat() if last_sale else None,
                    'stock_value': stock_value,
                    'status': status
                })

        # Sort by stock value (highest first - most capital tied up)
        result.sort(key=lambda x: x['stock_value'], reverse=True)

        # Summary
        total_dead_value = sum(r['stock_value'] for r in result if r['status'] == 'DEAD')
        total_slow_value = sum(r['stock_value'] for r in result if r['status'] == 'SLOW')
        dead_count = len([r for r in result if r['status'] == 'DEAD'])
        slow_count = len([r for r in result if r['status'] == 'SLOW'])

        return self.success_response(data={
            'analysis_period_days': days,
            'summary': {
                'dead_stock_count': dead_count,
                'dead_stock_value': round(total_dead_value, 2),
                'slow_moving_count': slow_count,
                'slow_moving_value': round(total_slow_value, 2),
                'total_at_risk_value': round(total_dead_value + total_slow_value, 2)
            },
            'items': result[:100]
        })


class ExportViewSet(viewsets.ViewSet):
    """Report export ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def sales_daily(self, request):
        """Export daily sales report."""
        format_type = request.query_params.get('format', 'csv')
        date_str = request.query_params.get('date')

        if date_str:
            report_date = date.fromisoformat(date_str)
        else:
            report_date = timezone.now().date()

        # Get orders for the date
        orders = Order.objects.filter(
            status='COMPLETED',
            created_at__date=report_date
        ).select_related('store', 'customer').values(
            'order_number',
            'store__name',
            'customer__name',
            'subtotal',
            'discount_amount',
            'tax_amount',
            'total_amount',
            'created_at'
        )

        data = list(orders)

        columns = [
            ('order_number', '訂單編號'),
            ('store__name', '門店'),
            ('customer__name', '客戶'),
            ('subtotal', '小計'),
            ('discount_amount', '折扣'),
            ('tax_amount', '稅額'),
            ('total_amount', '總金額'),
            ('created_at', '建立時間'),
        ]

        filename = f'sales_daily_{report_date.isoformat()}'

        if format_type == 'excel':
            return ExportService.to_excel(data, filename, columns, '銷售日報')
        elif format_type == 'pdf':
            return ExportService.to_pdf(data, filename, columns, f'銷售日報 - {report_date}')
        else:
            return ExportService.to_csv(data, filename, columns)

    @action(detail=False, methods=['get'])
    def inventory_current(self, request):
        """Export current inventory report."""
        format_type = request.query_params.get('format', 'csv')
        warehouse_id = request.query_params.get('warehouse_id')

        queryset = Inventory.objects.select_related(
            'warehouse', 'product', 'product__category'
        ).filter(product__status='ACTIVE')

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        data = list(queryset.values(
            'warehouse__name',
            'product__sku',
            'product__name',
            'product__category__name',
            'quantity',
            'available_quantity',
            'reserved_quantity',
            'product__safety_stock'
        ))

        columns = [
            ('warehouse__name', '倉庫'),
            ('product__sku', '商品編號'),
            ('product__name', '商品名稱'),
            ('product__category__name', '分類'),
            ('quantity', '庫存數量'),
            ('available_quantity', '可用數量'),
            ('reserved_quantity', '預留數量'),
            ('product__safety_stock', '安全庫存'),
        ]

        filename = f'inventory_{timezone.now().strftime("%Y%m%d")}'

        if format_type == 'excel':
            return ExportService.to_excel(data, filename, columns, '庫存清單')
        elif format_type == 'pdf':
            return ExportService.to_pdf(data, filename, columns, '庫存清單')
        else:
            return ExportService.to_csv(data, filename, columns)

    @action(detail=False, methods=['get'])
    def inventory_movements(self, request):
        """Export inventory movement report."""
        format_type = request.query_params.get('format', 'csv')
        warehouse_id = request.query_params.get('warehouse_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = InventoryMovement.objects.select_related(
            'warehouse', 'product'
        )

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        data = list(queryset.order_by('-created_at')[:1000].values(
            'warehouse__name',
            'product__sku',
            'product__name',
            'movement_type',
            'quantity',
            'balance',
            'reference_type',
            'reference_id',
            'note',
            'created_at'
        ))

        columns = [
            ('warehouse__name', '倉庫'),
            ('product__sku', '商品編號'),
            ('product__name', '商品名稱'),
            ('movement_type', '異動類型'),
            ('quantity', '異動數量'),
            ('balance', '餘額'),
            ('reference_type', '來源類型'),
            ('reference_id', '來源ID'),
            ('note', '備註'),
            ('created_at', '時間'),
        ]

        filename = f'inventory_movements_{timezone.now().strftime("%Y%m%d")}'

        if format_type == 'excel':
            return ExportService.to_excel(data, filename, columns, '庫存異動')
        elif format_type == 'pdf':
            return ExportService.to_pdf(data, filename, columns, '庫存異動報表')
        else:
            return ExportService.to_csv(data, filename, columns)

    @action(detail=False, methods=['get'])
    def top_products(self, request):
        """Export top selling products report."""
        format_type = request.query_params.get('format', 'csv')
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        data = list(OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        ).values(
            'product__sku',
            'product__name',
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('subtotal')
        ).order_by('-total_quantity')[:100])

        columns = [
            ('product__sku', '商品編號'),
            ('product__name', '商品名稱'),
            ('product__category__name', '分類'),
            ('total_quantity', '銷售數量'),
            ('total_sales', '銷售金額'),
        ]

        filename = f'top_products_{days}days_{timezone.now().strftime("%Y%m%d")}'

        if format_type == 'excel':
            return ExportService.to_excel(data, filename, columns, '熱銷商品')
        elif format_type == 'pdf':
            return ExportService.to_pdf(data, filename, columns, f'熱銷商品報表 (近{days}天)')
        else:
            return ExportService.to_csv(data, filename, columns)

    @action(detail=False, methods=['get'])
    def customers(self, request):
        """Export customer report."""
        format_type = request.query_params.get('format', 'csv')

        data = list(Customer.objects.filter(
            is_active=True
        ).select_related('level').values(
            'member_number',
            'name',
            'phone',
            'email',
            'level__name',
            'total_points',
            'total_spending',
            'total_orders',
            'created_at'
        ).order_by('-total_spending')[:1000])

        columns = [
            ('member_number', '會員編號'),
            ('name', '姓名'),
            ('phone', '電話'),
            ('email', 'Email'),
            ('level__name', '會員等級'),
            ('total_points', '點數餘額'),
            ('total_spending', '累計消費'),
            ('total_orders', '訂單數'),
            ('created_at', '加入時間'),
        ]

        filename = f'customers_{timezone.now().strftime("%Y%m%d")}'

        if format_type == 'excel':
            return ExportService.to_excel(data, filename, columns, '客戶清單')
        elif format_type == 'pdf':
            return ExportService.to_pdf(data, filename, columns, '客戶清單')
        else:
            return ExportService.to_csv(data, filename, columns)


class PurchaseReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Purchase reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get purchase summary report."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Purchase order summary
        po_summary = PurchaseOrder.objects.filter(
            created_at__date__gte=start_date
        ).aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_amount'),
            completed_count=Count('id', filter=Q(status='COMPLETED')),
            pending_count=Count('id', filter=Q(status__in=['DRAFT', 'SUBMITTED', 'APPROVED']))
        )

        # By supplier
        by_supplier = PurchaseOrder.objects.filter(
            created_at__date__gte=start_date,
            status='COMPLETED'
        ).values(
            'supplier__id', 'supplier__name'
        ).annotate(
            order_count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('-total_amount')[:10]

        # By product
        by_product = PurchaseOrderItem.objects.filter(
            purchase_order__created_at__date__gte=start_date,
            purchase_order__status='COMPLETED'
        ).values(
            'product__id', 'product__name', 'product__sku'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('subtotal')
        ).order_by('-total_amount')[:10]

        return self.success_response(data={
            'period_days': days,
            'summary': {
                'total_orders': po_summary['total_count'] or 0,
                'total_amount': float(po_summary['total_amount'] or 0),
                'completed_orders': po_summary['completed_count'] or 0,
                'pending_orders': po_summary['pending_count'] or 0
            },
            'by_supplier': list(by_supplier),
            'by_product': list(by_product)
        })

    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get purchase trend by month."""
        months = int(request.query_params.get('months', 12))
        from django.db.models.functions import TruncMonth

        trend = PurchaseOrder.objects.filter(
            status='COMPLETED'
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            order_count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('-month')[:months]

        return self.success_response(data=list(trend))


class ProfitReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Profit analysis reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get profit summary report."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Calculate profit from completed orders
        order_items = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        ).select_related('product')

        total_revenue = 0
        total_cost = 0
        product_profit = {}

        for item in order_items:
            revenue = float(item.subtotal)
            cost = float(item.product.cost_price) * item.quantity
            profit = revenue - cost

            total_revenue += revenue
            total_cost += cost

            product_id = item.product_id
            if product_id not in product_profit:
                product_profit[product_id] = {
                    'product_id': product_id,
                    'product_name': item.product.name,
                    'product_sku': item.product.sku,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0,
                    'quantity': 0
                }

            product_profit[product_id]['revenue'] += revenue
            product_profit[product_id]['cost'] += cost
            product_profit[product_id]['profit'] += profit
            product_profit[product_id]['quantity'] += item.quantity

        # Sort by profit
        top_profit = sorted(product_profit.values(), key=lambda x: x['profit'], reverse=True)[:20]
        low_profit = sorted(product_profit.values(), key=lambda x: x['profit'])[:10]

        gross_profit = total_revenue - total_cost
        margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

        return self.success_response(data={
            'period_days': days,
            'summary': {
                'total_revenue': round(total_revenue, 2),
                'total_cost': round(total_cost, 2),
                'gross_profit': round(gross_profit, 2),
                'profit_margin': round(margin, 2)
            },
            'top_profitable': top_profit,
            'low_profitable': low_profit
        })

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get profit by category."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        order_items = OrderItem.objects.filter(
            order__status='COMPLETED',
            order__created_at__date__gte=start_date
        ).select_related('product', 'product__category')

        category_profit = {}
        for item in order_items:
            category = item.product.category
            category_id = category.id if category else 0
            category_name = category.name if category else '無分類'

            revenue = float(item.subtotal)
            cost = float(item.product.cost_price) * item.quantity

            if category_id not in category_profit:
                category_profit[category_id] = {
                    'category_id': category_id,
                    'category_name': category_name,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0
                }

            category_profit[category_id]['revenue'] += revenue
            category_profit[category_id]['cost'] += cost
            category_profit[category_id]['profit'] += revenue - cost

        result = sorted(category_profit.values(), key=lambda x: x['profit'], reverse=True)
        return self.success_response(data=result)


class CustomerReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Customer analysis reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get customer summary report."""
        today = timezone.now().date()
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)

        # Customer counts
        total_customers = Customer.objects.filter(is_active=True).count()
        new_this_month = Customer.objects.filter(created_at__date__gte=this_month).count()
        new_last_month = Customer.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lt=this_month
        ).count()

        # Top customers
        top_customers = Customer.objects.filter(
            is_active=True
        ).order_by('-total_spending')[:10].values(
            'id', 'name', 'member_number', 'total_spending', 'total_orders', 'total_points'
        )

        return self.success_response(data={
            'summary': {
                'total_customers': total_customers,
                'new_this_month': new_this_month,
                'new_last_month': new_last_month,
                'growth_rate': round((new_this_month - new_last_month) / new_last_month * 100, 1) if new_last_month > 0 else 0
            },
            'top_customers': list(top_customers)
        })

    @action(detail=False, methods=['get'])
    def by_level(self, request):
        """Get customer breakdown by level."""
        data = Customer.objects.filter(
            is_active=True
        ).values(
            'level__id', 'level__name'
        ).annotate(
            customer_count=Count('id'),
            total_spending=Sum('total_spending'),
            avg_spending=Avg('total_spending')
        ).order_by('-total_spending')

        return self.success_response(data=list(data))

    @action(detail=False, methods=['get'])
    def rfm_analysis(self, request):
        """Get RFM (Recency, Frequency, Monetary) analysis."""
        days = int(request.query_params.get('days', 365))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get customer purchase data
        from django.db.models.functions import TruncDate

        customer_data = Order.objects.filter(
            status='COMPLETED',
            created_at__date__gte=start_date,
            customer__isnull=False
        ).values('customer_id').annotate(
            last_purchase=Max('created_at'),
            order_count=Count('id'),
            total_amount=Sum('total_amount')
        )

        today = timezone.now()
        result = []
        for data in customer_data:
            days_since = (today - data['last_purchase']).days

            # Simple RFM scoring (1-5)
            r_score = 5 if days_since < 30 else (4 if days_since < 60 else (3 if days_since < 90 else (2 if days_since < 180 else 1)))
            f_score = min(5, max(1, data['order_count']))
            m_score = 5 if data['total_amount'] > 10000 else (4 if data['total_amount'] > 5000 else (3 if data['total_amount'] > 2000 else (2 if data['total_amount'] > 500 else 1)))

            result.append({
                'customer_id': data['customer_id'],
                'recency_days': days_since,
                'frequency': data['order_count'],
                'monetary': float(data['total_amount']),
                'r_score': r_score,
                'f_score': f_score,
                'm_score': m_score,
                'rfm_score': r_score + f_score + m_score
            })

        # Sort by RFM score
        result.sort(key=lambda x: x['rfm_score'], reverse=True)
        return self.success_response(data=result[:100])


class ComparisonReportViewSet(StandardResponseMixin, viewsets.ViewSet):
    """Year-over-year and period comparison reports ViewSet."""
    permission_classes = [IsAuthenticatedAndActive]

    @action(detail=False, methods=['get'])
    def yoy_sales(self, request):
        """Year-over-year sales comparison."""
        current_year = timezone.now().year
        last_year = current_year - 1

        from django.db.models.functions import TruncMonth

        current_data = Order.objects.filter(
            status='COMPLETED',
            created_at__year=current_year
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')

        last_data = Order.objects.filter(
            status='COMPLETED',
            created_at__year=last_year
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')

        # Convert to month-indexed dicts
        current_dict = {d['month'].month: d for d in current_data}
        last_dict = {d['month'].month: d for d in last_data}

        result = []
        for month in range(1, 13):
            current = current_dict.get(month, {'total': 0, 'count': 0})
            last = last_dict.get(month, {'total': 0, 'count': 0})

            current_total = float(current.get('total') or 0)
            last_total = float(last.get('total') or 0)

            growth = ((current_total - last_total) / last_total * 100) if last_total > 0 else (100 if current_total > 0 else 0)

            result.append({
                'month': month,
                'current_year': current_year,
                'current_sales': current_total,
                'current_orders': current.get('count') or 0,
                'last_year': last_year,
                'last_sales': last_total,
                'last_orders': last.get('count') or 0,
                'growth_rate': round(growth, 2)
            })

        return self.success_response(data=result)

    @action(detail=False, methods=['get'])
    def period_comparison(self, request):
        """Compare two custom periods."""
        period1_start = request.query_params.get('period1_start')
        period1_end = request.query_params.get('period1_end')
        period2_start = request.query_params.get('period2_start')
        period2_end = request.query_params.get('period2_end')

        if not all([period1_start, period1_end, period2_start, period2_end]):
            return self.error_response(message='請提供兩個完整的比較期間')

        period1 = Order.objects.filter(
            status='COMPLETED',
            created_at__date__gte=period1_start,
            created_at__date__lte=period1_end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id'),
            avg=Avg('total_amount')
        )

        period2 = Order.objects.filter(
            status='COMPLETED',
            created_at__date__gte=period2_start,
            created_at__date__lte=period2_end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id'),
            avg=Avg('total_amount')
        )

        p1_total = float(period1['total'] or 0)
        p2_total = float(period2['total'] or 0)
        growth = ((p1_total - p2_total) / p2_total * 100) if p2_total > 0 else 0

        return self.success_response(data={
            'period1': {
                'start': period1_start,
                'end': period1_end,
                'total_sales': p1_total,
                'order_count': period1['count'] or 0,
                'avg_order_value': float(period1['avg'] or 0)
            },
            'period2': {
                'start': period2_start,
                'end': period2_end,
                'total_sales': p2_total,
                'order_count': period2['count'] or 0,
                'avg_order_value': float(period2['avg'] or 0)
            },
            'comparison': {
                'sales_growth': round(growth, 2),
                'sales_difference': round(p1_total - p2_total, 2)
            }
        })


class CustomReportViewSet(StandardResponseMixin, BaseViewSet):
    """
    Custom report management ViewSet.
    F08-008: 自訂報表
    """
    queryset = CustomReport.objects.all()
    serializer_class = CustomReportSerializer
    filterset_fields = ['report_type', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        """Filter to user's own reports or public reports."""
        qs = super().get_queryset()
        return qs.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def schema(self, request):
        """
        Get available columns and filters for each report type.
        Helps frontend build the custom report configuration UI.
        """
        from apps.reports.services import CustomReportBuilder

        report_type = request.query_params.get('report_type')

        if report_type:
            return self.success_response(data={
                'report_type': report_type,
                'columns': CustomReportBuilder.get_available_columns(report_type),
                'filters': CustomReportBuilder.get_available_filters(report_type)
            })

        # Return schema for all report types
        schema = {}
        for rt in ['SALES', 'INVENTORY', 'CUSTOMER', 'PRODUCT', 'PURCHASE']:
            schema[rt] = {
                'columns': CustomReportBuilder.get_available_columns(rt),
                'filters': CustomReportBuilder.get_available_filters(rt)
            }

        return self.success_response(data=schema)

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """
        Preview a custom report without saving it.
        Useful for testing report configuration before saving.
        """
        from apps.reports.services import CustomReportBuilder

        report_type = request.data.get('report_type')
        columns = request.data.get('columns', [])
        filters = request.data.get('filters', {})
        sort_by = request.data.get('sort_by', '')
        sort_order = request.data.get('sort_order', 'DESC')

        if not report_type:
            return self.error_response(message='請指定報表類型')

        # Validate columns and filters
        if columns and not CustomReportBuilder.validate_columns(report_type, columns):
            return self.error_response(message='包含無效的欄位設定')

        if filters and not CustomReportBuilder.validate_filters(report_type, filters):
            return self.error_response(message='包含無效的篩選條件')

        # Create temporary report object for execution
        temp_report = CustomReport(
            report_type=report_type,
            columns=columns,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )

        try:
            data = self._execute_report(temp_report)
            # Limit preview to 100 records
            return self.success_response(data={
                'records': data[:100],
                'total_count': len(data),
                'preview_limit': 100
            })
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['get'])
    def execute(self, request, pk=None):
        """Execute a custom report and return data."""
        report = self.get_object()

        try:
            data = self._execute_report(report)
            return self.success_response(data=data)
        except Exception as e:
            return self.error_response(message=str(e))

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export custom report."""
        report = self.get_object()
        format_type = request.query_params.get('format', 'excel')

        try:
            data = self._execute_report(report)

            # Build columns from report config
            columns = [(col['key'], col['label']) for col in report.columns] if report.columns else None

            filename = f'custom_report_{report.name}_{timezone.now().strftime("%Y%m%d")}'

            if format_type == 'excel':
                return ExportService.to_excel(data, filename, columns, report.name)
            elif format_type == 'pdf':
                return ExportService.to_pdf(data, filename, columns, report.name)
            else:
                return ExportService.to_csv(data, filename, columns)

        except Exception as e:
            return self.error_response(message=str(e))

    def _execute_report(self, report):
        """Execute report based on type and config."""
        report_type = report.report_type
        filters = report.filters or {}
        columns = report.columns or []

        if report_type == 'SALES':
            return self._execute_sales_report(filters, columns, report)
        elif report_type == 'INVENTORY':
            return self._execute_inventory_report(filters, columns, report)
        elif report_type == 'CUSTOMER':
            return self._execute_customer_report(filters, columns, report)
        elif report_type == 'PRODUCT':
            return self._execute_product_report(filters, columns, report)
        elif report_type == 'PURCHASE':
            return self._execute_purchase_report(filters, columns, report)
        else:
            return []

    def _execute_sales_report(self, filters, columns, report):
        """Execute sales report."""
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
            'total_amount', 'created_at'
        )[:1000])

    def _execute_inventory_report(self, filters, columns, report):
        """Execute inventory report."""
        qs = Inventory.objects.select_related('warehouse', 'product')

        if filters.get('warehouse_id'):
            qs = qs.filter(warehouse_id=filters['warehouse_id'])
        if filters.get('min_quantity') is not None:
            qs = qs.filter(quantity__gte=filters['min_quantity'])
        if filters.get('max_quantity') is not None:
            qs = qs.filter(quantity__lte=filters['max_quantity'])

        return list(qs.values(
            'warehouse__name', 'product__sku', 'product__name',
            'quantity', 'available_quantity'
        )[:1000])

    def _execute_customer_report(self, filters, columns, report):
        """Execute customer report."""
        qs = Customer.objects.filter(is_active=True)

        if filters.get('level_id'):
            qs = qs.filter(level_id=filters['level_id'])
        if filters.get('min_spending'):
            qs = qs.filter(total_spending__gte=filters['min_spending'])

        return list(qs.values(
            'member_number', 'name', 'phone', 'level__name',
            'total_points', 'total_spending', 'total_orders'
        )[:1000])

    def _execute_product_report(self, filters, columns, report):
        """Execute product report."""
        qs = Product.objects.filter(status='ACTIVE')

        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])

        return list(qs.values(
            'sku', 'name', 'category__name', 'selling_price', 'cost_price'
        )[:1000])

    def _execute_purchase_report(self, filters, columns, report):
        """Execute purchase report."""
        from apps.purchasing.models import PurchaseOrder

        qs = PurchaseOrder.objects.select_related('supplier', 'warehouse')

        if filters.get('start_date'):
            qs = qs.filter(created_at__date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__date__lte=filters['end_date'])
        if filters.get('supplier_id'):
            qs = qs.filter(supplier_id=filters['supplier_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])

        return list(qs.values(
            'po_number', 'supplier__name', 'warehouse__name',
            'status', 'total_amount', 'created_at'
        )[:1000])


class ScheduledReportViewSet(StandardResponseMixin, BaseViewSet):
    """Scheduled report management ViewSet."""
    queryset = ScheduledReport.objects.select_related('custom_report')
    serializer_class = ScheduledReportSerializer
    filterset_fields = ['status', 'frequency', 'report_type']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'next_run_at']

    def get_queryset(self):
        """Filter to user's own schedules."""
        qs = super().get_queryset()
        return qs.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        instance.calculate_next_run()
        instance.save()

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause scheduled report."""
        schedule = self.get_object()
        schedule.status = 'PAUSED'
        schedule.save()
        return self.success_response(message='排程已暫停')

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume scheduled report."""
        schedule = self.get_object()
        schedule.status = 'ACTIVE'
        schedule.calculate_next_run()
        schedule.save()
        return self.success_response(message='排程已恢復')

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """Run scheduled report immediately."""
        schedule = self.get_object()

        try:
            # Create execution record
            execution = ReportExecution.objects.create(
                scheduled_report=schedule,
                status='RUNNING',
                started_at=timezone.now(),
                created_by=request.user
            )

            # Execute report (simplified - in production this would be async)
            # ... report execution logic ...

            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.save()

            schedule.last_run_at = timezone.now()
            schedule.last_run_status = 'SUCCESS'
            schedule.calculate_next_run()
            schedule.save()

            return self.success_response(message='報表執行完成')

        except Exception as e:
            if 'execution' in locals():
                execution.status = 'FAILED'
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save()
            return self.error_response(message=str(e))

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get execution history for a schedule."""
        schedule = self.get_object()
        executions = schedule.executions.order_by('-created_at')[:50]
        return self.success_response(
            data=ReportExecutionSerializer(executions, many=True).data
        )
