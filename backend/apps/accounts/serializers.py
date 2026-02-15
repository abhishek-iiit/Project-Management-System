"""
User and authentication serializers.

Following CLAUDE.md best practices:
- Efficient data transformation
- Validation in serializers
- Computed fields with annotations
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import APIKey

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for profile display.

    Read-only computed fields for full_name, short_name, initials.
    """

    full_name = serializers.CharField(source='full_name', read_only=True)
    short_name = serializers.CharField(source='short_name', read_only=True)
    initials = serializers.CharField(source='initials', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'short_name', 'initials',
            'avatar', 'bio', 'timezone', 'language', 'phone_number',
            'email_verified', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'email_verified']


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested relationships."""

    full_name = serializers.CharField(source='full_name', read_only=True)
    initials = serializers.CharField(source='initials', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'full_name', 'initials', 'avatar']
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration."""

    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, max_length=150, allow_blank=True)
    last_name = serializers.CharField(required=False, max_length=150, allow_blank=True)

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value.lower()

    def validate_username(self, value):
        """Validate username uniqueness and format."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this username already exists")

        # Validate username format
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        return value


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenSerializer(serializers.Serializer):
    """Serializer for JWT token response."""

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer for token refresh."""

    refresh = serializers.CharField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for profile updates."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'bio', 'avatar',
            'phone_number', 'timezone', 'language'
        ]


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API keys."""

    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'prefix', 'is_active',
            'scopes', 'expires_at', 'last_used_at',
            'created_at'
        ]
        read_only_fields = ['id', 'prefix', 'last_used_at', 'created_at']


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for API key creation."""

    key = serializers.CharField(read_only=True)  # Full key returned only on creation

    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key', 'prefix', 'scopes', 'expires_at']
        read_only_fields = ['id', 'key', 'prefix']
