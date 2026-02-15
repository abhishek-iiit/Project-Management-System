"""
Factory Boy factories for Issue models.
"""

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
from faker import Faker
from apps.issues.models import Issue, Comment
from .project_factories import ProjectFactory
from .user_factories import UserFactory

fake = Faker()


class IssueFactory(DjangoModelFactory):
    """Factory for creating Issue instances."""

    class Meta:
        model = Issue

    project = factory.SubFactory(ProjectFactory)
    reporter = factory.SubFactory(UserFactory)
    assignee = factory.SubFactory(UserFactory)

    summary = factory.LazyAttribute(lambda _: fake.sentence(nb_words=6))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=500))

    issue_type = fuzzy.FuzzyChoice(['task', 'bug', 'story', 'epic'])
    priority = fuzzy.FuzzyChoice(['low', 'medium', 'high', 'critical'])
    status = fuzzy.FuzzyChoice(['to_do', 'in_progress', 'in_review', 'done'])

    @factory.post_generation
    def labels(obj, create, extracted, **kwargs):
        """Add labels after issue creation."""
        if not create:
            return

        if extracted:
            # A list of labels was passed in
            obj.labels = extracted
            obj.save()
        else:
            # Generate random labels
            obj.labels = [fake.word() for _ in range(fake.random_int(min=0, max=3))]
            obj.save()


class CommentFactory(DjangoModelFactory):
    """Factory for creating Comment instances."""

    class Meta:
        model = Comment

    issue = factory.SubFactory(IssueFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))


class BugIssueFactory(IssueFactory):
    """Factory for creating Bug-type issues."""

    issue_type = 'bug'
    priority = fuzzy.FuzzyChoice(['high', 'critical'])


class TaskIssueFactory(IssueFactory):
    """Factory for creating Task-type issues."""

    issue_type = 'task'
    priority = 'medium'


class StoryIssueFactory(IssueFactory):
    """Factory for creating Story-type issues."""

    issue_type = 'story'
    priority = 'medium'
