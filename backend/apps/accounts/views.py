"""
Authentication and user views.

Following CLAUDE.md best practices:
- Thin views (orchestration only)
- Delegate to services for business logic
- Proper error handling
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.accounts.serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    TokenSerializer,
    RefreshTokenSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
)
from apps.accounts.services import AuthService, UserService

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user.

    POST /api/v1/auth/register/
    {
        "email": "user@example.com",
        "username": "username",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe"
    }
    """
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Delegate to service
        auth_service = AuthService(user=None)
        user, tokens = auth_service.register_user(serializer.validated_data)

        # Return response
        return Response({
            'status': 'success',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': tokens,
            },
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)

    except ValidationError as e:
        return Response({
            'status': 'error',
            'error': {
                'code': 'REGISTRATION_FAILED',
                'message': 'Registration failed',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return JWT tokens.

    POST /api/v1/auth/login/
    {
        "email": "user@example.com",
        "password": "password123"
    }
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Get IP address
        ip_address = request.META.get('REMOTE_ADDR')

        # Delegate to service
        auth_service = AuthService(user=None)
        user, tokens = auth_service.login(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            ip_address=ip_address
        )

        return Response({
            'status': 'success',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': tokens,
            },
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

    except ValidationError as e:
        return Response({
            'status': 'error',
            'error': {
                'code': 'AUTHENTICATION_FAILED',
                'message': 'Authentication failed',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh access token using refresh token.

    POST /api/v1/auth/refresh/
    {
        "refresh": "refresh_token_here"
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Delegate to service
        auth_service = AuthService(user=None)
        tokens = auth_service.refresh_token(serializer.validated_data['refresh'])

        return Response({
            'status': 'success',
            'data': tokens,
            'message': 'Token refreshed successfully'
        }, status=status.HTTP_200_OK)

    except ValidationError as e:
        return Response({
            'status': 'error',
            'error': {
                'code': 'TOKEN_REFRESH_FAILED',
                'message': 'Token refresh failed',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user by blacklisting refresh token.

    POST /api/v1/auth/logout/
    {
        "refresh": "refresh_token_here"
    }
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Delegate to service
        auth_service = AuthService(user=request.user)
        auth_service.logout(serializer.validated_data['refresh'])

        return Response({
            'status': 'success',
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)

    except ValidationError as e:
        return Response({
            'status': 'error',
            'error': {
                'code': 'LOGOUT_FAILED',
                'message': 'Logout failed',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Get or update current user profile.

    GET /api/v1/auth/me/
    PUT /api/v1/auth/me/
    {
        "first_name": "John",
        "last_name": "Doe",
        "bio": "Software developer",
        "avatar": "https://example.com/avatar.jpg"
    }
    """
    if request.method == 'GET':
        # Return current user
        return Response({
            'status': 'success',
            'data': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        # Update profile
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        user_service = UserService(user=request.user)
        user = user_service.update_profile(request.user, serializer.validated_data)

        return Response({
            'status': 'success',
            'data': UserSerializer(user).data,
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.

    POST /api/v1/auth/change-password/
    {
        "old_password": "oldpass123",
        "new_password": "newpass123"
    }
    """
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        # Delegate to service
        auth_service = AuthService(user=request.user)
        auth_service.change_password(
            user=request.user,
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password']
        )

        return Response({
            'status': 'success',
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

    except ValidationError as e:
        return Response({
            'status': 'error',
            'error': {
                'code': 'PASSWORD_CHANGE_FAILED',
                'message': 'Password change failed',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """
    Get current user statistics.

    GET /api/v1/auth/stats/
    """
    user_service = UserService(user=request.user)
    stats = user_service.get_user_stats(request.user)

    return Response({
        'status': 'success',
        'data': stats
    }, status=status.HTTP_200_OK)
