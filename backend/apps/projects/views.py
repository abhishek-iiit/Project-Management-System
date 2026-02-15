"""
Project views for API endpoints.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Business logic delegated to services
- Optimized queries with select_related/prefetch_related
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.projects.models import Project, ProjectMember, ProjectRole, ProjectTemplate
from apps.projects.serializers import (
    ProjectSerializer,
    ProjectMinimalSerializer,
    ProjectCreateSerializer,
    ProjectMemberSerializer,
    ProjectRoleSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer,
    ProjectTemplateSerializer,
)
from apps.projects.services.project_service import ProjectService
from apps.organizations.models import Organization

User = get_user_model()


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project management endpoints.

    Provides CRUD operations for projects with member management.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ProjectCreateSerializer
        elif self.action == 'list':
            return ProjectMinimalSerializer
        return ProjectSerializer

    def get_queryset(self):
        """
        Get optimized queryset with proper filtering.

        Uses .with_full_details() for optimal query performance.
        Filters to projects user has access to.
        """
        # Get organization from header
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Project.objects.none()

        # Base queryset with optimizations
        queryset = Project.objects.with_full_details()

        # Filter by organization
        queryset = queryset.for_organization(organization_id)

        # Filter by user membership (users see projects they're members of)
        queryset = queryset.filter(
            project_members__user=self.request.user,
            project_members__is_active=True
        ).distinct()

        # Query params filtering
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        project_type = self.request.query_params.get('type')
        if project_type:
            queryset = queryset.filter(project_type=project_type)

        return queryset

    def create(self, request):
        """
        Create a new project.

        Delegates to ProjectService for business logic.
        Automatically adds creator as admin member.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get organization
        organization = serializer.validated_data['organization']

        # Delegate to service
        service = ProjectService(user=request.user)
        project = service.create_project(
            organization=organization,
            data=serializer.validated_data
        )

        # Return full project details
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update project details."""
        project = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = ProjectService(user=request.user)
        updated_project = service.update_project(
            project=project,
            data=serializer.validated_data
        )

        return Response(
            ProjectSerializer(updated_project).data
        )

    def destroy(self, request, pk=None):
        """Soft delete project."""
        project = self.get_object()

        # Delegate to service for permission check and deletion
        service = ProjectService(user=request.user)

        # Check permission using service method
        if not service._can_manage_project(project):
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'PERMISSION_DENIED',
                        'message': 'You do not have permission to delete this project'
                    }
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Soft delete
        project.delete()

        return Response(
            {
                'status': 'success',
                'message': 'Project deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get project members."""
        project = self.get_object()

        # Optimized query for members
        members = ProjectMember.objects.filter(
            project=project,
            is_active=True
        ).select_related(
            'user', 'role', 'created_by'
        ).order_by('-is_admin', 'user__first_name')

        serializer = ProjectMemberSerializer(members, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to project."""
        project = self.get_object()

        serializer = AddMemberSerializer(
            data=request.data,
            context={'project': project, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = ProjectService(user=request.user)
        membership = service.add_member(
            project=project,
            user=serializer.validated_data['user'],
            role=serializer.validated_data.get('role'),
            is_admin=serializer.validated_data.get('is_admin', False)
        )

        return Response(
            {
                'status': 'success',
                'data': ProjectMemberSerializer(membership).data,
                'message': 'Member added successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """Remove a member from project."""
        project = self.get_object()
        user = get_object_or_404(User, id=user_id)

        # Delegate to service
        service = ProjectService(user=request.user)
        service.remove_member(project=project, user=user)

        return Response(
            {
                'status': 'success',
                'message': 'Member removed successfully'
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['put'], url_path='members/(?P<user_id>[^/.]+)')
    def update_member(self, request, pk=None, user_id=None):
        """Update member role or admin status."""
        project = self.get_object()
        user = get_object_or_404(User, id=user_id)

        serializer = UpdateMemberRoleSerializer(
            data=request.data,
            context={'project': project, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        service = ProjectService(user=request.user)
        membership = service.update_member_role(
            project=project,
            user=user,
            role=serializer.validated_data.get('role'),
            is_admin=serializer.validated_data.get('is_admin')
        )

        return Response(
            {
                'status': 'success',
                'data': ProjectMemberSerializer(membership).data,
                'message': 'Member updated successfully'
            }
        )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get project statistics."""
        project = self.get_object()

        # Delegate to service
        service = ProjectService(user=request.user)
        stats = service.get_project_stats(project)

        return Response({
            'status': 'success',
            'data': stats
        })


class ProjectRoleViewSet(viewsets.ModelViewSet):
    """
    Project role management endpoints.

    Provides CRUD operations for custom project roles.
    """

    serializer_class = ProjectRoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get roles for user's current organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return ProjectRole.objects.none()

        return ProjectRole.objects.filter(
            organization_id=organization_id
        ).select_related('organization').order_by('name')

    def create(self, request):
        """Create a new project role."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get organization
        organization_id = request.headers.get('X-Organization-ID')
        organization = get_object_or_404(Organization, id=organization_id)

        # Create role
        role = ProjectRole.objects.create(
            organization=organization,
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(role).data,
                'message': 'Role created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update project role."""
        role = self.get_object()
        serializer = self.get_serializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update role
        for field, value in serializer.validated_data.items():
            setattr(role, field, value)

        role.updated_by = request.user
        role.save()

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(role).data,
                'message': 'Role updated successfully'
            }
        )

    def destroy(self, request, pk=None):
        """Delete project role."""
        role = self.get_object()

        # Check if role is in use
        if ProjectMember.objects.filter(role=role, is_active=True).exists():
            return Response(
                {
                    'status': 'error',
                    'error': {
                        'code': 'ROLE_IN_USE',
                        'message': 'Cannot delete role that is currently assigned to members'
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Soft delete
        role.delete()

        return Response(
            {
                'status': 'success',
                'message': 'Role deleted successfully'
            },
            status=status.HTTP_204_NO_CONTENT
        )


class ProjectTemplateViewSet(viewsets.ModelViewSet):
    """
    Project template management endpoints.

    Provides CRUD operations for project templates.
    """

    serializer_class = ProjectTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get templates for user's current organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return ProjectTemplate.objects.none()

        return ProjectTemplate.objects.filter(
            organization_id=organization_id
        ).select_related('organization').order_by('name')

    def create(self, request):
        """Create a new project template."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get organization
        organization_id = request.headers.get('X-Organization-ID')
        organization = get_object_or_404(Organization, id=organization_id)

        # Create template
        template = ProjectTemplate.objects.create(
            organization=organization,
            created_by=request.user,
            **serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': self.get_serializer(template).data,
                'message': 'Template created successfully'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def create_project(self, request, pk=None):
        """Create a project from this template."""
        template = self.get_object()

        # Validate project data
        serializer = ProjectCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Get organization
        organization = serializer.validated_data['organization']

        # Delegate to service
        service = ProjectService(user=request.user)
        project = service.create_from_template(
            organization=organization,
            template=template,
            data=serializer.validated_data
        )

        return Response(
            {
                'status': 'success',
                'data': ProjectSerializer(project).data,
                'message': 'Project created from template successfully'
            },
            status=status.HTTP_201_CREATED
        )
