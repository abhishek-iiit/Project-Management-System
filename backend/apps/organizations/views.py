"""
Organization views.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Delegate to services
- Proper permissions
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, OrganizationMember, OrganizationInvitation
from apps.organizations.serializers import (
    OrganizationSerializer,
    OrganizationCreateSerializer,
    OrganizationMemberSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer,
    InviteMemberSerializer,
    OrganizationInvitationSerializer,
    AcceptInvitationSerializer,
)
from apps.organizations.services import OrganizationService
from apps.common.permissions import IsOrganizationMember, IsOrganizationAdmin

User = get_user_model()


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Organization CRUD operations.

    List: GET /api/v1/organizations/
    Create: POST /api/v1/organizations/
    Retrieve: GET /api/v1/organizations/{id}/
    Update: PUT /api/v1/organizations/{id}/
    Delete: DELETE /api/v1/organizations/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        """
        Get organizations where user is a member.

        Optimized with select_related/prefetch_related.
        """
        return Organization.objects.filter(
            members=self.request.user,
            organization_members__is_active=True
        ).select_related(
            'created_by'
        ).prefetch_related(
            'organization_members',
            'organization_members__user'
        ).distinct()

    def get_serializer_class(self):
        """Use different serializer for create."""
        if self.action == 'create':
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def create(self, request):
        """
        Create a new organization.

        POST /api/v1/organizations/
        {
            "name": "My Organization",
            "slug": "my-org",
            "description": "Description",
            "website": "https://example.com"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Delegate to service
            org_service = OrganizationService(user=request.user)
            organization = org_service.create_organization(serializer.validated_data)

            return Response({
                'status': 'success',
                'data': OrganizationSerializer(organization).data,
                'message': 'Organization created successfully'
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'ORGANIZATION_CREATE_FAILED',
                    'message': 'Failed to create organization',
                    'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Update organization details.

        PUT /api/v1/organizations/{id}/
        """
        organization = self.get_object()
        serializer = self.get_serializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            # Delegate to service
            org_service = OrganizationService(user=request.user)
            organization = org_service.update_organization(
                organization,
                serializer.validated_data
            )

            return Response({
                'status': 'success',
                'data': OrganizationSerializer(organization).data,
                'message': 'Organization updated successfully'
            }, status=status.HTTP_200_OK)

        except (ValidationError, PermissionDenied) as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'ORGANIZATION_UPDATE_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        Delete organization (soft delete).

        DELETE /api/v1/organizations/{id}/
        """
        organization = self.get_object()

        try:
            # Check permission (only owner can delete)
            org_service = OrganizationService(user=request.user)
            if not org_service._can_manage_organization(organization):
                raise PermissionDenied("Only organization owners can delete the organization")

            # Soft delete
            organization.delete()

            return Response({
                'status': 'success',
                'message': 'Organization deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)

        except PermissionDenied as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'ORGANIZATION_DELETE_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        List organization members.

        GET /api/v1/organizations/{id}/members/
        """
        organization = self.get_object()

        # Get active members with optimized query
        members = OrganizationMember.objects.filter(
            organization=organization,
            is_active=True
        ).select_related(
            'user',
            'invited_by'
        ).order_by('created_at')

        serializer = OrganizationMemberSerializer(members, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """
        Add a member to organization.

        POST /api/v1/organizations/{id}/add-member/
        {
            "user_id": "uuid",
            "role": "member"
        }
        """
        organization = self.get_object()
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get user
            user = User.objects.get(id=serializer.validated_data['user_id'])

            # Delegate to service
            org_service = OrganizationService(user=request.user)
            membership = org_service.add_member(
                organization,
                user,
                serializer.validated_data['role']
            )

            return Response({
                'status': 'success',
                'data': OrganizationMemberSerializer(membership).data,
                'message': 'Member added successfully'
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except (ValidationError, PermissionDenied) as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'ADD_MEMBER_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        Remove a member from organization.

        DELETE /api/v1/organizations/{id}/members/{user_id}/
        """
        organization = self.get_object()

        try:
            # Get user
            user = User.objects.get(id=user_id)

            # Delegate to service
            org_service = OrganizationService(user=request.user)
            org_service.remove_member(organization, user)

            return Response({
                'status': 'success',
                'message': 'Member removed successfully'
            }, status=status.HTTP_204_NO_CONTENT)

        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except (ValidationError, PermissionDenied) as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'REMOVE_MEMBER_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='members/(?P<user_id>[^/.]+)/role')
    def update_member_role(self, request, pk=None, user_id=None):
        """
        Update member's role.

        PUT /api/v1/organizations/{id}/members/{user_id}/role/
        {
            "role": "admin"
        }
        """
        organization = self.get_object()
        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get user
            user = User.objects.get(id=user_id)

            # Delegate to service
            org_service = OrganizationService(user=request.user)
            membership = org_service.update_member_role(
                organization,
                user,
                serializer.validated_data['role']
            )

            return Response({
                'status': 'success',
                'data': OrganizationMemberSerializer(membership).data,
                'message': 'Member role updated successfully'
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': 'User not found'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except (ValidationError, PermissionDenied) as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'UPDATE_ROLE_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """
        Invite a member to organization.

        POST /api/v1/organizations/{id}/invite/
        {
            "email": "user@example.com",
            "role": "member",
            "message": "Join our team!"
        }
        """
        organization = self.get_object()
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Delegate to service
            org_service = OrganizationService(user=request.user)
            invitation = org_service.invite_member(
                organization,
                serializer.validated_data['email'],
                serializer.validated_data.get('role', 'member'),
                serializer.validated_data.get('message', '')
            )

            return Response({
                'status': 'success',
                'data': OrganizationInvitationSerializer(invitation).data,
                'message': 'Invitation sent successfully'
            }, status=status.HTTP_201_CREATED)

        except (ValidationError, PermissionDenied) as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'INVITATION_FAILED',
                    'message': str(e),
                }
            }, status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied) else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def invitations(self, request, pk=None):
        """
        List organization invitations.

        GET /api/v1/organizations/{id}/invitations/
        """
        organization = self.get_object()

        # Get pending invitations
        invitations = OrganizationInvitation.objects.filter(
            organization=organization,
            status='pending'
        ).select_related(
            'invited_by'
        ).order_by('-created_at')

        serializer = OrganizationInvitationSerializer(invitations, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get organization statistics.

        GET /api/v1/organizations/{id}/stats/
        """
        organization = self.get_object()

        # Delegate to service
        org_service = OrganizationService(user=request.user)
        stats = org_service.get_organization_stats(organization)

        return Response({
            'status': 'success',
            'data': stats
        }, status=status.HTTP_200_OK)


class InvitationViewSet(viewsets.ViewSet):
    """
    Invitation operations.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='accept')
    def accept_invitation(self, request):
        """
        Accept an organization invitation.

        POST /api/v1/invitations/accept/
        {
            "token": "invitation_token"
        }
        """
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get invitation
            invitation = OrganizationInvitation.objects.get(
                token=serializer.validated_data['token']
            )

            # Accept invitation
            membership = invitation.accept(request.user)

            return Response({
                'status': 'success',
                'data': OrganizationMemberSerializer(membership).data,
                'message': 'Invitation accepted successfully'
            }, status=status.HTTP_200_OK)

        except OrganizationInvitation.DoesNotExist:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'INVITATION_NOT_FOUND',
                    'message': 'Invalid invitation token'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'INVITATION_INVALID',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
