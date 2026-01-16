"""
Core views and viewsets for the application.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .pagination import StandardPagination
from .permissions import IsAuthenticatedAndActive


class BaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet with common functionality."""
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def perform_create(self, serializer):
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)

    def get_queryset(self):
        """Filter out soft-deleted records by default."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        return queryset

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete the instance."""
        instance = self.get_object()
        if hasattr(instance, 'soft_delete'):
            instance.soft_delete(user=request.user)
            return Response(
                {'success': True, 'message': '刪除成功'},
                status=status.HTTP_200_OK
            )
        return Response(
            {'success': False, 'message': '此資源不支援軟刪除'},
            status=status.HTTP_400_BAD_REQUEST
        )


class ReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet."""
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticatedAndActive]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    def get_queryset(self):
        """Filter out soft-deleted records by default."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, 'is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        return queryset
