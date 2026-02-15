"""
Organization service for multi-tenancy management.

Following CLAUDE.MD best practices:
- Business logic in services
- Transaction management
- Permission validation
"""

from typing import Dict, List
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.utils.text import slugify
from apps.common.services import BaseService
from apps.organizations.models import Organization, OrganizationMember, OrganizationInvitation


class OrganizationService(BaseService):
    """
    Organization management service.

    Handles:
    - Organization creation
    - Member management
    - Invitations
    - Settings
    """

    @transaction.atomic
    def create_organization(self, data: Dict) -> Organization:
        """
        Create a new organization and add creator as owner.

        Args:
            data: Organization data
                - name: str
                - slug: str (optional, auto-generated from name)
                - description: str (optional)
                - ...

        Returns:
            Organization instance

        Raises:
            ValidationError: If validation fails
        """
        # Generate slug if not provided
        if 'slug' not in data or not data['slug']:
            data['slug'] = slugify(data['name'])

        # Validate slug uniqueness
        if Organization.objects.filter(slug=data['slug']).exists():
            raise ValidationError({'slug': 'Organization with this slug already exists'})

        # Create organization
        organization = Organization.objects.create(
            created_by=self.user,
            **data
        )

        # Add creator as owner
        OrganizationMember.objects.create(
            organization=organization,
            user=self.user,
            role='owner',
            created_by=self.user
        )

        return organization

    @transaction.atomic
    def update_organization(self, organization: Organization, data: Dict) -> Organization:
        """
        Update organization details.

        Args:
            organization: Organization instance
            data: Data to update

        Returns:
            Updated Organization instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_organization(organization):
            raise PermissionDenied("You don't have permission to update this organization")

        # Update fields
        allowed_fields = [
            'name', 'description', 'logo', 'website', 'email', 'phone',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(organization, field, data[field])

        organization.updated_by = self.user
        organization.save()

        return organization

    @transaction.atomic
    def add_member(self, organization: Organization, user, role: str = 'member') -> OrganizationMember:
        """
        Add a user to organization.

        Args:
            organization: Organization instance
            user: User to add
            role: Role to assign

        Returns:
            OrganizationMember instance

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If member already exists
        """
        # Check permission
        if not self._can_manage_members(organization):
            raise PermissionDenied("You don't have permission to add members")

        # Check if already member
        if OrganizationMember.objects.filter(
            organization=organization,
            user=user,
            is_active=True
        ).exists():
            raise ValidationError({'user': 'User is already a member'})

        # Create membership
        membership = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            role=role,
            invited_by=self.user,
            invitation_accepted_at=timezone.now(),
            created_by=self.user
        )

        return membership

    @transaction.atomic
    def remove_member(self, organization: Organization, user) -> None:
        """
        Remove a user from organization.

        Args:
            organization: Organization instance
            user: User to remove

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If trying to remove last owner
        """
        # Check permission
        if not self._can_manage_members(organization):
            raise PermissionDenied("You don't have permission to remove members")

        # Get membership
        try:
            membership = OrganizationMember.objects.get(
                organization=organization,
                user=user,
                is_active=True
            )
        except OrganizationMember.DoesNotExist:
            raise ValidationError({'user': 'User is not a member'})

        # Prevent removing last owner
        if membership.role == 'owner':
            owner_count = OrganizationMember.objects.filter(
                organization=organization,
                role='owner',
                is_active=True
            ).count()
            if owner_count <= 1:
                raise ValidationError({'user': 'Cannot remove the last owner'})

        # Soft delete membership
        membership.delete()

    @transaction.atomic
    def update_member_role(self, organization: Organization, user, new_role: str) -> OrganizationMember:
        """
        Update member's role.

        Args:
            organization: Organization instance
            user: User to update
            new_role: New role to assign

        Returns:
            Updated OrganizationMember instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_members(organization):
            raise PermissionDenied("You don't have permission to update member roles")

        # Get membership
        try:
            membership = OrganizationMember.objects.get(
                organization=organization,
                user=user,
                is_active=True
            )
        except OrganizationMember.DoesNotExist:
            raise ValidationError({'user': 'User is not a member'})

        # Update role
        membership.role = new_role
        membership.updated_by = self.user
        membership.save(update_fields=['role', 'updated_by', 'updated_at'])

        return membership

    @transaction.atomic
    def invite_member(
        self,
        organization: Organization,
        email: str,
        role: str = 'member',
        message: str = ''
    ) -> OrganizationInvitation:
        """
        Send invitation to join organization.

        Args:
            organization: Organization instance
            email: Email address to invite
            role: Role to assign
            message: Optional message

        Returns:
            OrganizationInvitation instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_members(organization):
            raise PermissionDenied("You don't have permission to invite members")

        # Check for existing invitation
        existing = OrganizationInvitation.objects.filter(
            organization=organization,
            email=email,
            status='pending'
        ).first()

        if existing:
            raise ValidationError({'email': 'Invitation already sent to this email'})

        # Create invitation
        invitation = OrganizationInvitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            invited_by=self.user,
            message=message,
            token=OrganizationInvitation.generate_token(),
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        # TODO: Send invitation email (Phase 10)

        return invitation

    def get_organization_stats(self, organization: Organization) -> Dict:
        """
        Get organization statistics.

        Args:
            organization: Organization instance

        Returns:
            Dict with organization stats
        """
        return {
            'members_count': organization.get_member_count(),
            'projects_count': organization.get_project_count(),
            'active_members': organization.organization_members.filter(is_active=True).count(),
            'pending_invitations': organization.invitations.filter(status='pending').count(),
        }

    # Permission helpers

    def _can_manage_organization(self, organization: Organization) -> bool:
        """Check if user can manage organization settings."""
        try:
            membership = OrganizationMember.objects.get(
                organization=organization,
                user=self.user,
                is_active=True
            )
            return membership.can_manage_settings()
        except OrganizationMember.DoesNotExist:
            return False

    def _can_manage_members(self, organization: Organization) -> bool:
        """Check if user can manage organization members."""
        try:
            membership = OrganizationMember.objects.get(
                organization=organization,
                user=self.user,
                is_active=True
            )
            return membership.can_manage_members()
        except OrganizationMember.DoesNotExist:
            return False
