"""
Custom permissions for the application.
"""
from rest_framework import permissions


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Permission that checks if user is authenticated and active.
    """
    def has_permission(self, request, view):
        if not request.user:
            return False
        return (
            request.user.is_authenticated and
            request.user.is_active
        )


class HasModulePermission(permissions.BasePermission):
    """
    Permission that checks module-level access based on user role.
    """
    module_name = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not hasattr(request.user, 'role') or not request.user.role:
            return False

        # Read operations
        if request.method in permissions.SAFE_METHODS:
            return request.user.has_module_permission(self.module_name, 'read')

        # Write operations
        return request.user.has_module_permission(self.module_name, 'write')


class IsAdminUser(permissions.BasePermission):
    """
    Permission that allows access only to admin users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        return request.user.role.code == 'ADMIN'


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission that allows access to owner or admin users.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'role') and request.user.role:
            if request.user.role.code == 'ADMIN':
                return True

        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user

        return False


class IsManagerOrAbove(permissions.BasePermission):
    """
    Permission that allows access to managers and above (admin, store manager).
    """
    ALLOWED_ROLES = ['ADMIN', 'STORE_MANAGER']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'role') and request.user.role:
            return request.user.role.code in self.ALLOWED_ROLES

        return False


class IsWarehouseStaffOrAbove(permissions.BasePermission):
    """
    Permission that allows access to warehouse staff and above.
    """
    ALLOWED_ROLES = ['ADMIN', 'STORE_MANAGER', 'WAREHOUSE_STAFF', 'PURCHASER']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'role') and request.user.role:
            return request.user.role.code in self.ALLOWED_ROLES

        return False
