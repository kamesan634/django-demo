"""
Reports URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardViewSet, SalesReportViewSet, InventoryReportViewSet, ExportViewSet,
    PurchaseReportViewSet, ProfitReportViewSet, CustomerReportViewSet, ComparisonReportViewSet,
    CustomReportViewSet, ScheduledReportViewSet
)

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'reports/sales', SalesReportViewSet, basename='sales-report')
router.register(r'reports/inventory', InventoryReportViewSet, basename='inventory-report')
router.register(r'reports/purchase', PurchaseReportViewSet, basename='purchase-report')
router.register(r'reports/profit', ProfitReportViewSet, basename='profit-report')
router.register(r'reports/customer', CustomerReportViewSet, basename='customer-report')
router.register(r'reports/comparison', ComparisonReportViewSet, basename='comparison-report')
router.register(r'custom-reports', CustomReportViewSet, basename='custom-report')
router.register(r'scheduled-reports', ScheduledReportViewSet, basename='scheduled-report')
router.register(r'export', ExportViewSet, basename='export')

urlpatterns = [
    path('', include(router.urls)),
]
