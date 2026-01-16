"""
Account serializers.
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Role, UserStore


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer."""
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'code', 'description',
            'permissions', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserListSerializer(serializers.ModelSerializer):
    """User list serializer (minimal fields)."""
    role_name = serializers.CharField(source='role.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'display_name',
            'phone', 'role', 'role_name', 'status', 'status_display',
            'is_active', 'last_login', 'created_at'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """User detail serializer (full fields)."""
    role = RoleSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stores = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'display_name',
            'phone', 'role', 'status', 'status_display',
            'is_active', 'is_staff', 'last_login',
            'last_login_ip', 'password_changed_at',
            'stores', 'created_at', 'updated_at'
        ]

    def get_stores(self, obj):
        """Get user's assigned stores."""
        user_stores = obj.user_stores.select_related('store').all()
        return [
            {
                'id': us.store.id,
                'name': us.store.name,
                'code': us.store.code,
                'is_primary': us.is_primary
            }
            for us in user_stores
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    """User create serializer."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    store_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    primary_store_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'display_name', 'phone',
            'role', 'password', 'password_confirm',
            'store_ids', 'primary_store_id'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '密碼不一致'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        store_ids = validated_data.pop('store_ids', [])
        primary_store_id = validated_data.pop('primary_store_id', None)

        user = User.objects.create_user(**validated_data)

        # Assign stores
        for store_id in store_ids:
            UserStore.objects.create(
                user=user,
                store_id=store_id,
                is_primary=(store_id == primary_store_id)
            )

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """User update serializer."""
    store_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    primary_store_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'email', 'display_name', 'phone',
            'role', 'status', 'is_active',
            'store_ids', 'primary_store_id'
        ]

    def update(self, instance, validated_data):
        store_ids = validated_data.pop('store_ids', None)
        primary_store_id = validated_data.pop('primary_store_id', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update stores if provided
        if store_ids is not None:
            instance.user_stores.all().delete()
            for store_id in store_ids:
                UserStore.objects.create(
                    user=instance,
                    store_id=store_id,
                    is_primary=(store_id == primary_store_id)
                )

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': '新密碼不一致'})
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('舊密碼不正確')
        return value


class LoginSerializer(serializers.Serializer):
    """Login serializer."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
