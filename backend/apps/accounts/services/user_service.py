"""
User service for user management.

Following CLAUDE.md best practices.
"""

from typing import Dict, Optional
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.common.services import BaseService

User = get_user_model()


class UserService(BaseService):
    """
    User management service.

    Handles:
    - User profile updates
    - User settings
    - Avatar management
    """

    @transaction.atomic
    def update_profile(self, user: User, data: Dict) -> User:
        """
        Update user profile.

        Args:
            user: User instance
            data: Profile data to update

        Returns:
            Updated User instance
        """
        allowed_fields = [
            'first_name', 'last_name', 'bio', 'avatar',
            'phone_number', 'timezone', 'language'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        user.save()
        return user

    def get_user_stats(self, user: User) -> Dict:
        """
        Get user statistics.

        Args:
            user: User instance

        Returns:
            Dict with user stats
        """
        from apps.organizations.models import OrganizationMember

        return {
            'organizations_count': user.organizations.filter(is_active=True).count(),
            'projects_count': user.get_projects().count(),
            'issues_assigned': 0,  # TODO: Implement in Phase 5
            'issues_reported': 0,  # TODO: Implement in Phase 5
        }

    def deactivate_user(self, user: User) -> User:
        """
        Deactivate user account (soft delete).

        Args:
            user: User instance

        Returns:
            Updated User instance
        """
        user.is_active = False
        user.save(update_fields=['is_active'])
        return user

    def reactivate_user(self, user: User) -> User:
        """
        Reactivate user account.

        Args:
            user: User instance

        Returns:
            Updated User instance
        """
        user.is_active = True
        user.save(update_fields=['is_active'])
        return user
