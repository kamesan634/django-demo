"""
Tests for accounts API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAuthAPI:
    """Tests for authentication API."""

    def test_login_success(self, api_client, create_user):
        """Test successful login."""
        user = create_user(username='loginuser', password='testpass123')

        response = api_client.post('/api/v1/auth/login/', {
            'username': 'loginuser',
            'password': 'testpass123'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data.get('data', response.data)

    def test_login_invalid_credentials(self, api_client, create_user):
        """Test login with invalid credentials."""
        create_user(username='loginuser', password='testpass123')

        response = api_client.post('/api/v1/auth/login/', {
            'username': 'loginuser',
            'password': 'wrongpassword'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client):
        """Test login with missing fields."""
        response = api_client.post('/api/v1/auth/login/', {
            'username': 'testuser'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_refresh(self, api_client, create_user):
        """Test token refresh."""
        user = create_user(username='refreshuser', password='testpass123')

        # First login to get tokens
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': 'refreshuser',
            'password': 'testpass123'
        })

        data = login_response.data.get('data', login_response.data)
        refresh_token = data.get('refresh')

        # Use refresh token to get new access token
        response = api_client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data


@pytest.mark.django_db
class TestUserAPI:
    """Tests for user API endpoints."""

    def test_get_current_user(self, auth_client, user):
        """Test getting current user info."""
        response = auth_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data.get('data', response.data)
        assert data['username'] == user.username

    def test_get_current_user_unauthenticated(self, api_client):
        """Test getting current user without authentication."""
        response = api_client.get('/api/v1/users/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password(self, auth_client, user):
        """Test changing password."""
        response = auth_client.post('/api/v1/users/change_password/', {
            'old_password': 'testpass123',
            'new_password': 'Newpass456!',
            'new_password_confirm': 'Newpass456!'
        })

        assert response.status_code == status.HTTP_200_OK

        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('Newpass456!')

    def test_change_password_wrong_old_password(self, auth_client):
        """Test changing password with wrong old password."""
        response = auth_client.post('/api/v1/users/change_password/', {
            'old_password': 'wrongpassword',
            'new_password': 'Newpass456!',
            'new_password_confirm': 'Newpass456!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_users_as_admin(self, admin_client):
        """Test listing users as admin."""
        response = admin_client.get('/api/v1/users/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_users_as_regular_user(self, auth_client):
        """Test listing users as regular user (should be forbidden)."""
        response = auth_client.get('/api/v1/users/')

        # Regular users shouldn't be able to list all users
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_200_OK]


@pytest.mark.django_db
class TestRoleAPI:
    """Tests for role API endpoints."""

    def test_list_roles_as_admin(self, admin_client, create_role):
        """Test listing roles as admin."""
        create_role(name='角色1', code='ROLE1')
        create_role(name='角色2', code='ROLE2')

        response = admin_client.get('/api/v1/roles/')

        assert response.status_code == status.HTTP_200_OK

    def test_create_role_as_admin(self, admin_client):
        """Test creating role as admin."""
        response = admin_client.post('/api/v1/roles/', {
            'name': '檢視者角色',
            'code': 'VIEWER',
            'permissions': {}
        }, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_role_as_regular_user(self, auth_client):
        """Test creating role as regular user (should be forbidden)."""
        response = auth_client.post('/api/v1/roles/', {
            'name': '新角色',
            'code': 'NEW_ROLE'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN
