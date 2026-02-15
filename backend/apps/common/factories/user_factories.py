"""
Factory Boy factories for User models.
"""

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth import get_user_model

fake = Faker()
User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    full_name = factory.LazyAttribute(lambda _: fake.name())
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password after user creation."""
        if create:
            password = extracted or 'testpass123'
            obj.set_password(password)
            obj.save()


class SuperUserFactory(UserFactory):
    """Factory for creating superuser instances."""

    is_staff = True
    is_superuser = True
    email = factory.LazyAttribute(lambda _: f'admin.{fake.unique.user_name()}@example.com')


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive user instances."""

    is_active = False
