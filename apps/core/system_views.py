"""
System management API views.
Based on SA_06_Redis快取模組.md specifications.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdminUser, IsManagerOrAbove
from apps.core.mixins import StandardResponseMixin
from apps.core.redis_services import (
    OnlineStatusService,
    CacheService,
    AuditQueueService,
    RateLimitService,
    TokenBlacklistService,
)


class OnlineStatusView(StandardResponseMixin, APIView):
    """
    API endpoint for user online status.
    GET /api/v1/system/online-status
    """
    permission_classes = [IsManagerOrAbove]

    def get(self, request):
        """
        Get online users status.
        F06-002: 使用者在線狀態
        """
        try:
            # Cleanup inactive users first
            OnlineStatusService.cleanup_inactive_users()

            online_users = OnlineStatusService.get_online_users()
            online_count = OnlineStatusService.get_online_count()

            # Enrich user data with username/display_name
            from apps.accounts.models import User
            user_ids = [u['userId'] for u in online_users]
            users_data = {
                u.id: {'username': u.username, 'name': u.display_name or u.username}
                for u in User.objects.filter(id__in=user_ids)
            }

            for user_info in online_users:
                user_data = users_data.get(user_info['userId'], {})
                user_info['username'] = user_data.get('username', '')
                user_info['name'] = user_data.get('name', '')

            return self.success_response(data={
                'onlineCount': online_count,
                'users': online_users
            })
        except Exception as e:
            return self.error_response(message=f'取得在線狀態失敗: {str(e)}')


class CacheStatsView(StandardResponseMixin, APIView):
    """
    API endpoint for cache statistics.
    GET /api/v1/system/cache-stats
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Get cache statistics.
        F06-004: 熱門資料快取 - BR06-004-04: 記錄 Cache Hit/Miss 比率供監控
        """
        try:
            stats = CacheService.get_stats()
            return self.success_response(data=stats)
        except Exception as e:
            return self.error_response(message=f'取得快取統計失敗: {str(e)}')


class CacheClearView(StandardResponseMixin, APIView):
    """
    API endpoint for clearing cache.
    POST /api/v1/system/cache/clear
    POST /api/v1/system/cache/clear-all
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Clear specific cache type.
        F06-004: 熱門資料快取 - BR06-004-01: 資料更新時自動清除對應快取
        """
        try:
            cache_type = request.data.get('cache_type')
            identifier = request.data.get('identifier')

            if not cache_type:
                return self.error_response(message='請指定快取類型')

            if identifier:
                CacheService.delete(cache_type, identifier)
                message = f'已清除 {cache_type}:{identifier} 快取'
            else:
                deleted = CacheService.delete_pattern(cache_type)
                message = f'已清除 {deleted} 個 {cache_type} 快取'

            return self.success_response(message=message)
        except Exception as e:
            return self.error_response(message=f'清除快取失敗: {str(e)}')


class CacheClearAllView(StandardResponseMixin, APIView):
    """
    API endpoint for clearing all cache.
    POST /api/v1/system/cache/clear-all
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """Clear all cache data."""
        try:
            CacheService.clear_all()
            return self.success_response(message='已清除所有快取')
        except Exception as e:
            return self.error_response(message=f'清除快取失敗: {str(e)}')


class AuditQueueStatsView(StandardResponseMixin, APIView):
    """
    API endpoint for audit queue statistics.
    GET /api/v1/system/audit-queue-stats
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Get audit queue statistics.
        F06-007: 操作紀錄佇列
        """
        try:
            stats = AuditQueueService.get_stats()
            return self.success_response(data=stats)
        except Exception as e:
            return self.error_response(message=f'取得佇列統計失敗: {str(e)}')


