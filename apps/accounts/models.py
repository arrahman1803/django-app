from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from apps.core.models import BaseModel, Address, PhoneNumber
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom user model that uses email as the unique identifier.
    """
    USER_TYPE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
        ('CUSTOMER', 'Customer'),
        ('VENDOR', 'Vendor'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='CUSTOMER'
    )
    
    phone = models.CharField(max_length=15, blank=True, null=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    profile_picture = models.ImageField(
        upload_to='users/profiles/%Y/%m/',
        null=True,
        blank=True
    )
    profile_picture_thumbnail = ImageSpecField(
        source='profile_picture',
        processors=[ResizeToFit(150, 150)],
        format='JPEG',
        options={'quality': 85}
    )
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    
    # Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    # Marketing preferences
    marketing_emails = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    
    # Generic relations
    addresses = GenericRelation(Address, related_query_name='user')
    phone_numbers = GenericRelation(PhoneNumber, related_query_name='user')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['user_type', 'is_active']),
            models.Index(fields=['email', 'is_active']),
        ]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Send an email to this user.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def full_name(self):
        return self.get_full_name()

    @property
    def primary_address(self):
        """
        Get the primary address for the user.
        """
        return self.addresses.filter(type='HOME').first()

    @property
    def primary_phone(self):
        """
        Get the primary phone number for the user.
        """
        return self.phone_numbers.filter(is_primary=True).first()

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('accounts:profile', kwargs={'pk': self.pk})

    def has_permission(self, permission_name):
        """
        Check if user has specific permission.
        """
        if self.is_superuser:
            return True
        
        # Add custom permission logic here
        permissions_map = {
            'ADMIN': ['view_all', 'create_all', 'update_all', 'delete_all'],
            'MANAGER': ['view_all', 'create_most', 'update_most'],
            'STAFF': ['view_assigned', 'update_assigned'],
            'CUSTOMER': ['view_own', 'update_own'],
            'VENDOR': ['view_own', 'update_own'],
        }
        
        user_permissions = permissions_map.get(self.user_type, [])
        return permission_name in user_permissions


class UserProfile(BaseModel):
    """
    Extended user profile with additional information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    company = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    
    # Social media links
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    
    # Preferences
    newsletter_subscription = models.BooleanField(default=True)
    two_factor_enabled = models.BooleanField(default=False)
    
    # Privacy settings
    public_profile = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"


class UserSession(BaseModel):
    """
    Track user sessions for analytics and security.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.ip_address}"


class UserLoginHistory(BaseModel):
    """
    Track user login history for security and analytics.
    """
    LOGIN_STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('BLOCKED', 'Blocked'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=LOGIN_STATUS_CHOICES)
    failure_reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'User Login History'
        verbose_name_plural = 'User Login Histories'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.status} - {self.created_at}"


class PasswordResetToken(BaseModel):
    """
    Tokens for password reset functionality.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['token', 'is_used']),
            models.Index(fields=['user', 'is_used']),
        ]

    def __str__(self):
        return f"Reset token for {self.user.email}"

    def is_valid(self):
        """
        Check if the token is still valid.
        """
        return not self.is_used and timezone.now() < self.expires_at


class EmailVerificationToken(BaseModel):
    """
    Tokens for email verification.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['token', 'is_used']),
            models.Index(fields=['email', 'is_used']),
        ]

    def __str__(self):
        return f"Verification token for {self.email}"

    def is_valid(self):
        """
        Check if the token is still valid.
        """
        return not self.is_used and timezone.now() < self.expires_at