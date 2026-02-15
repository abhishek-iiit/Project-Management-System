"""
Project service for project management.

Following CLAUDE.md best practices:
- Business logic in services
- Transaction management
- Permission validation
"""

from typing import Dict, Optional
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.text import slugify
from apps.common.services import BaseService
from apps.projects.models import Project, ProjectMember, ProjectRole, ProjectTemplate


class ProjectService(BaseService):
    """
    Project management service.

    Handles:
    - Project creation
    - Member management
    - Role management
    - Settings
    """

    @transaction.atomic
    def create_project(self, organization, data: Dict) -> Project:
        """
        Create a new project and add creator as admin.

        Args:
            organization: Organization instance
            data: Project data
                - name: str
                - key: str
                - description: str (optional)
                - project_type: str (optional)
                - template: str (optional)
                ...

        Returns:
            Project instance

        Raises:
            ValidationError: If validation fails
            PermissionDenied: If user lacks permission
        """
        # Check if user has permission to create projects in org
        if not self._can_create_project(organization):
            raise PermissionDenied("You don't have permission to create projects in this organization")

        # Validate key uniqueness within organization
        if Project.objects.filter(organization=organization, key=data['key']).exists():
            raise ValidationError({'key': 'Project with this key already exists in the organization'})

        # Set lead to current user if not specified
        if 'lead' not in data or not data['lead']:
            data['lead'] = self.user

        # Create project
        project = Project.objects.create(
            organization=organization,
            created_by=self.user,
            **data
        )

        # Add creator as project admin
        ProjectMember.objects.create(
            project=project,
            user=self.user,
            is_admin=True,
            created_by=self.user
        )

        return project

    @transaction.atomic
    def update_project(self, project: Project, data: Dict) -> Project:
        """
        Update project details.

        Args:
            project: Project instance
            data: Data to update

        Returns:
            Updated Project instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_project(project):
            raise PermissionDenied("You don't have permission to update this project")

        # Update fields
        allowed_fields = [
            'name', 'description', 'avatar', 'lead', 'project_type',
            'template', 'settings', 'is_active', 'is_private'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(project, field, data[field])

        project.updated_by = self.user
        project.save()

        return project

    @transaction.atomic
    def add_member(self, project: Project, user, role: Optional[ProjectRole] = None, is_admin: bool = False) -> ProjectMember:
        """
        Add a user to project.

        Args:
            project: Project instance
            user: User to add
            role: Optional ProjectRole instance
            is_admin: Whether user is project admin

        Returns:
            ProjectMember instance

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If member already exists
        """
        # Check permission
        if not self._can_manage_members(project):
            raise PermissionDenied("You don't have permission to add members")

        # Check if already member
        if ProjectMember.objects.filter(
            project=project,
            user=user,
            is_active=True
        ).exists():
            raise ValidationError({'user': 'User is already a project member'})

        # Create membership
        membership = ProjectMember.objects.create(
            project=project,
            user=user,
            role=role,
            is_admin=is_admin,
            created_by=self.user
        )

        return membership

    @transaction.atomic
    def remove_member(self, project: Project, user) -> None:
        """
        Remove a user from project.

        Args:
            project: Project instance
            user: User to remove

        Raises:
            PermissionDenied: If user lacks permission
            ValidationError: If trying to remove last admin
        """
        # Check permission
        if not self._can_manage_members(project):
            raise PermissionDenied("You don't have permission to remove members")

        # Get membership
        try:
            membership = ProjectMember.objects.get(
                project=project,
                user=user,
                is_active=True
            )
        except ProjectMember.DoesNotExist:
            raise ValidationError({'user': 'User is not a project member'})

        # Prevent removing last admin
        if membership.is_admin:
            admin_count = ProjectMember.objects.filter(
                project=project,
                is_admin=True,
                is_active=True
            ).count()
            if admin_count <= 1:
                raise ValidationError({'user': 'Cannot remove the last project admin'})

        # Soft delete membership
        membership.delete()

    @transaction.atomic
    def update_member_role(self, project: Project, user, role: Optional[ProjectRole] = None, is_admin: Optional[bool] = None) -> ProjectMember:
        """
        Update member's role or admin status.

        Args:
            project: Project instance
            user: User to update
            role: Optional new ProjectRole
            is_admin: Optional new admin status

        Returns:
            Updated ProjectMember instance

        Raises:
            PermissionDenied: If user lacks permission
        """
        # Check permission
        if not self._can_manage_members(project):
            raise PermissionDenied("You don't have permission to update member roles")

        # Get membership
        try:
            membership = ProjectMember.objects.get(
                project=project,
                user=user,
                is_active=True
            )
        except ProjectMember.DoesNotExist:
            raise ValidationError({'user': 'User is not a project member'})

        # Update role
        if role is not None:
            membership.role = role

        if is_admin is not None:
            membership.is_admin = is_admin

        membership.updated_by = self.user
        membership.save()

        return membership

    def get_project_stats(self, project: Project) -> Dict:
        """
        Get project statistics.

        Args:
            project: Project instance

        Returns:
            Dict with project stats
        """
        return {
            'members_count': project.get_member_count(),
            'issues_count': project.get_issue_count(),
            'admins_count': project.project_members.filter(is_admin=True, is_active=True).count(),
        }

    @transaction.atomic
    def create_from_template(self, organization, template: ProjectTemplate, data: Dict) -> Project:
        """
        Create project from template.

        Args:
            organization: Organization instance
            template: ProjectTemplate instance
            data: Project data (name, key)

        Returns:
            Project instance
        """
        # Merge template config with provided data
        project_data = {
            'project_type': template.template_type,
            'template': template.template_type,
            'settings': template.config.get('settings', {}),
            **data
        }

        # Create project
        project = self.create_project(organization, project_data)

        # TODO: Apply template configuration (workflows, roles, etc.)
        # This will be implemented when we build workflows and custom fields

        return project

    # Permission helpers

    def _can_create_project(self, organization) -> bool:
        """Check if user can create projects in organization."""
        from apps.organizations.models import OrganizationMember

        try:
            membership = OrganizationMember.objects.get(
                organization=organization,
                user=self.user,
                is_active=True
            )
            return membership.can_manage_projects()
        except OrganizationMember.DoesNotExist:
            return False

    def _can_manage_project(self, project: Project) -> bool:
        """Check if user can manage project settings."""
        # Project lead can manage
        if project.lead == self.user:
            return True

        # Project admins can manage
        try:
            membership = ProjectMember.objects.get(
                project=project,
                user=self.user,
                is_active=True
            )
            return membership.is_admin
        except ProjectMember.DoesNotExist:
            return False

    def _can_manage_members(self, project: Project) -> bool:
        """Check if user can manage project members."""
        return self._can_manage_project(project)