class AuditQueueReprocessView(StandardResponseMixin, APIView):
    """
    API endpoint for reprocessing dead letter queue.
    POST /api/v1/system/audit-queue/reprocess
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        """
        Reprocess entries from dead letter queue.
        F06-007: 操作紀錄佇列
        """
        try:
            count = request.data.get('count', 100)
            reprocessed = AuditQueueService.reprocess_dead_letters(count)
            return self.success_response(
                message=f'已將 {reprocessed} 筆記錄重新加入處理佇列',
                data={'reprocessed': reprocessed}
            )
        except Exception as e:
            return self.error_response(message=f'重新處理失敗: {str(e)}')


class RateLimitStatusView(StandardResponseMixin, APIView):
    """
    API endpoint for rate limit status.
    GET /api/v1/system/rate-limit/status
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Get rate limit status and statistics.
        F06-003: API 速率限制
        """
        try:
            user_id = request.query_params.get('user_id')

            if user_id:
                user_status = RateLimitService.get_user_status(int(user_id))
                data = {'userStatus': user_status}
            else:
                blocked_stats = RateLimitService.get_blocked_stats()
                data = {'blockedStats': blocked_stats}

            return self.success_response(data=data)
        except Exception as e:
            return self.error_response(message=f'取得速率限制狀態失敗: {str(e)}')


class ForceLogoutView(StandardResponseMixin, APIView):
    """
    API endpoint for force logout user.
    POST /api/v1/auth/force-logout/{user_id}
    """
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        """
        Force logout a specific user by blacklisting all their tokens.
        F06-001: JWT Token 黑名單 - BR06-001-04
        """
        try:
            # Blacklist all tokens for the user
            TokenBlacklistService.blacklist_user_tokens(user_id)

            # Remove from online list
            OnlineStatusService.user_logout(user_id)

            return self.success_response(message=f'使用者 {user_id} 已被強制登出')
        except Exception as e:
            return self.error_response(message=f'強制登出失敗: {str(e)}')


class UserSessionsView(StandardResponseMixin, APIView):
    """
    API endpoint for user sessions.
    GET /api/v1/auth/sessions
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get current user's session information.
        F06-002: 使用者在線狀態
        """
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection('default')

            user_id = request.user.id
            session_key = f'session:user:{user_id}'
            session_data = redis_conn.hgetall(session_key)

            if session_data:
                session_info = {
                    'userId': user_id,
                    'loginTime': session_data.get(b'loginTime', b'').decode(),
                    'lastActiveTime': session_data.get(b'lastActiveTime', b'').decode(),
                    'ip': session_data.get(b'ip', b'').decode(),
                    'isOnline': OnlineStatusService.is_user_online(user_id)
                }
            else:
                session_info = {
                    'userId': user_id,
                    'isOnline': False
                }

            return self.success_response(data=session_info)
        except Exception as e:
            return self.error_response(message=f'取得 Session 失敗: {str(e)}')


class AuditLogViewSet(StandardResponseMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    """
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        from apps.core.models import AuditLog
        queryset = AuditLog.objects.all()

        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # Filter by module
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        return queryset.order_by('-created_at')

    def list(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        data = []
        for log in page:
            data.append({
                'id': log.id,
                'auditId': log.audit_id,
                'userId': log.user_id,
                'username': log.username,
                'action': log.action,
                'actionDisplay': log.get_action_display(),
                'module': log.module,
                'moduleDisplay': log.get_module_display(),
                'targetId': log.target_id,
                'targetType': log.target_type,
                'ipAddress': log.ip_address,
                'createdAt': log.created_at.isoformat() if log.created_at else None,
            })

        return self.get_paginated_response(data)

    def retrieve(self, request, pk=None):
        from apps.core.models import AuditLog
        try:
            log = AuditLog.objects.get(pk=pk)
            data = {
                'id': log.id,
                'auditId': log.audit_id,
                'userId': log.user_id,
                'username': log.username,
                'action': log.action,
                'actionDisplay': log.get_action_display(),
                'module': log.module,
                'moduleDisplay': log.get_module_display(),
                'targetId': log.target_id,
                'targetType': log.target_type,
                'oldValue': log.old_value,
                'newValue': log.new_value,
                'ipAddress': log.ip_address,
                'userAgent': log.user_agent,
                'createdAt': log.created_at.isoformat() if log.created_at else None,
            }
            return self.success_response(data=data)
        except AuditLog.DoesNotExist:
            return self.error_response(message='審計日誌不存在', status_code=status.HTTP_404_NOT_FOUND)
