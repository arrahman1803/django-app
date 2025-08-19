from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    """
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'website', 'company', 'position',
            'facebook', 'twitter', 'linkedin', 'instagram',
            'newsletter_subscription', 'two_factor_enabled',
            'public_profile', 'show_email', 'show_phone'
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user model.
    """
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    primary_address = serializers.SerializerMethodField()
    primary_phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'phone', 'date_of_birth', 'gender',
            'profile_picture', 'is_verified', 'preferred_language',
            'timezone', 'marketing_emails', 'sms_notifications',
            'profile', 'primary_address', 'primary_phone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_type', 'is_verified', 'created_at', 'updated_at']

    def get_primary_address(self, obj):
        """
        Get primary address for the user.
        """
        address = obj.primary_address
        if address:
            return {
                'id': str(address.id),
                'type': address.type,
                'street_address': address.street_address,
                'city': address.city,
                'state': address.state,
                'postal_code': address.postal_code,
                'country': address.country
            }
        return None

    def get_primary_phone(self, obj):
        """
        Get primary phone number for the user.
        """
        phone = obj.primary_phone
        if phone:
            return {
                'id': str(phone.id),
                'type': phone.type,
                'number': phone.formatted_number,
                'is_verified': phone.is_verified
            }
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'gender', 'password', 'password_confirm',
            'marketing_emails', 'sms_notifications'
        ]

    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match.'
            })
        return attrs

    def create(self, validated_data):
        """
        Create new user.
        """
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer.
    """
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        self.fields['password'] = serializers.CharField()
        # Remove username field
        del self.fields['username']

    def validate(self, attrs):
        """
        Validate user credentials.
        """
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is inactive.')

            # Update validated data
            attrs['user'] = user
            
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        """
        Generate token with custom claims.
        """
        token = super().get_token(user)
        
        # Add custom claims
        token['user_type'] = user.user_type
        token['is_verified'] = user.is_verified
        token['full_name'] = user.get_full_name()
        
        return token


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing password.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        """
        Validate password change data.
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Password confirmation does not match.'
            })
        
        return attrs


class UserLoginHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for user login history.
    """
    class Meta:
        model = UserLoginHistory
        fields = [
            'id', 'ip_address', 'location', 'status',
            'failure_reason', 'created_at'
        ]
        read_only_fields = fields


class UserStatsSerializer(serializers.Serializer):
    """
    Serializer for user statistics.
    """
    total_orders = serializers.IntegerField(read_only=True)
    completed_orders = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    last_purchase_date = serializers.DateField(read_only=True)
    loyalty_points = serializers.IntegerField(read_only=True)
    wishlist_items = serializers.IntegerField(read_only=True)


class StaffPerformanceSerializer(serializers.Serializer):
    """
    Serializer for staff performance data.
    """
    total_sales = serializers.IntegerField(read_only=True)
    total_sales_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    this_month_sales = serializers.IntegerField(read_only=True)
    average_sale_value = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    commission_earned = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    target_achievement = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)