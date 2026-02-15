"""
Authentication service.

Following CLAUDE.md best practices:
- Thin views, fat services
- All business logic in services
- Transaction management
"""

from typing import Dict, Tuple
from django.db import transaction
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from apps.common.services import BaseService

User = get_user_model()


class AuthService(BaseService):
    """
    Authentication service for user registration, login, and token management.

    Handles:
    - User registration
    - Login with JWT tokens
    - Token refresh
    - Logout (token blacklisting)
    - Password management
    """

    @transaction.atomic
    def register_user(self, data: Dict) -> Tuple[User, Dict]:
        """
        Register a new user and create default organization.

        Args:
            data: User registration data
                - email: str
                - username: str
                - password: str
                - first_name: str (optional)
                - last_name: str (optional)

        Returns:
            Tuple of (User instance, tokens dict)

        Raises:
            ValidationError: If validation fails
        """
        # Validate email uniqueness
        if User.objects.filter(email=data['email']).exists():
            raise ValidationError({'email': 'User with this email already exists'})

        # Validate username uniqueness
        if User.objects.filter(username=data['username']).exists():
            raise ValidationError({'username': 'User with this username already exists'})

        # Create user
        user = User.objects.create_user(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )

        # Generate tokens
        tokens = self.generate_tokens(user)

        return user, tokens

    def login(self, email: str, password: str, ip_address: str = None) -> Tuple[User, Dict]:
        """
        Authenticate user and generate JWT tokens.

        Args:
            email: User email
            password: User password
            ip_address: IP address of login request

        Returns:
            Tuple of (User instance, tokens dict)

        Raises:
            ValidationError: If authentication fails
        """
        # Authenticate user
        user = authenticate(username=email, password=password)

        if user is None:
            raise ValidationError({'non_field_errors': 'Invalid email or password'})

        if not user.is_active:
            raise ValidationError({'non_field_errors': 'Account is inactive'})

        # Update last login info
        user.last_login = timezone.now()
        if ip_address:
            user.last_login_ip = ip_address
        user.save(update_fields=['last_login', 'last_login_ip'])

        # Generate tokens
        tokens = self.generate_tokens(user)

        return user, tokens

    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            Dict with new access token

        Raises:
            ValidationError: If token is invalid
        """
        try:
            token = RefreshToken(refresh_token)
            return {
                'access': str(token.access_token),
            }
        except Exception as e:
            raise ValidationError({'refresh': 'Invalid or expired refresh token'})

    def logout(self, refresh_token: str) -> None:
        """
        Logout user by blacklisting refresh token.

        Args:
            refresh_token: JWT refresh token

        Raises:
            ValidationError: If token is invalid
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            raise ValidationError({'refresh': 'Invalid refresh token'})

    def generate_tokens(self, user: User) -> Dict:
        """
        Generate JWT access and refresh tokens for user.

        Args:
            user: User instance

        Returns:
            Dict with access and refresh tokens
        """
        refresh = RefreshToken.for_user(user)

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    def verify_email(self, token: str) -> User:
        """
        Verify user email using verification token.

        Args:
            token: Email verification token

        Returns:
            User instance

        Raises:
            ValidationError: If token is invalid
        """
        try:
            user = User.objects.get(
                email_verification_token=token,
                email_verified=False
            )

            user.email_verified = True
            user.email_verification_token = None
            user.save(update_fields=['email_verified', 'email_verification_token'])

            return user

        except User.DoesNotExist:
            raise ValidationError({'token': 'Invalid verification token'})

    @transaction.atomic
    def change_password(self, user: User, old_password: str, new_password: str) -> User:
        """
        Change user password.

        Args:
            user: User instance
            old_password: Current password
            new_password: New password

        Returns:
            User instance

        Raises:
            ValidationError: If old password is incorrect
        """
        if not user.check_password(old_password):
            raise ValidationError({'old_password': 'Incorrect password'})

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return user

    def reset_password_request(self, email: str) -> User:
        """
        Generate password reset token and send email.

        Args:
            email: User email

        Returns:
            User instance

        Raises:
            ValidationError: If user not found
        """
        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            user.password_reset_token = reset_token
            user.password_reset_expires = timezone.now() + timezone.timedelta(hours=24)
            user.save(update_fields=['password_reset_token', 'password_reset_expires'])

            # TODO: Send email with reset link (implement in Phase 10)

            return user

        except User.DoesNotExist:
            # Don't reveal that user doesn't exist (security)
            pass

    @transaction.atomic
    def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user password using reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            User instance

        Raises:
            ValidationError: If token is invalid or expired
        """
        try:
            user = User.objects.get(password_reset_token=token)

            # Check if token expired
            if timezone.now() > user.password_reset_expires:
                raise ValidationError({'token': 'Reset token has expired'})

            # Set new password
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            user.save(update_fields=['password', 'password_reset_token', 'password_reset_expires'])

            return user

        except User.DoesNotExist:
            raise ValidationError({'token': 'Invalid reset token'})
