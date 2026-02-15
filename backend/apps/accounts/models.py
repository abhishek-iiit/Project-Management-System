"""
User and authentication models.

Following CLAUDE.md best practices:
- Custom User model with UUID primary key
- Email-based authentication
- Profile information
- API key support
"""

import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimestampedModel, UUIDModel, SoftDeleteModel


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, username, password=None, **extra_fields):
        """
        Create and save a regular user with email and password.

        Args:
            email: User email address
            username: Username
            password: User password
            **extra_fields: Additional user fields

        Returns:
            User instance
        """
        if not email:
            raise ValueError(_('Email address is required'))
        if not username:
            raise ValueError(_('Username is required'))

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """
        Create and save a superuser with email and password.

        Args:
            email: User email address
            username: Username
            password: User password
            **extra_fields: Additional user fields

        Returns:
            Superuser instance
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser, UUIDModel, TimestampedModel, SoftDeleteModel):
    """
    Custom user model with UUID primary key and email authentication.

    Extends Django's AbstractUser with:
    - UUID primary key
    - Email as unique identifier
    - Timestamps (created_at, updated_at)
    - Soft delete support
    - Profile fields
    """

    # Override email to be unique and required
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        help_text=_('User email address (used for login)')
    )

    # Username is still required but not used for auth
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        db_index=True,
        help_text=_('Unique username for display')
    )

    # Profile fields
    first_name = models.CharField(
        _('first name'),
        max_length=150,
        blank=True,
        help_text=_('User first name')
    )

    last_name = models.CharField(
        _('last name'),
        max_length=150,
        blank=True,
        help_text=_('User last name')
    )

    avatar = models.URLField(
        _('avatar URL'),
        blank=True,
        null=True,
        help_text=_('URL to user avatar image')
    )

    bio = models.TextField(
        _('bio'),
        blank=True,
        max_length=500,
        help_text=_('Short bio about the user')
    )

    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='UTC',
        help_text=_('User timezone (e.g., America/New_York)')
    )

    language = models.CharField(
        _('language'),
        max_length=10,
        default='en',
        help_text=_('Preferred language code')
    )

    # Phone number (optional)
    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('User phone number')
    )

    # Email verification
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_('Whether user email is verified')
    )

    email_verification_token = models.CharField(
        _('email verification token'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Token for email verification')
    )

    # Last login tracking
    last_login_ip = models.GenericIPAddressField(
        _('last login IP'),
        blank=True,
        null=True,
        help_text=_('IP address of last login')
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_active', 'email_verified']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.email} ({self.username})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<User id={self.id} email={self.email}>"

    @property
    def full_name(self):
        """Return user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def short_name(self):
        """Return user's short name."""
        return self.first_name or self.username

    @property
    def initials(self):
        """Return user's initials."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    def get_organizations(self):
        """
        Get all organizations this user belongs to.

        Returns:
            QuerySet of Organization instances
        """
        from apps.organizations.models import Organization

        return Organization.objects.filter(
            members__user=self,
            members__is_active=True
        ).distinct()

    def get_organization_role(self, organization):
        """
        Get user's role in a specific organization.

        Args:
            organization: Organization instance

        Returns:
            Role string or None
        """
        from apps.organizations.models import OrganizationMember

        try:
            membership = OrganizationMember.objects.get(
                user=self,
                organization=organization,
                is_active=True
            )
            return membership.role
        except OrganizationMember.DoesNotExist:
            return None

    def is_organization_admin(self, organization):
        """
        Check if user is an admin of the organization.

        Args:
            organization: Organization instance

        Returns:
            Boolean
        """
        role = self.get_organization_role(organization)
        return role in ['owner', 'admin']

    def get_projects(self, organization=None):
        """
        Get all projects this user has access to.

        Args:
            organization: Optional organization to filter by

        Returns:
            QuerySet of Project instances
        """
        from apps.projects.models import Project

        qs = Project.objects.filter(
            members__user=self,
            members__is_active=True
        )

        if organization:
            qs = qs.filter(organization=organization)

        return qs.distinct()


class APIKey(UUIDModel, TimestampedModel, SoftDeleteModel):
    """
    API key for programmatic access.

    Allows users to authenticate via API key instead of JWT tokens.
    Useful for integrations, webhooks, and automated scripts.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text=_('User who owns this API key')
    )

    name = models.CharField(
        _('name'),
        max_length=100,
        help_text=_('Descriptive name for this API key')
    )

    key = models.CharField(
        _('key'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('The actual API key (hashed)')
    )

    prefix = models.CharField(
        _('prefix'),
        max_length=8,
        db_index=True,
        help_text=_('First 8 characters of key for identification')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether this API key is active')
    )

    last_used_at = models.DateTimeField(
        _('last used at'),
        blank=True,
        null=True,
        help_text=_('When this API key was last used')
    )

    last_used_ip = models.GenericIPAddressField(
        _('last used IP'),
        blank=True,
        null=True,
        help_text=_('IP address of last API key usage')
    )

    expires_at = models.DateTimeField(
        _('expires at'),
        blank=True,
        null=True,
        help_text=_('When this API key expires (null = never)')
    )

    # Permissions/scopes (JSONB)
    scopes = models.JSONField(
        _('scopes'),
        default=list,
        blank=True,
        help_text=_('List of permission scopes for this API key')
    )

    class Meta:
        db_table = 'api_keys'
        verbose_name = _('API key')
        verbose_name_plural = _('API keys')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['prefix']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.name} ({self.prefix}...)"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<APIKey id={self.id} user={self.user.email} prefix={self.prefix}>"

    @staticmethod
    def generate_key():
        """
        Generate a new API key.

        Returns:
            Tuple of (key, prefix) where key is the full key
        """
        import secrets
        key = secrets.token_urlsafe(32)
        prefix = key[:8]
        return key, prefix

    def revoke(self):
        """Revoke this API key (soft delete)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def is_valid(self):
        """
        Check if API key is valid (active and not expired).

        Returns:
            Boolean
        """
        if not self.is_active:
            return False

        if self.expires_at:
            from django.utils import timezone
            if timezone.now() > self.expires_at:
                return False

        return True

    def record_usage(self, ip_address=None):
        """
        Record API key usage.

        Args:
            ip_address: IP address of the request
        """
        from django.utils import timezone

        self.last_used_at = timezone.now()
        if ip_address:
            self.last_used_ip = ip_address
        self.save(update_fields=['last_used_at', 'last_used_ip', 'updated_at'])
