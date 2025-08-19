from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class TimeStampedModel(models.Model):
    """
    Abstract base class for models that need created and updated timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class UUIDModel(models.Model):
    """
    Abstract base class for models that use UUID as primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class BaseModel(TimeStampedModel, UUIDModel):
    """
    Abstract base class that combines TimeStamped and UUID models.
    """
    class Meta:
        abstract = True

class EntityMixin(models.Model):
    """
    Mixin for models that need to be associated with an entity (MPshoes or MPfootwear).
    """
    ENTITY_CHOICES = [
        ('MPSHOES', 'MPshoes - Men\'s Footwear'),
        ('MPFOOTWEAR', 'MPfootwear - Ladies Footwear'),
    ]
    
    entity = models.CharField(
        max_length=20,
        choices=ENTITY_CHOICES,
        default='MPSHOES',
        help_text="Business entity this record belongs to"
    )

    class Meta:
        abstract = True

class StatusMixin(models.Model):
    """
    Mixin for models that need status tracking.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('DRAFT', 'Draft'),
        ('ARCHIVED', 'Archived'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    
    class Meta:
        abstract = True

class UserTrackingMixin(models.Model):
    """
    Mixin for tracking user who created and last modified the record.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated'
    )

    class Meta:
        abstract = True

class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft deleted objects by default.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteMixin(models.Model):
    """
    Mixin for soft delete functionality.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_deleted'
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete the object.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """
        Actually delete the object from database.
        """
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """
        Restore a soft deleted object.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()

class Address(BaseModel):
    """
    Generic address model for storing addresses.
    """
    ADDRESS_TYPE_CHOICES = [
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('BILLING', 'Billing'),
        ('SHIPPING', 'Shipping'),
        ('OTHER', 'Other'),
    ]

    type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='HOME')
    street_address = models.TextField()
    apartment = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    landmark = models.CharField(max_length=200, blank=True)
    
    # For polymorphic relations
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = models.GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name_plural = 'Addresses'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['city', 'state']),
        ]

    def __str__(self):
        return f"{self.type} - {self.street_address}, {self.city}"

    @property
    def full_address(self):
        """
        Return formatted full address.
        """
        parts = [
            self.street_address,
            self.apartment,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, parts))

class PhoneNumber(BaseModel):
    """
    Generic phone number model.
    """
    PHONE_TYPE_CHOICES = [
        ('MOBILE', 'Mobile'),
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('FAX', 'Fax'),
        ('OTHER', 'Other'),
    ]

    type = models.CharField(max_length=20, choices=PHONE_TYPE_CHOICES, default='MOBILE')
    country_code = models.CharField(max_length=5, default='+91')
    number = models.CharField(max_length=15)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # For polymorphic relations
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = models.GenericForeignKey('content_type', 'object_id')

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['number']),
        ]

    def __str__(self):
        return f"{self.country_code} {self.number}"

    @property
    def formatted_number(self):
        """
        Return formatted phone number.
        """
        return f"{self.country_code} {self.number}"

class Attachment(BaseModel):
    """
    Generic attachment model for files.
    """
    ATTACHMENT_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('DOCUMENT', 'Document'),
        ('INVOICE', 'Invoice'),
        ('RECEIPT', 'Receipt'),
        ('OTHER', 'Other'),
    ]

    type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES, default='OTHER')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    file_size = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)

    # For polymorphic relations
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = models.GenericForeignKey('content_type', 'object_id')

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.title} ({self.type})"

    def save(self, *args, **kwargs):
        """
        Save file size and mime type on save.
        """
        if self.file:
            self.file_size = self.file.size
            # You can add logic to detect mime type here
        super().save(*args, **kwargs)

class AuditLog(BaseModel):
    """
    Model for tracking changes to other models.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} at {self.created_at}"