"""
Base permission classes for the application.
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow owners of an object to edit it.
    Read-only access for everyone else.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        return obj.created_by == request.user


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the organization.
    Requires request.organization to be set by TenantMiddleware.
    """

    def has_permission(self, request, view):
        # Check if organization context is set
        if not hasattr(request, 'organization') or not request.organization:
            return False

        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # TenantMiddleware already validated membership
        return True

    def has_object_permission(self, request, view, obj):
        # Check if object belongs to the current organization
        if hasattr(obj, 'organization'):
            return obj.organization == request.organization

        # If object has project, check project's organization
        if hasattr(obj, 'project'):
            return obj.project.organization == request.organization

        # Default to True if no organization relationship
        return True


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin of the organization.
    """

    def has_permission(self, request, view):
        # Check if organization context is set
        if not hasattr(request, 'organization') or not request.organization:
            return False

        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is org admin
        from apps.organizations.models import OrganizationMember

        try:
            membership = OrganizationMember.objects.get(
                user=request.user,
                organization=request.organization,
                is_active=True
            )
            return membership.role in ['admin', 'owner']
        except OrganizationMember.DoesNotExist:
            return False


class IsProjectMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the project.
    """

    def has_object_permission(self, request, view, obj):
        # Get project from object
        project = obj if hasattr(obj, 'project_id') else getattr(obj, 'project', None)

        if not project:
            return False

        # Check if user is project member
        from apps.projects.models import ProjectMember

        return ProjectMember.objects.filter(
            project=project,
            user=request.user,
            is_active=True
        ).exists()


class IsProjectAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin of the project.
    """

    def has_object_permission(self, request, view, obj):
        # Get project from object
        project = obj if hasattr(obj, 'project_id') else getattr(obj, 'project', None)

        if not project:
            return False

        # Check if user is project admin
        from apps.projects.models import ProjectMember

        try:
            membership = ProjectMember.objects.get(
                project=project,
                user=request.user,
                is_active=True
            )
            return membership.role.permissions.get('is_admin', False)
        except ProjectMember.DoesNotExist:
            return False
