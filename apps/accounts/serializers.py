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


# //////////////////////////////////////////////////
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import UserProfile, Role, Permission

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for permissions"""
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for roles"""
    
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'permissions', 'permission_ids',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = Role.objects.create(**validated_data)
        
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids, is_active=True)
            role.permissions.set(permissions)
        
        return role

    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids, is_active=True)
            instance.permissions.set(permissions)
        
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'entity', 'phone_number', 'date_of_birth', 'avatar',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'employee_id', 'department', 'position', 'hire_date', 'salary',
            'role', 'role_id', 'is_active', 'last_login_ip', 'login_attempts',
            'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_login_ip', 'login_attempts']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def update(self, instance, validated_data):
        role_id = validated_data.pop('role_id', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if role_id is not None:
            try:
                role = Role.objects.get(id=role_id, is_active=True)
                instance.role = role
                instance.save()
            except Role.DoesNotExist:
                pass
        
        return instance


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    profile = UserProfileSerializer(source='userprofile', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'password',
            'confirm_password', 'is_staff', 'is_active', 'date_joined', 'last_login',
            'profile', 'full_name'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError("Passwords do not match.")
        
        if password:
            try:
                validate_password(password)
            except DjangoValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    entity = serializers.ChoiceField(choices=[('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')])
    phone_number = serializers.CharField(max_length=15)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password',
            'confirm_password', 'entity', 'phone_number'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')
        
        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        
        return attrs

    def create(self, validated_data):
        # Extract profile data
        entity = validated_data.pop('entity')
        phone_number = validated_data.pop('phone_number')
        validated_data.pop('confirm_password')
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            entity=entity,
            phone_number=phone_number
        )
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Allow login with email or username
            if '@' in username:
                try:
                    user = User.objects.get(email=username)
                    username = user.username
                except User.DoesNotExist:
                    raise serializers.ValidationError("Invalid credentials.")
            
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError("Invalid credentials.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            attrs['user'] = user
        else:
            raise serializers.ValidationError("Must include username and password.")
        
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError("New passwords do not match.")
        
        try:
            validate_password(new_password, self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("No active user with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()
    token = serializers.CharField()
    uid = serializers.CharField()

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")
        
        try:
            validate_password(new_password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    """Simplified serializer for user list views"""
    
    profile = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'date_joined', 'profile', 'full_name'
        ]

    def get_profile(self, obj):
        try:
            profile = obj.userprofile
            return {
                'entity': profile.entity,
                'phone_number': profile.phone_number,
                'department': profile.department,
                'position': profile.position,
                'role': profile.role.name if profile.role else None
            }
        except UserProfile.DoesNotExist:
            return None

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField()
    staff_users = serializers.IntegerField()
    mpshoes_users = serializers.IntegerField()
    mpfootwear_users = serializers.IntegerField()
    recent_logins = serializers.IntegerField()