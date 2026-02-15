"""
Factory Boy factories for Organization models.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from apps.organizations.models import Organization, OrganizationMember
from .user_factories import UserFactory

fake = Faker()


class OrganizationFactory(DjangoModelFactory):
    """Factory for creating Organization instances."""

    class Meta:
        model = Organization
        django_get_or_create = ('slug',)

    name = factory.LazyAttribute(lambda _: fake.company())
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-')[:50])
    description = factory.LazyAttribute(lambda _: fake.catch_phrase())
    is_active = True

    @factory.post_generation
    def members(obj, create, extracted, **kwargs):
        """Add members after organization creation."""
        if not create:
            return

        if extracted:
            # A list of members was passed in
            for user in extracted:
                OrganizationMemberFactory(organization=obj, user=user)


class OrganizationMemberFactory(DjangoModelFactory):
    """Factory for creating OrganizationMember instances."""

    class Meta:
        model = OrganizationMember

    organization = factory.SubFactory(OrganizationFactory)
    user = factory.SubFactory(UserFactory)
    role = 'member'
    is_active = True
