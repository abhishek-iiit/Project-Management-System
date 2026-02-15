"""
Factory Boy factories for Project models.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from apps.projects.models import Project, ProjectMember
from .organization_factories import OrganizationFactory
from .user_factories import UserFactory

fake = Faker()


class ProjectFactory(DjangoModelFactory):
    """Factory for creating Project instances."""

    class Meta:
        model = Project
        django_get_or_create = ('key',)

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.LazyAttribute(lambda _: f'{fake.catch_phrase()} Project')
    key = factory.LazyAttribute(lambda _: fake.unique.lexify(text='????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_active = True

    @factory.post_generation
    def members(obj, create, extracted, **kwargs):
        """Add members after project creation."""
        if not create:
            return

        if extracted:
            # A list of members was passed in
            for user in extracted:
                ProjectMemberFactory(project=obj, user=user)


class ProjectMemberFactory(DjangoModelFactory):
    """Factory for creating ProjectMember instances."""

    class Meta:
        model = ProjectMember

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = 'developer'
    is_active = True
