"""
Tests for accounts models.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()


@pytest.mark.django_db
class TestRoleModel:
    """Tests for Role model."""

    def test_create_role(self):
        """Test creating a role."""
        role = Role.objects.create(
            name='店長',
            code='STORE_MANAGER',
            permissions={'stores': ['read', 'update']}
        )
        assert role.name == '店長'
        assert role.code == 'STORE_MANAGER'
        assert role.is_active is True

    def test_role_str(self):
        """Test role string representation."""
        role = Role.objects.create(name='測試角色', code='TEST')
        assert '測試角色' in str(role)
        assert 'TEST' in str(role)


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, create_user):
        """Test creating a regular user."""
        user = create_user(
            username='testuser',
            email='test@example.com',
            display_name='測試使用者'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.display_name == '測試使用者'
        assert user.is_superuser is False
        assert user.check_password('testpass123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_user_str(self, create_user):
        """Test user string representation."""
        user = create_user(username='john', display_name='John Doe')
        assert 'john' in str(user).lower() or 'John' in str(user)

    def test_user_with_role(self, create_user, create_role):
        """Test user with assigned role."""
        role = create_role(name='收銀員', code='CASHIER')
        user = create_user(username='cashier1', role=role)
        assert user.role == role
        assert user.role.code == 'CASHIER'

    def test_user_lock_account(self, create_user):
        """Test user account lock functionality."""
        user = create_user(username='tolock')
        user.lock_account()

        assert user.status == 'LOCKED'

    def test_user_unlock_account(self, create_user):
        """Test user account unlock functionality."""
        user = create_user(username='tounlock')
        user.lock_account()
        user.unlock_account()

        assert user.status == 'ACTIVE'
        assert user.login_attempts == 0
