"""
Custom exception handling for the application.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns responses in a standard format.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'success': False,
            'error': {
                'code': exc.__class__.__name__,
                'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            }
        }

        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            custom_response['error']['details'] = exc.detail

        response.data = custom_response

    return response


class BusinessException(Exception):
    """Base exception for business logic errors."""
    def __init__(self, message, code='BUSINESS_ERROR'):
        self.message = message
        self.code = code
        super().__init__(message)


class InsufficientStockError(BusinessException):
    """Exception raised when stock is insufficient."""
    def __init__(self, product_name, required, available):
        message = f'商品 {product_name} 庫存不足，需要 {required}，可用 {available}'
        super().__init__(message, 'INSUFFICIENT_STOCK')


class InvalidOperationError(BusinessException):
    """Exception raised for invalid operations."""
    def __init__(self, message):
        super().__init__(message, 'INVALID_OPERATION')


class ValidationError(BusinessException):
    """Exception raised for validation errors."""
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message, 'VALIDATION_ERROR')


class PermissionDeniedError(BusinessException):
    """Exception raised when user doesn't have permission."""
    def __init__(self, message='您沒有權限執行此操作'):
        super().__init__(message, 'PERMISSION_DENIED')
