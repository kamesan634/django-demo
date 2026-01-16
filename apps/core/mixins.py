"""
Mixins for views and serializers.
"""
from rest_framework import status
from rest_framework.response import Response


class StandardResponseMixin:
    """Mixin for standard API responses."""

    def success_response(self, data=None, message='操作成功', status_code=status.HTTP_200_OK):
        """Return a success response."""
        response_data = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_data['data'] = data
        return Response(response_data, status=status_code)

    def error_response(self, message='操作失敗', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Return an error response."""
        response_data = {
            'success': False,
            'message': message,
        }
        if errors is not None:
            response_data['errors'] = errors
        return Response(response_data, status=status_code)

    def created_response(self, data=None, message='建立成功'):
        """Return a created response."""
        return self.success_response(data, message, status.HTTP_201_CREATED)

    def deleted_response(self, message='刪除成功'):
        """Return a deleted response."""
        return self.success_response(message=message, status_code=status.HTTP_200_OK)


class MultiSerializerMixin:
    """
    Mixin that allows different serializers for different actions.
    Usage:
        serializer_classes = {
            'list': ListSerializer,
            'retrieve': DetailSerializer,
            'create': CreateSerializer,
        }
    """
    serializer_classes = {}

    def get_serializer_class(self):
        """Return serializer class based on action."""
        return self.serializer_classes.get(
            self.action,
            super().get_serializer_class()
        )


class BulkOperationMixin:
    """Mixin for bulk create/update operations."""

    def bulk_create(self, request):
        """Bulk create records."""
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(
            {'success': True, 'message': f'成功建立 {len(serializer.data)} 筆資料'},
            status=status.HTTP_201_CREATED
        )

    def perform_bulk_create(self, serializer):
        """Perform the bulk create."""
        serializer.save(created_by=self.request.user)

    def bulk_update(self, request):
        """Bulk update records."""
        serializer = self.get_serializer(
            instance=self.get_queryset(),
            data=request.data,
            many=True,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_update(serializer)
        return Response(
            {'success': True, 'message': f'成功更新 {len(serializer.data)} 筆資料'},
            status=status.HTTP_200_OK
        )

    def perform_bulk_update(self, serializer):
        """Perform the bulk update."""
        serializer.save(updated_by=self.request.user)
