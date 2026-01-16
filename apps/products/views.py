"""
Product views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.views import BaseViewSet
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from .models import Category, Product, ProductVariant, ProductBarcode, Unit, TaxType
from .serializers import (
    CategorySerializer,
    CategoryTreeSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductVariantSerializer,
    ProductBarcodeSerializer,
    BarcodeSearchResultSerializer,
    UnitSerializer,
    TaxTypeSerializer,
)
from .filters import ProductFilter


class CategoryViewSet(BaseViewSet):
    """Category management ViewSet."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['name']
    filterset_fields = ['parent', 'is_active']
    ordering_fields = ['name', 'sort_order']

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree structure."""
        root_categories = self.get_queryset().filter(
            parent__isnull=True,
            is_active=True
        )
        serializer = CategoryTreeSerializer(root_categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


class ProductViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """
    Product management ViewSet.
    Includes batch import/export functionality (F03-005).
    """
    queryset = Product.objects.select_related('category', 'unit', 'tax_type').all()
    serializer_class = ProductListSerializer
    serializer_classes = {
        'list': ProductListSerializer,
        'retrieve': ProductDetailSerializer,
        'create': ProductCreateSerializer,
        'update': ProductDetailSerializer,
        'partial_update': ProductDetailSerializer,
    }
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'sku', 'sale_price', 'created_at']

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """
        Import products from Excel or CSV file.
        F03-005: 商品匯入匯出
        """
        from apps.products.import_export import ProductImportService
        from apps.core.throttling import ExportThrottle

        file = request.FILES.get('file')
        if not file:
            return self.error_response(message='請上傳檔案')

        # Determine file type
        filename = file.name.lower()
        update_existing = request.data.get('update_existing', 'false').lower() == 'true'

        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            result = ProductImportService.import_from_excel(
                file, request.user, update_existing
            )
        elif filename.endswith('.csv'):
            result = ProductImportService.import_from_csv(
                file, request.user, update_existing
            )
        else:
            return self.error_response(message='不支援的檔案格式，請使用 Excel 或 CSV')

        if result['success']:
            return self.success_response(
                message=result['message'],
                data={
                    'created': result['created'],
                    'updated': result['updated'],
                    'errors': result['errors']
                }
            )
        else:
            return self.error_response(
                message=result['message'],
                errors=result['errors']
            )

    @action(detail=False, methods=['get'])
    def export_data(self, request):
        """
        Export products to Excel or CSV file.
        F03-005: 商品匯入匯出
        """
        from apps.products.import_export import ProductExportService
        from apps.core.throttling import ExportThrottle

        # Use 'export_format' to avoid conflict with DRF's 'format' param
        format_type = request.query_params.get('export_format', 'excel').lower()
        queryset = self.filter_queryset(self.get_queryset())

        if format_type == 'csv':
            return ProductExportService.export_to_csv(queryset)
        else:
            return ProductExportService.export_to_excel(queryset)

    @action(detail=False, methods=['get'])
    def import_template(self, request):
        """
        Download import template file.
        F03-005: 商品匯入匯出
        """
        from apps.products.import_export import ProductExportService
        return ProductExportService.get_template()

    @action(detail=False, methods=['get'])
    def search_barcode(self, request):
        """Search product by barcode."""
        barcode = request.query_params.get('barcode')
        if not barcode:
            return self.error_response(message='請提供條碼')

        try:
            barcode_obj = ProductBarcode.objects.select_related(
                'product', 'variant'
            ).get(barcode=barcode)

            result = {
                'product': ProductListSerializer(barcode_obj.product).data,
                'variant': ProductVariantSerializer(barcode_obj.variant).data if barcode_obj.variant else None,
                'barcode': barcode_obj.barcode,
            }
            return self.success_response(data=result)

        except ProductBarcode.DoesNotExist:
            return self.error_response(
                message='找不到此條碼的商品',
                status_code=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        """Get product stock by warehouse."""
        product = self.get_object()
        warehouse_id = request.query_params.get('warehouse')

        inventory_items = product.inventory_items.select_related('warehouse')
        if warehouse_id:
            inventory_items = inventory_items.filter(warehouse_id=warehouse_id)

        stock_data = [
            {
                'warehouse_id': item.warehouse.id,
                'warehouse_name': item.warehouse.name,
                'quantity': item.quantity,
                'available_quantity': item.available_quantity,
            }
            for item in inventory_items
        ]

        return self.success_response(data=stock_data)

    @action(detail=True, methods=['post'])
    def add_barcode(self, request, pk=None):
        """Add barcode to product."""
        product = self.get_object()
        serializer = ProductBarcodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product, created_by=request.user)
        return self.created_response(data=serializer.data, message='條碼新增成功')


class UnitViewSet(BaseViewSet):
    """Unit management ViewSet."""
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    search_fields = ['name', 'symbol']


class TaxTypeViewSet(BaseViewSet):
    """TaxType management ViewSet."""
    queryset = TaxType.objects.all()
    serializer_class = TaxTypeSerializer
    search_fields = ['name']
