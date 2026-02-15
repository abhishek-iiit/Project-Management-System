"""
Base models for the application.

Following CLAUDE.md best practices:
- All models inherit from TimestampedModel for created_at/updated_at
- Use SoftDeleteModel for soft deletion support
- Use UUIDModel for UUID primary keys
"""

import uuid
from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """
    Abstract base model with timestamp fields.

    All models should inherit from this to automatically track
    creation and modification times.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """Override save to ensure updated_at is set."""
        if not self.pk:
            # New instance
            if not self.created_at:
                self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class SoftDeleteQuerySet(models.QuerySet):
    """Custom QuerySet for soft delete functionality."""

    def active(self):
        """Return only non-deleted records."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Return only deleted records."""
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft delete all records in queryset."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently delete all records in queryset."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Custom manager for soft delete models."""

    def get_queryset(self):
        """Return only non-deleted records by default."""
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self):
        """Return all records including deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Return only deleted records."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class SoftDeleteModel(models.Model):
    """
    Abstract base model with soft delete functionality.

    Instead of permanently deleting records, sets deleted_at timestamp.
    Use .hard_delete() to permanently delete.
    """

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when the record was soft deleted"
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access all records including deleted

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the record."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self):
        """Permanently delete the record."""
        super().delete()

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    @property
    def is_deleted(self):
        """Check if record is soft deleted."""
        return self.deleted_at is not None


class UUIDModel(models.Model):
    """
    Abstract base model with UUID primary key.

    All models should use UUID for primary keys for:
    - Security (no sequential IDs)
    - Distributed system compatibility
    - Better for APIs
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID4)"
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel, SoftDeleteModel):
    """
    Complete base model combining UUID, timestamps, and soft delete.

    This is the recommended base for all application models.

    Example:
        class Product(BaseModel):
            name = models.CharField(max_length=255)
            # Automatically gets: id (UUID), created_at, updated_at, deleted_at
    """

    class Meta:
        abstract = True

    def __str__(self):
        """Default string representation."""
        return f"{self.__class__.__name__}({self.id})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<{self.__class__.__name__} id={self.id}>"
