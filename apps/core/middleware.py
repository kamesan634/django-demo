"""
Custom middleware for the ERP system.
Based on SA_06_Redis快取模組.md specifications.
"""
import json
import logging
import re
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)


class OnlineStatusMiddleware(MiddlewareMixin):
    """
    Middleware to track user online status.
    F06-002: 使用者在線狀態
    BR06-002-03: 使用者每次 API 請求更新最後活動時間
    """

    def process_request(self, request):
        """Update user's last activity time on each request."""
        if request.user and request.user.is_authenticated:
            try:
                from apps.core.redis_services import OnlineStatusService
                OnlineStatusService.update_activity(request.user.id)
            except Exception as e:
                # Don't fail the request if Redis is unavailable
                logger.debug(f"Failed to update online status: {e}")

        return None


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to automatically log API operations.
    F06-007: 操作紀錄佇列
    """

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = [
        r'^/api/v1/auth/token',
        r'^/api/v1/system/online-status',
        r'^/api/v1/system/cache-stats',
        r'^/api/v1/system/audit-queue-stats',
        r'^/api/docs',
        r'^/api/schema',
        r'^/admin',
        r'^/static',
        r'^/media',
    ]

    # Methods to audit
    AUDIT_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # Module mapping based on URL patterns
    MODULE_MAPPING = {
        r'/api/v1/auth/': 'AUTH',
        r'/api/v1/users/': 'USER',
        r'/api/v1/roles/': 'ROLE',
        r'/api/v1/products/': 'PRODUCT',
        r'/api/v1/categories/': 'CATEGORY',
        r'/api/v1/stores/': 'STORE',
        r'/api/v1/warehouses/': 'WAREHOUSE',
        r'/api/v1/customers/': 'CUSTOMER',
        r'/api/v1/orders/': 'ORDER',
        r'/api/v1/pos/': 'POS',
        r'/api/v1/inventory/': 'INVENTORY',
        r'/api/v1/stock-counts/': 'STOCK_COUNT',
        r'/api/v1/stock-transfers/': 'STOCK_TRANSFER',
        r'/api/v1/suppliers/': 'SUPPLIER',
        r'/api/v1/purchase-orders/': 'PURCHASE_ORDER',
        r'/api/v1/reports/': 'REPORT',
    }

    # Action mapping based on HTTP method and URL patterns
    ACTION_MAPPING = {
        'POST': 'CREATE',
        'PUT': 'UPDATE',
        'PATCH': 'UPDATE',
        'DELETE': 'DELETE',
    }

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.excluded_patterns = [re.compile(p) for p in self.EXCLUDED_PATHS]
        self.module_patterns = [(re.compile(p), m) for p, m in self.MODULE_MAPPING.items()]

    def _should_audit(self, request):
        """Check if this request should be audited."""
        # Skip non-audit methods
        if request.method not in self.AUDIT_METHODS:
            return False

        # Skip unauthenticated requests
        if not request.user or not request.user.is_authenticated:
            return False

        # Skip excluded paths
        for pattern in self.excluded_patterns:
            if pattern.search(request.path):
                return False

        return True

    def _get_module(self, path):
        """Determine module from request path."""
        for pattern, module in self.module_patterns:
            if pattern.search(path):
                return module
        return 'UNKNOWN'

    def _get_action(self, request, response):
        """Determine action from request method and response."""
        base_action = self.ACTION_MAPPING.get(request.method, 'UNKNOWN')

        # Check for specific actions in path
        if '/confirm/' in request.path:
            return 'CONFIRM'
        elif '/void/' in request.path or '/cancel/' in request.path:
            return 'VOID'
        elif '/approve/' in request.path:
            return 'APPROVE'
        elif '/reject/' in request.path:
            return 'REJECT'
        elif '/lock/' in request.path:
            return 'LOCK'
        elif '/unlock/' in request.path:
            return 'UNLOCK'
        elif '/export' in request.path:
            return 'EXPORT'

        return base_action

    def _get_target_id(self, request, response):
        """Extract target ID from request path or response."""
        # Try to extract ID from URL path
        path_parts = request.path.rstrip('/').split('/')
        for part in reversed(path_parts):
            if part.isdigit():
                return part

        # Try to get from response for CREATE operations
        if request.method == 'POST' and hasattr(response, 'data'):
            data = response.data
            if isinstance(data, dict):
                return str(data.get('data', {}).get('id', '')) or str(data.get('id', ''))

        return None

    def _get_target_type(self, module):
        """Get target type from module name."""
        return module.replace('_', '')

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _get_request_body(self, request):
        """Safely get request body."""
        try:
            if hasattr(request, 'data'):
                return request.data
            elif request.body:
                return json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
        return None

    def process_response(self, request, response):
        """Log the operation after response is generated."""
        if not self._should_audit(request):
            return response

        # Only log successful operations (2xx status codes)
        if not (200 <= response.status_code < 300):
            return response

        try:
            from apps.core.redis_services import AuditQueueService

            module = self._get_module(request.path)
            action = self._get_action(request, response)
            target_id = self._get_target_id(request, response)

            # Get request body for new_value (for CREATE/UPDATE)
            new_value = None
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = self._get_request_body(request)
                if body:
                    # Sanitize sensitive data
                    if isinstance(body, dict):
                        body = {k: v for k, v in body.items()
                               if k.lower() not in ['password', 'token', 'secret', 'refresh']}
                    new_value = body

            AuditQueueService.push(
                user_id=request.user.id,
                username=request.user.username,
                action=action,
                module=module,
                target_id=target_id,
                target_type=self._get_target_type(module),
                old_value=None,  # Would need to query DB before operation to get this
                new_value=new_value,
                ip=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except Exception as e:
            # Don't fail the response if audit logging fails
            logger.error(f"Failed to push audit log: {e}")

        return response


class RateLimitHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add rate limit headers to responses.
    BR06-003-05: 回應 Header 包含剩餘次數與重置時間
    """

    def process_response(self, request, response):
        """Add rate limit headers to response."""
        # Check if throttle information is available on the request
        if hasattr(request, '_throttle_headers'):
            for header, value in request._throttle_headers.items():
                response[header] = value

        return response


class TokenBlacklistMiddleware(MiddlewareMixin):
    """
    Middleware to check JWT token against blacklist.
    F06-001: JWT Token 黑名單
    BR06-001-02: 每次 API 請求需檢查 Token 是否在黑名單中
    """

    def process_request(self, request):
        """Check if the token is blacklisted."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

            try:
                from apps.core.redis_services import TokenBlacklistService

                if TokenBlacklistService.is_blacklisted(token):
                    from rest_framework.response import Response
                    from rest_framework import status
                    from django.http import JsonResponse

                    return JsonResponse(
                        {
                            'success': False,
                            'message': 'Token 已失效，請重新登入',
                            'code': 'TOKEN_BLACKLISTED'
                        },
                        status=401
                    )

                # Also check if user is globally blacklisted
                if request.user and request.user.is_authenticated:
                    if TokenBlacklistService.is_user_blacklisted(request.user.id):
                        return JsonResponse(
                            {
                                'success': False,
                                'message': '您的帳號已被強制登出，請重新登入',
                                'code': 'USER_BLACKLISTED'
                            },
                            status=401
                        )
            except Exception as e:
                # Don't fail the request if Redis is unavailable
                logger.debug(f"Failed to check token blacklist: {e}")

        return None
