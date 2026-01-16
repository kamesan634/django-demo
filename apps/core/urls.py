"""
Core app URL Configuration.
System management APIs based on SA_06_Redis快取模組.md.
Business configuration APIs.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .system_views import (
    OnlineStatusView,
    CacheStatsView,
    CacheClearView,
    CacheClearAllView,
    AuditQueueStatsView,
    AuditQueueReprocessView,
    RateLimitStatusView,
    ForceLogoutView,
    UserSessionsView,
    AuditLogViewSet,
)
from .business_views import (
    PaymentMethodViewSet,
    NumberingRuleViewSet,
    ProductPriceViewSet,
    SupplierPerformanceViewSet,
    AccountPayableViewSet,
)

router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
# Business configuration
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'numbering-rules', NumberingRuleViewSet, basename='numbering-rule')
router.register(r'product-prices', ProductPriceViewSet, basename='product-price')
router.register(r'supplier-performances', SupplierPerformanceViewSet, basename='supplier-performance')
router.register(r'accounts-payable', AccountPayableViewSet, basename='account-payable')

urlpatterns = [
    # Online status (F06-002)
    path('system/online-status/', OnlineStatusView.as_view(), name='online-status'),

    # Cache management (F06-004)
    path('system/cache-stats/', CacheStatsView.as_view(), name='cache-stats'),
    path('system/cache/clear/', CacheClearView.as_view(), name='cache-clear'),
    path('system/cache/clear-all/', CacheClearAllView.as_view(), name='cache-clear-all'),

    # Audit queue (F06-007)
    path('system/audit-queue-stats/', AuditQueueStatsView.as_view(), name='audit-queue-stats'),
    path('system/audit-queue/reprocess/', AuditQueueReprocessView.as_view(), name='audit-queue-reprocess'),

    # Rate limit status (F06-003)
    path('system/rate-limit/status/', RateLimitStatusView.as_view(), name='rate-limit-status'),

    # Auth related (F06-001)
    path('auth/force-logout/<int:user_id>/', ForceLogoutView.as_view(), name='force-logout'),
    path('auth/sessions/', UserSessionsView.as_view(), name='user-sessions'),
]

urlpatterns += router.urls
