"""
Tests for core permission classes.
"""
import pytest
from unittest.mock import Mock, MagicMock
from apps.core.permissions import (
    IsAuthenticatedAndActive,
    HasModulePermission,
    IsAdminUser,
    IsOwnerOrAdmin,
)


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    return Mock()


@pytest.fixture
def mock_view():
    """Create a mock view object."""
    return Mock()


class TestIsAuthenticatedAndActive:
    """Tests for IsAuthenticatedAndActive permission."""

    def test_authenticated_active_user(self, mock_request, mock_view):
        """Test authenticated and active user has permission."""
        mock_request.user = Mock(is_authenticated=True, is_active=True)

        permission = IsAuthenticatedAndActive()
        assert permission.has_permission(mock_request, mock_view) is True

    def test_authenticated_inactive_user(self, mock_request, mock_view):
        """Test authenticated but inactive user is denied."""
        mock_request.user = Mock(is_authenticated=True, is_active=False)

        permission = IsAuthenticatedAndActive()
        assert permission.has_permission(mock_request, mock_view) is False

    def test_unauthenticated_user(self, mock_request, mock_view):
        """Test unauthenticated user is denied."""
        mock_request.user = Mock(is_authenticated=False, is_active=True)

        permission = IsAuthenticatedAndActive()
        assert permission.has_permission(mock_request, mock_view) is False

    def test_no_user(self, mock_request, mock_view):
        """Test request without user is denied."""
        mock_request.user = None

        permission = IsAuthenticatedAndActive()
        assert permission.has_permission(mock_request, mock_view) is False


class TestHasModulePermission:
    """Tests for HasModulePermission permission."""

    def test_superuser_has_permission(self, mock_request, mock_view):
        """Test superuser always has permission."""
        mock_request.user = Mock(is_authenticated=True, is_superuser=True)

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is True

    def test_user_without_role_denied(self, mock_request, mock_view):
        """Test user without role is denied."""
        mock_request.user = Mock(is_authenticated=True, is_superuser=False, role=None)

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is False

    def test_user_with_read_permission(self, mock_request, mock_view):
        """Test user with read permission for GET request."""
        mock_user = Mock(is_authenticated=True, is_superuser=False)
        mock_user.role = Mock()
        mock_user.has_module_permission = Mock(return_value=True)
        mock_request.user = mock_user
        mock_request.method = 'GET'

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is True
        mock_user.has_module_permission.assert_called_with('products', 'read')

    def test_user_with_write_permission(self, mock_request, mock_view):
        """Test user with write permission for POST request."""
        mock_user = Mock(is_authenticated=True, is_superuser=False)
        mock_user.role = Mock()
        mock_user.has_module_permission = Mock(return_value=True)
        mock_request.user = mock_user
        mock_request.method = 'POST'

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is True
        mock_user.has_module_permission.assert_called_with('products', 'write')

    def test_user_without_module_permission(self, mock_request, mock_view):
        """Test user without module permission is denied."""
        mock_user = Mock(is_authenticated=True, is_superuser=False)
        mock_user.role = Mock()
        mock_user.has_module_permission = Mock(return_value=False)
        mock_request.user = mock_user
        mock_request.method = 'GET'

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is False

    def test_unauthenticated_user(self, mock_request, mock_view):
        """Test unauthenticated user is denied."""
        mock_request.user = Mock(is_authenticated=False)

        permission = HasModulePermission()
        permission.module_name = 'products'
        assert permission.has_permission(mock_request, mock_view) is False


class TestIsAdminUser:
    """Tests for IsAdminUser permission."""

    def test_admin_user_has_permission(self, mock_request, mock_view):
        """Test admin user has permission."""
        mock_role = Mock(code='ADMIN')
        mock_request.user = Mock(is_authenticated=True, role=mock_role)

        permission = IsAdminUser()
        assert permission.has_permission(mock_request, mock_view) is True

    def test_non_admin_user_denied(self, mock_request, mock_view):
        """Test non-admin user is denied."""
        mock_role = Mock(code='CASHIER')
        mock_request.user = Mock(is_authenticated=True, role=mock_role)

        permission = IsAdminUser()
        assert permission.has_permission(mock_request, mock_view) is False

    def test_user_without_role_denied(self, mock_request, mock_view):
        """Test user without role is denied."""
        mock_request.user = Mock(is_authenticated=True, role=None)

        permission = IsAdminUser()
        assert permission.has_permission(mock_request, mock_view) is False

    def test_unauthenticated_user_denied(self, mock_request, mock_view):
        """Test unauthenticated user is denied."""
        mock_request.user = Mock(is_authenticated=False)
        mock_request.user.role = None

        permission = IsAdminUser()
        assert permission.has_permission(mock_request, mock_view) is False


class TestIsOwnerOrAdmin:
    """Tests for IsOwnerOrAdmin permission."""

    def test_superuser_has_permission(self, mock_request, mock_view):
        """Test superuser has object permission."""
        mock_request.user = Mock(is_superuser=True)
        mock_obj = Mock()

        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(mock_request, mock_view, mock_obj) is True

    def test_admin_has_permission(self, mock_request, mock_view):
        """Test admin user has object permission."""
        mock_role = Mock(code='ADMIN')
        mock_request.user = Mock(is_superuser=False, role=mock_role)
        mock_obj = Mock()

        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(mock_request, mock_view, mock_obj) is True

    def test_owner_has_permission(self, mock_request, mock_view):
        """Test object owner has permission."""
        mock_user = Mock(is_superuser=False)
        mock_user.role = None
        mock_request.user = mock_user
        mock_obj = Mock(created_by=mock_user)

        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(mock_request, mock_view, mock_obj) is True

    def test_non_owner_denied(self, mock_request, mock_view):
        """Test non-owner user is denied."""
        mock_user = Mock(is_superuser=False)
        mock_user.role = None
        mock_request.user = mock_user
        other_user = Mock()
        mock_obj = Mock(created_by=other_user)

        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(mock_request, mock_view, mock_obj) is False

    def test_object_without_created_by(self, mock_request, mock_view):
        """Test object without created_by attribute."""
        mock_user = Mock(is_superuser=False)
        mock_user.role = None
        mock_request.user = mock_user
        mock_obj = Mock(spec=[])  # No created_by attribute

        permission = IsOwnerOrAdmin()
        assert permission.has_object_permission(mock_request, mock_view, mock_obj) is False
