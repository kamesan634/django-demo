"""
Account views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.core.views import BaseViewSet
from apps.core.permissions import IsAdminUser
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from apps.core.throttling import LoginThrottle
from apps.core.redis_services import (
    OnlineStatusService,
    TokenBlacklistService,
    AuditQueueService,
)
from .models import User, Role
from .serializers import (
    RoleSerializer,
    UserListSerializer,
    UserDetailSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)


class RoleViewSet(BaseViewSet):
    """Role management ViewSet."""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('active_only'):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        """Role doesn't have created_by field, so override parent."""
        serializer.save()

    def perform_update(self, serializer):
        """Role doesn't have updated_by field, so override parent."""
        serializer.save()


class UserViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """User management ViewSet."""
    queryset = User.objects.select_related('role').all()
    serializer_class = UserListSerializer
    serializer_classes = {
        'list': UserListSerializer,
        'retrieve': UserDetailSerializer,
        'create': UserCreateSerializer,
        'update': UserUpdateSerializer,
        'partial_update': UserUpdateSerializer,
    }
    search_fields = ['username', 'email', 'display_name', 'phone']
    filterset_fields = ['role', 'status', 'is_active']
    ordering_fields = ['username', 'created_at', 'last_login']

    def get_permissions(self):
        if self.action in ['me', 'change_password']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info."""
        serializer = UserDetailSerializer(request.user)
        return self.success_response(data=serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change current user's password."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])

        return self.success_response(message='密碼變更成功')

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock user account."""
        user = self.get_object()
        user.lock_account()
        return self.success_response(message='帳號已鎖定')

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock user account."""
        user = self.get_object()
        user.unlock_account()
        return self.success_response(message='帳號已解鎖')

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password (admin only)."""
        user = self.get_object()
        new_password = request.data.get('new_password')

        if not new_password:
            return self.error_response(message='請提供新密碼')

        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])

        return self.success_response(message='密碼重設成功')


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login view with rate limiting and online status tracking.
    F06-003: API 速率限制 - BR06-003-02: 登入 API 限制：每分鐘 5 次
    F06-002: 使用者在線狀態 - BR06-002-01: 使用者登入成功後加入在線列表
    """
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Update last login IP
            username = request.data.get('username')
            client_ip = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            try:
                user = User.objects.get(username=username)
                user.last_login_ip = client_ip
                user.login_attempts = 0
                user.save(update_fields=['last_login_ip', 'login_attempts'])

                # Mark user as online (F06-002)
                OnlineStatusService.user_login(
                    user_id=user.id,
                    ip=client_ip,
                    user_agent=user_agent
                )

                # Push audit log for login (F06-007)
                AuditQueueService.push(
                    user_id=user.id,
                    username=user.username,
                    action='LOGIN',
                    module='AUTH',
                    target_id=str(user.id),
                    target_type='User',
                    ip=client_ip,
                    user_agent=user_agent[:500] if user_agent else None
                )
            except User.DoesNotExist:
                pass

            return Response({
                'success': True,
                'message': '登入成功',
                'data': response.data
            })

        return response

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class LogoutView(StandardResponseMixin, APIView):
    """
    Logout view that blacklists the refresh token and updates online status.
    F06-001: JWT Token 黑名單
    F06-002: 使用者在線狀態 - BR06-002-02: 使用者登出後從在線列表移除
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            client_ip = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Blacklist refresh token using SimpleJWT's built-in blacklist
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Also add access token to Redis blacklist for immediate effect (F06-001)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header[7:]
                TokenBlacklistService.add_to_blacklist(
                    token=access_token,
                    user_id=user.id,
                    ttl_seconds=7200  # 2 hours (typical JWT lifetime)
                )

            # Mark user as offline (F06-002)
            OnlineStatusService.user_logout(user.id)

            # Push audit log for logout (F06-007)
            AuditQueueService.push(
                user_id=user.id,
                username=user.username,
                action='LOGOUT',
                module='AUTH',
                target_id=str(user.id),
                target_type='User',
                ip=client_ip,
                user_agent=user_agent[:500] if user_agent else None
            )

            return self.success_response(message='登出成功')
        except Exception as e:
            return self.error_response(message=f'登出失敗: {str(e)}')

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
