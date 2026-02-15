"""
Organization serializers.

Following CLAUDE.md best practices.
"""

from rest_framework import serializers
from apps.organizations.models import Organization, OrganizationMember, OrganizationInvitation
from apps.accounts.serializers import UserMinimalSerializer


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Organization serializer with computed fields.
    """

    member_count = serializers.IntegerField(source='get_member_count', read_only=True)
    project_count = serializers.IntegerField(source='get_project_count', read_only=True)
    created_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'website',
            'email', 'phone',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'settings', 'is_active',
            'member_count', 'project_count',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def validate_slug(self, value):
        """Validate slug uniqueness."""
        # Check uniqueness (excluding current instance on update)
        qs = Organization.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Organization with this slug already exists")

        return value


class OrganizationMinimalSerializer(serializers.ModelSerializer):
    """Minimal organization serializer for nested relationships."""

    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'logo']
        read_only_fields = fields


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for organization creation."""

    class Meta:
        model = Organization
        fields = ['name', 'slug', 'description', 'website']

    def validate_slug(self, value):
        """Validate slug uniqueness."""
        if Organization.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Organization with this slug already exists")
        return value


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """
    Organization member serializer.
    """

    user = UserMinimalSerializer(read_only=True)
    organization = OrganizationMinimalSerializer(read_only=True)
    invited_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'user', 'role', 'is_active',
            'invited_by', 'invitation_accepted_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding a member to organization."""

    user_id = serializers.UUIDField(required=True)
    role = serializers.ChoiceField(
        choices=['owner', 'admin', 'member'],
        default='member'
    )


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating member role."""

    role = serializers.ChoiceField(
        choices=['owner', 'admin', 'member'],
        required=True
    )


class OrganizationInvitationSerializer(serializers.ModelSerializer):
    """Serializer for organization invitations."""

    organization = OrganizationMinimalSerializer(read_only=True)
    invited_by = UserMinimalSerializer(read_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = [
            'id', 'organization', 'email', 'role', 'status',
            'invited_by', 'message', 'expires_at',
            'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting a member."""

    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=['owner', 'admin', 'member'],
        default='member'
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting an invitation."""

    token = serializers.CharField(required=True)
