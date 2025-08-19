from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager that uses email as the unique identifier.
    """
    
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 'CUSTOMER')
        return self._create_user(email, password, **extra_fields)

    def create_staff_user(self, email, password=None, **extra_fields):
        """
        Create and save a staff user with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 'STAFF')
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Staff user must have is_staff=True.')
            
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('email_verified_at', timezone.now())

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        """
        Allow authentication using case-insensitive email.
        """
        return self.get(email__iexact=username)

    def active_users(self):
        """
        Return only active users.
        """
        return self.filter(is_active=True)

    def verified_users(self):
        """
        Return only verified users.
        """
        return self.filter(is_verified=True, is_active=True)

    def customers(self):
        """
        Return only customer users.
        """
        return self.filter(user_type='CUSTOMER', is_active=True)

    def staff_members(self):
        """
        Return only staff users.
        """
        return self.filter(
            user_type__in=['STAFF', 'MANAGER', 'ADMIN'],
            is_active=True
        )

    def vendors(self):
        """
        Return only vendor users.
        """
        return self.filter(user_type='VENDOR', is_active=True)