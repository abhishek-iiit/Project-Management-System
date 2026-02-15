"""
Field views.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Delegate to service layer
- Proper permissions
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.fields.models import FieldDefinition, FieldContext, FieldScheme, FieldType
from apps.fields.services import FieldService
from apps.fields.serializers import (
    FieldDefinitionSerializer,
    FieldDefinitionCreateSerializer,
    FieldDefinitionUpdateSerializer,
    FieldContextSerializer,
    FieldContextCreateSerializer,
    FieldSchemeSerializer,
    FieldSchemeCreateSerializer,
    FieldTypeSerializer,
    FieldRenderConfigSerializer,
    FieldValidationSerializer,
    BulkFieldContextCreateSerializer,
    FieldReorderSerializer,
    FieldConfigUpdateSerializer,
    CopyFieldContextsSerializer,
)
from apps.common.permissions import IsOrganizationMember


class FieldDefinitionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for field definitions.

    Endpoints:
    - GET /field-definitions/ - List all field definitions
    - POST /field-definitions/ - Create field definition
    - GET /field-definitions/{id}/ - Get field definition
    - PUT /field-definitions/{id}/ - Update field definition
    - PATCH /field-definitions/{id}/ - Partial update field definition
    - DELETE /field-definitions/{id}/ - Delete field definition
    - POST /field-definitions/reorder/ - Reorder fields
    - GET /field-definitions/types/ - Get available field types
    - POST /field-definitions/{id}/validate/ - Validate field value
    - GET /field-definitions/{id}/render-config/ - Get render configuration
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = FieldDefinitionSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get field definitions for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return FieldDefinition.objects.none()

        return FieldDefinition.objects.filter(
            organization=self.request.user.current_organization
        ).order_by('position', 'name')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return FieldDefinitionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FieldDefinitionUpdateSerializer
        return FieldDefinitionSerializer

    @extend_schema(
        summary="List field definitions",
        parameters=[
            OpenApiParameter('is_active', bool, description='Filter by active status'),
            OpenApiParameter('field_type', str, description='Filter by field type'),
        ]
    )
    def list(self, request):
        """List field definitions with optional filters."""
        service = FieldService(user=request.user)

        # Get filter parameters
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'

        field_type = request.query_params.get('field_type')

        # Get fields
        fields = service.list_field_definitions(
            is_active=is_active,
            field_type=field_type
        )

        serializer = self.get_serializer(fields, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create field definition")
    def create(self, request):
        """Create a new field definition."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        field = service.create_field_definition(serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldDefinitionSerializer(field).data,
            'message': 'Field definition created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get field definition")
    def retrieve(self, request, id=None):
        """Get a specific field definition."""
        service = FieldService(user=request.user)
        field = service.get_field_definition(id)

        serializer = self.get_serializer(field)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update field definition")
    def update(self, request, id=None):
        """Update a field definition."""
        service = FieldService(user=request.user)
        field = service.get_field_definition(id)

        serializer = self.get_serializer(field, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_field = service.update_field_definition(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldDefinitionSerializer(updated_field).data,
            'message': 'Field definition updated successfully'
        })

    @extend_schema(summary="Partially update field definition")
    def partial_update(self, request, id=None):
        """Partially update a field definition."""
        service = FieldService(user=request.user)
        field = service.get_field_definition(id)

        serializer = self.get_serializer(field, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_field = service.update_field_definition(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldDefinitionSerializer(updated_field).data,
            'message': 'Field definition updated successfully'
        })

    @extend_schema(summary="Delete field definition")
    def destroy(self, request, id=None):
        """Delete a field definition."""
        service = FieldService(user=request.user)
        service.delete_field_definition(id)

        return Response({
            'status': 'success',
            'message': 'Field definition deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Reorder field definitions",
        request=FieldReorderSerializer,
        responses={200: OpenApiResponse(description='Fields reordered successfully')}
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder field definitions."""
        serializer = FieldReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        service.reorder_fields(serializer.validated_data['field_order'])

        return Response({
            'status': 'success',
            'message': 'Fields reordered successfully'
        })

    @extend_schema(
        summary="Get available field types",
        responses={200: FieldTypeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available field types."""
        types_data = [
            {'value': choice[0], 'label': choice[1]}
            for choice in FieldType.choices
        ]

        serializer = FieldTypeSerializer(types_data, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Validate field value",
        request=FieldValidationSerializer,
        responses={200: OpenApiResponse(description='Value is valid')}
    )
    @action(detail=True, methods=['post'])
    def validate(self, request, id=None):
        """Validate a value against this field definition."""
        serializer = FieldValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)

        try:
            service.validate_field_value(
                id,
                serializer.validated_data['value']
            )
            return Response({
                'status': 'success',
                'data': {'is_valid': True},
                'message': 'Value is valid'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'data': {'is_valid': False},
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get field render configuration",
        responses={200: FieldRenderConfigSerializer}
    )
    @action(detail=True, methods=['get'])
    def render_config(self, request, id=None):
        """Get rendering configuration for frontend."""
        service = FieldService(user=request.user)
        field = service.get_field_definition(id)

        render_config = field.get_render_config()

        return Response({
            'status': 'success',
            'data': render_config
        })


class FieldContextViewSet(viewsets.ModelViewSet):
    """
    ViewSet for field contexts.

    Endpoints:
    - GET /field-contexts/ - List all field contexts
    - POST /field-contexts/ - Create field context
    - GET /field-contexts/{id}/ - Get field context
    - PUT /field-contexts/{id}/ - Update field context
    - PATCH /field-contexts/{id}/ - Partial update field context
    - DELETE /field-contexts/{id}/ - Delete field context
    - POST /field-contexts/bulk-create/ - Bulk create contexts
    - POST /field-contexts/copy/ - Copy contexts between projects
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = FieldContextSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get field contexts for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return FieldContext.objects.none()

        return FieldContext.objects.filter(
            field__organization=self.request.user.current_organization
        ).select_related('field', 'project', 'issue_type').order_by('field', 'position')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return FieldContextCreateSerializer
        return FieldContextSerializer

    @extend_schema(
        summary="List field contexts",
        parameters=[
            OpenApiParameter('field_id', str, description='Filter by field'),
            OpenApiParameter('project_id', str, description='Filter by project'),
            OpenApiParameter('issue_type_id', str, description='Filter by issue type'),
        ]
    )
    def list(self, request):
        """List field contexts with optional filters."""
        service = FieldService(user=request.user)

        # Get filter parameters
        field_id = request.query_params.get('field_id')
        project_id = request.query_params.get('project_id')
        issue_type_id = request.query_params.get('issue_type_id')

        # Get contexts
        contexts = service.list_field_contexts(
            field_id=field_id,
            project_id=project_id,
            issue_type_id=issue_type_id
        )

        serializer = self.get_serializer(contexts, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create field context")
    def create(self, request):
        """Create a new field context."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        context = service.create_field_context(serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldContextSerializer(context).data,
            'message': 'Field context created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get field context")
    def retrieve(self, request, id=None):
        """Get a specific field context."""
        service = FieldService(user=request.user)
        context = service.get_field_context(id)

        serializer = self.get_serializer(context)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update field context")
    def update(self, request, id=None):
        """Update a field context."""
        service = FieldService(user=request.user)
        context = service.get_field_context(id)

        serializer = self.get_serializer(context, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_context = service.update_field_context(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldContextSerializer(updated_context).data,
            'message': 'Field context updated successfully'
        })

    @extend_schema(summary="Partially update field context")
    def partial_update(self, request, id=None):
        """Partially update a field context."""
        service = FieldService(user=request.user)
        context = service.get_field_context(id)

        serializer = self.get_serializer(context, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_context = service.update_field_context(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldContextSerializer(updated_context).data,
            'message': 'Field context updated successfully'
        })

    @extend_schema(summary="Delete field context")
    def destroy(self, request, id=None):
        """Delete a field context."""
        service = FieldService(user=request.user)
        service.delete_field_context(id)

        return Response({
            'status': 'success',
            'message': 'Field context deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Bulk create field contexts",
        request=BulkFieldContextCreateSerializer,
        responses={201: FieldContextSerializer(many=True)}
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create field contexts for a field."""
        serializer = BulkFieldContextCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        contexts = service.bulk_create_field_contexts(
            serializer.validated_data['field_id'],
            serializer.validated_data['contexts']
        )

        return Response({
            'status': 'success',
            'data': FieldContextSerializer(contexts, many=True).data,
            'message': f'Created {len(contexts)} field contexts'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Copy field contexts between projects",
        request=CopyFieldContextsSerializer,
        responses={201: FieldContextSerializer(many=True)}
    )
    @action(detail=False, methods=['post'])
    def copy(self, request):
        """Copy field contexts from one project to another."""
        serializer = CopyFieldContextsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        contexts = service.copy_field_contexts_to_project(
            serializer.validated_data['source_project_id'],
            serializer.validated_data['target_project_id']
        )

        return Response({
            'status': 'success',
            'data': FieldContextSerializer(contexts, many=True).data,
            'message': f'Copied {len(contexts)} field contexts'
        }, status=status.HTTP_201_CREATED)


class FieldSchemeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for field schemes.

    Endpoints:
    - GET /field-schemes/ - List all field schemes
    - POST /field-schemes/ - Create field scheme
    - GET /field-schemes/{id}/ - Get field scheme
    - PUT /field-schemes/{id}/ - Update field scheme
    - PATCH /field-schemes/{id}/ - Partial update field scheme
    - DELETE /field-schemes/{id}/ - Delete field scheme
    - GET /field-schemes/by-project/{project_id}/ - Get scheme by project
    - POST /field-schemes/{id}/set-field-config/ - Set field config
    - GET /field-schemes/{id}/get-field-config/ - Get field config
    """

    permission_classes = [IsAuthenticated, IsOrganizationMember]
    serializer_class = FieldSchemeSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Get field schemes for current organization."""
        if not hasattr(self.request.user, 'current_organization'):
            return FieldScheme.objects.none()

        return FieldScheme.objects.filter(
            project__organization=self.request.user.current_organization
        ).select_related('project').order_by('project__name')

    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'create':
            return FieldSchemeCreateSerializer
        return FieldSchemeSerializer

    @extend_schema(summary="List field schemes")
    def list(self, request):
        """List field schemes."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Create field scheme")
    def create(self, request):
        """Create a new field scheme."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        scheme = service.create_field_scheme(serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldSchemeSerializer(scheme).data,
            'message': 'Field scheme created successfully'
        }, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Get field scheme")
    def retrieve(self, request, id=None):
        """Get a specific field scheme."""
        service = FieldService(user=request.user)
        scheme = service.get_field_scheme(id)

        serializer = self.get_serializer(scheme)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(summary="Update field scheme")
    def update(self, request, id=None):
        """Update a field scheme."""
        service = FieldService(user=request.user)
        scheme = service.get_field_scheme(id)

        serializer = self.get_serializer(scheme, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_scheme = service.update_field_scheme(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldSchemeSerializer(updated_scheme).data,
            'message': 'Field scheme updated successfully'
        })

    @extend_schema(summary="Partially update field scheme")
    def partial_update(self, request, id=None):
        """Partially update a field scheme."""
        service = FieldService(user=request.user)
        scheme = service.get_field_scheme(id)

        serializer = self.get_serializer(scheme, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_scheme = service.update_field_scheme(id, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': FieldSchemeSerializer(updated_scheme).data,
            'message': 'Field scheme updated successfully'
        })

    @extend_schema(summary="Delete field scheme")
    def destroy(self, request, id=None):
        """Delete a field scheme."""
        service = FieldService(user=request.user)
        service.delete_field_scheme(id)

        return Response({
            'status': 'success',
            'message': 'Field scheme deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Get field scheme by project",
        parameters=[OpenApiParameter('project_id', str, location=OpenApiParameter.PATH)]
    )
    @action(detail=False, methods=['get'], url_path='by-project/(?P<project_id>[^/.]+)')
    def by_project(self, request, project_id=None):
        """Get field scheme for a specific project."""
        service = FieldService(user=request.user)
        scheme = service.get_field_scheme_for_project(project_id)

        if not scheme:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Field scheme not found for this project'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(scheme)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    @extend_schema(
        summary="Set field configuration in scheme",
        request=FieldConfigUpdateSerializer,
        responses={200: FieldSchemeSerializer}
    )
    @action(detail=True, methods=['post'])
    def set_field_config(self, request, id=None):
        """Set configuration for a specific field in this scheme."""
        serializer = FieldConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FieldService(user=request.user)
        scheme = service.set_field_config_for_scheme(
            id,
            serializer.validated_data['field_id'],
            serializer.validated_data['config']
        )

        return Response({
            'status': 'success',
            'data': FieldSchemeSerializer(scheme).data,
            'message': 'Field configuration updated'
        })

    @extend_schema(
        summary="Get field configuration from scheme",
        parameters=[OpenApiParameter('field_id', str, description='Field UUID')]
    )
    @action(detail=True, methods=['get'])
    def get_field_config(self, request, id=None):
        """Get configuration for a specific field in this scheme."""
        field_id = request.query_params.get('field_id')
        if not field_id:
            return Response({
                'status': 'error',
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'field_id parameter is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        service = FieldService(user=request.user)
        config = service.get_field_config_for_scheme(id, field_id)

        return Response({
            'status': 'success',
            'data': config
        })
