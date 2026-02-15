"""
URL configuration for issues app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.issues.views import (
    IssueViewSet,
    IssueTypeViewSet,
    PriorityViewSet,
    LabelViewSet,
    CommentViewSet,
    IssueLinkTypeViewSet,
)

app_name = 'issues'

router = DefaultRouter()
router.register(r'issues', IssueViewSet, basename='issue')
router.register(r'issue-types', IssueTypeViewSet, basename='issue-type')
router.register(r'priorities', PriorityViewSet, basename='priority')
router.register(r'labels', LabelViewSet, basename='label')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'link-types', IssueLinkTypeViewSet, basename='link-type')

urlpatterns = [
    path('', include(router.urls)),
]
