"""
Model mixins for common functionality.
"""

from django.db import models
from django.contrib.auth import get_user_model


class AuditMixin(models.Model):
    """
    Mixin to track who created and last modified a record.

    Usage:
        class MyModel(BaseModel, AuditMixin):
            # Automatically gets created_by and updated_by fields
            pass
    """

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        help_text="User who created this record"
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        help_text="User who last updated this record"
    )

    class Meta:
        abstract = True


class OrderableMixin(models.Model):
    """
    Mixin to add ordering/ranking functionality.

    Useful for features like drag-and-drop reordering.

    Usage:
        class BoardIssue(BaseModel, OrderableMixin):
            board = models.ForeignKey(Board, on_delete=models.CASCADE)
            issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
            # Automatically gets 'order' field
    """

    order = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Order/rank for sorting (lower numbers first)"
    )

    class Meta:
        abstract = True
        ordering = ['order']

    def move_up(self):
        """Move item up in order (decrease order number)."""
        if self.order > 0:
            self.order -= 1
            self.save(update_fields=['order'])

    def move_down(self):
        """Move item down in order (increase order number)."""
        self.order += 1
        self.save(update_fields=['order'])

    def move_to(self, position):
        """Move item to specific position."""
        self.order = position
        self.save(update_fields=['order'])
