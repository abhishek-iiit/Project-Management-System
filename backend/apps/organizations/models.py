"""
Organization models for multi-tenancy.

Following CLAUDE.md best practices:
- Organization is the tenant root
- OrganizationMember maps users to organizations with roles
- All data is scoped to organizations
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.common.models import BaseModel, AuditMixin


class Organization(BaseModel, AuditMixin):
    """
    Organization model - root of multi-tenancy.

    All projects, issues, and data belong to an organization.
    Users can be members of multiple organizations.
    """

    name = models.CharField(
        _('name'),
        max_length=255,
        help_text=_('Organization name')
    )

    slug = models.SlugField(
        _('slug'),
        max_length=100,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9-]+$',
                message=_('Slug can only contain lowercase letters, numbers, and hyphens')
            )
        ],
        help_text=_('URL-friendly organization identifier')
    )

    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Organization description')
    )

    logo = models.URLField(
        _('logo URL'),
        blank=True,
        null=True,
        help_text=_('URL to organization logo')
    )

    website = models.URLField(
        _('website'),
        blank=True,
        null=True,
        help_text=_('Organization website')
    )

    # Contact information
    email = models.EmailField(
        _('email'),
        blank=True,
        null=True,
        help_text=_('Organization contact email')
    )

    phone = models.CharField(
        _('phone'),
        max_length=20,
        blank=True,
        null=True,
        help_text=_('Organization contact phone')
    )

    # Address fields
    address_line1 = models.CharField(
        _('address line 1'),
        max_length=255,
        blank=True,
        help_text=_('Street address')
    )

    address_line2 = models.CharField(
        _('address line 2'),
        max_length=255,
        blank=True,
        help_text=_('Apartment, suite, unit, etc.')
    )

    city = models.CharField(
        _('city'),
        max_length=100,
        blank=True,
        help_text=_('City')
    )

    state = models.CharField(
        _('state/province'),
        max_length=100,
        blank=True,
        help_text=_('State or province')
    )

    postal_code = models.CharField(
        _('postal code'),
        max_length=20,
        blank=True,
        help_text=_('Postal/ZIP code')
    )

    country = models.CharField(
        _('country'),
        max_length=100,
        blank=True,
        help_text=_('Country')
    )

    # Settings (JSONB for flexibility)
    settings = models.JSONField(
        _('settings'),
        default=dict,
        blank=True,
        help_text=_('Organization-specific settings')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this organization is active')
    )

    # Members relationship (defined via OrganizationMember)
    members = models.ManyToManyField(
        'accounts.User',
        through='OrganizationMember',
        through_fields=('organization', 'user'),  # Specify which FKs to use
        related_name='organizations',
        help_text=_('Users who are members of this organization')
    )

    class Meta:
        db_table = 'organizations'
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'name']),
        ]

    def __str__(self):
        """String representation."""
        return self.name

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<Organization id={self.id} slug={self.slug}>"

    def get_member_count(self):
        """
        Get count of active members.

        Returns:
            Integer count of active members
        """
        return self.organization_members.filter(is_active=True).count()

    def get_project_count(self):
        """
        Get count of projects in this organization.

        Returns:
            Integer count of projects
        """
        return self.projects.count()

    def get_owners(self):
        """
        Get all owners of this organization.

        Returns:
            QuerySet of User instances
        """
        return self.members.filter(
            organization_members__role='owner',
            organization_members__is_active=True
        )

    def get_admins(self):
        """
        Get all admins (owners + admins) of this organization.

        Returns:
            QuerySet of User instances
        """
        return self.members.filter(
            organization_members__role__in=['owner', 'admin'],
            organization_members__is_active=True
        )

    def add_member(self, user, role='member', invited_by=None):
        """
        Add a user to this organization.

        Args:
            user: User instance to add
            role: Role to assign (owner, admin, member)
            invited_by: User who invited this member

        Returns:
            OrganizationMember instance
        """
        return OrganizationMember.objects.create(
            organization=self,
            user=user,
            role=role,
            invited_by=invited_by
        )

    def remove_member(self, user):
        """
        Remove a user from this organization (soft delete).

        Args:
            user: User instance to remove
        """
        try:
            membership = OrganizationMember.objects.get(
                organization=self,
                user=user
            )
            membership.delete()  # Soft delete
        except OrganizationMember.DoesNotExist:
            pass

    def has_member(self, user):
        """
        Check if user is a member of this organization.

        Args:
            user: User instance

        Returns:
            Boolean
        """
        return OrganizationMember.objects.filter(
            organization=self,
            user=user,
            is_active=True
        ).exists()


class OrganizationMember(BaseModel, AuditMixin):
    """
    Organization membership - links users to organizations with roles.

    Defines what role a user has in an organization.
    """

    ROLE_CHOICES = [
        ('owner', _('Owner')),
        ('admin', _('Admin')),
        ('member', _('Member')),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='organization_members',
        help_text=_('Organization this membership belongs to')
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        help_text=_('User who is a member')
    )

    role = models.CharField(
        _('role'),
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        db_index=True,
        help_text=_('Role of the user in this organization')
    )

    is_active = models.BooleanField(
        _('is active'),
        default=True,
        db_index=True,
        help_text=_('Whether this membership is active')
    )

    # Invitation tracking
    invited_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organization_invitations_sent',
        help_text=_('User who invited this member')
    )

    invitation_accepted_at = models.DateTimeField(
        _('invitation accepted at'),
        blank=True,
        null=True,
        help_text=_('When the invitation was accepted')
    )

    # Custom permissions (JSONB for flexibility)
    custom_permissions = models.JSONField(
        _('custom permissions'),
        default=dict,
        blank=True,
        help_text=_('Custom permissions for this member')
    )

    class Meta:
        db_table = 'organization_members'
        verbose_name = _('organization member')
        verbose_name_plural = _('organization members')
        ordering = ['organization', 'user']
        unique_together = [['organization', 'user']]
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['organization', 'role', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        """String representation."""
        return f"{self.user.email} - {self.organization.name} ({self.role})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<OrganizationMember org={self.organization.slug} user={self.user.email} role={self.role}>"

    @property
    def is_owner(self):
        """Check if member is an owner."""
        return self.role == 'owner'

    @property
    def is_admin(self):
        """Check if member is an admin or owner."""
        return self.role in ['owner', 'admin']

    def can_manage_members(self):
        """Check if member can manage other members."""
        return self.is_admin

    def can_manage_projects(self):
        """Check if member can create/manage projects."""
        return self.is_admin

    def can_manage_settings(self):
        """Check if member can manage organization settings."""
        return self.is_owner


class OrganizationInvitation(BaseModel):
    """
    Pending invitations to join an organization.

    Sent to users who are not yet members.
    """

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('declined', _('Declined')),
        ('expired', _('Expired')),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text=_('Organization the invitation is for')
    )

    email = models.EmailField(
        _('email'),
        db_index=True,
        help_text=_('Email address of invitee')
    )

    role = models.CharField(
        _('role'),
        max_length=20,
        choices=OrganizationMember.ROLE_CHOICES,
        default='member',
        help_text=_('Role to assign upon acceptance')
    )

    invited_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent',
        help_text=_('User who sent the invitation')
    )

    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text=_('Invitation status')
    )

    token = models.CharField(
        _('token'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_('Unique token for invitation link')
    )

    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_('When this invitation expires')
    )

    accepted_at = models.DateTimeField(
        _('accepted at'),
        blank=True,
        null=True,
        help_text=_('When the invitation was accepted')
    )

    message = models.TextField(
        _('message'),
        blank=True,
        help_text=_('Optional message from inviter')
    )

    class Meta:
        db_table = 'organization_invitations'
        verbose_name = _('organization invitation')
        verbose_name_plural = _('organization invitations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        """String representation."""
        return f"Invitation to {self.email} for {self.organization.name}"

    @staticmethod
    def generate_token():
        """
        Generate a unique invitation token.

        Returns:
            String token
        """
        import secrets
        return secrets.token_urlsafe(32)

    def is_valid(self):
        """
        Check if invitation is still valid.

        Returns:
            Boolean
        """
        if self.status != 'pending':
            return False

        from django.utils import timezone
        if timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save(update_fields=['status', 'updated_at'])
            return False

        return True

    def accept(self, user):
        """
        Accept invitation and create organization membership.

        Args:
            user: User who is accepting

        Returns:
            OrganizationMember instance
        """
        from django.utils import timezone

        if not self.is_valid():
            raise ValueError("Invitation is not valid")

        if user.email != self.email:
            raise ValueError("Email mismatch")

        # Create membership
        membership = OrganizationMember.objects.create(
            organization=self.organization,
            user=user,
            role=self.role,
            invited_by=self.invited_by,
            invitation_accepted_at=timezone.now()
        )

        # Update invitation status
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at', 'updated_at'])

        return membership

    def decline(self):
        """Decline invitation."""
        self.status = 'declined'
        self.save(update_fields=['status', 'updated_at'])
