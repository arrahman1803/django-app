from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, UpdateView, DetailView, ListView, TemplateView
)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
import json

from .models import User, UserProfile, UserLoginHistory
from .serializers import (
    UserSerializer, UserProfileSerializer, UserRegistrationSerializer,
    CustomTokenObtainPairSerializer, ChangePasswordSerializer
)
from .forms import UserRegistrationForm, UserProfileForm, ChangePasswordForm
from .permissions import IsOwnerOrAdmin


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token view with login tracking.
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Track successful login
            email = request.data.get('email')
            if email:
                try:
                    user = User.objects.get(email=email)
                    UserLoginHistory.objects.create(
                        user=user,
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        status='SUCCESS'
                    )
                    # Update user login count
                    user.login_count += 1
                    user.last_login_ip = self.get_client_ip(request)
                    user.save(update_fields=['login_count', 'last_login_ip'])
                except User.DoesNotExist:
                    pass
        else:
            # Track failed login
            email = request.data.get('email')
            if email:
                UserLoginHistory.objects.create(
                    user=None,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    status='FAILED',
                    failure_reason='Invalid credentials'
                )
        
        return response

    def get_client_ip(self, request):
        """
        Get client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserRegistrationAPIView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Create user profile
        UserProfile.objects.create(user=user)
        
        # Send welcome email (implement as needed)
        # send_welcome_email.delay(user.id)


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for user profile management.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self):
        return self.request.user


class UserListAPIView(generics.ListAPIView):
    """
    API endpoint for listing users (admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filterset_fields = ['user_type', 'is_active', 'is_verified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email', 'last_login']


class ChangePasswordAPIView(generics.UpdateAPIView):
    """
    API endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            old_password = serializer.data.get('old_password')
            if not user.check_password(old_password):
                return Response(
                    {'old_password': ['Wrong password.']}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.data.get('new_password'))
            user.save()
            
            return Response({'message': 'Password updated successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Traditional Django Views for Web Interface

class UserRegistrationView(CreateView):
    """
    User registration view.
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Registration successful! Please check your email to verify your account.'
        )
        return response


class UserLoginView(TemplateView):
    """
    User login view.
    """
    template_name = 'accounts/login.html'

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            user = authenticate(request, username=email, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    
                    # Track login
                    UserLoginHistory.objects.create(
                        user=user,
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        status='SUCCESS'
                    )
                    
                    # Update user
                    user.login_count += 1
                    user.last_login_ip = self.get_client_ip(request)
                    user.save(update_fields=['login_count', 'last_login_ip'])
                    
                    messages.success(request, 'Login successful!')
                    return redirect('accounts:dashboard')
                else:
                    messages.error(request, 'Your account is inactive.')
            else:
                messages.error(request, 'Invalid email or password.')
                # Track failed login
                UserLoginHistory.objects.create(
                    user=None,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    status='FAILED',
                    failure_reason='Invalid credentials'
                )
        else:
            messages.error(request, 'Please provide both email and password.')
            
        return render(request, self.template_name)

    def get_client_ip(self, request):
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@login_required
def user_logout_view(request):
    """
    User logout view.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """
    User dashboard view.
    """
    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'user': user,
            'profile': getattr(user, 'profile', None),
            'recent_orders': self.get_recent_orders(user),
            'order_count': self.get_order_count(user),
            'total_spent': self.get_total_spent(user),
            'loyalty_points': self.get_loyalty_points(user),
            'recent_activities': self.get_recent_activities(user),
        })
        
        return context

    def get_recent_orders(self, user):
        """
        Get recent orders for the user.
        """
        if hasattr(user, 'customer_profile'):
            return user.customer_profile.orders.order_by('-order_date')[:5]
        return []

    def get_order_count(self, user):
        """
        Get total order count for the user.
        """
        if hasattr(user, 'customer_profile'):
            return user.customer_profile.orders.count()
        return 0

    def get_total_spent(self, user):
        """
        Get total amount spent by the user.
        """
        if hasattr(user, 'customer_profile'):
            return user.customer_profile.calculate_lifetime_value()
        return Decimal('0.00')

    def get_loyalty_points(self, user):
        """
        Get loyalty points for the user.
        """
        if hasattr(user, 'customer_profile') and hasattr(user.customer_profile, 'loyalty_account'):
            return user.customer_profile.loyalty_account.points_balance
        return 0

    def get_recent_activities(self, user):
        """
        Get recent user activities.
        """
        activities = []
        
        if hasattr(user, 'customer_profile'):
            # Recent orders
            recent_orders = user.customer_profile.orders.order_by('-order_date')[:3]
            for order in recent_orders:
                activities.append({
                    'type': 'order',
                    'description': f'Order #{order.display_id} placed',
                    'date': order.order_date,
                    'amount': order.total_amount
                })
            
            # Recent reviews
            recent_reviews = user.customer_profile.product_reviews.order_by('-created_at')[:2]
            for review in recent_reviews:
                activities.append({
                    'type': 'review',
                    'description': f'Reviewed {review.product.name}',
                    'date': review.created_at,
                    'rating': review.rating
                })
        
        # Sort by date
        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:5]


class UserProfileView(LoginRequiredMixin, UpdateView):
    """
    User profile update view.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = getattr(self.request.user, 'profile', None)
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class ChangePasswordView(LoginRequiredMixin, TemplateView):
    """
    Change password view.
    """
    template_name = 'accounts/change_password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ChangePasswordForm()
        return context

    def post(self, request):
        form = ChangePasswordForm(request.POST)
        
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password']
            
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                
                # Update session to prevent logout
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                
                messages.success(request, 'Password changed successfully!')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Current password is incorrect.')
        
        return render(request, self.template_name, {'form': form})


# API Views for Mobile/Frontend Integration

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_api(request):
    """
    API endpoint for user registration.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        with transaction.atomic():
            user = serializer.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_api(request):
    """
    API endpoint for user logout.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_profile_api(request):
    """
    API endpoint to get user profile.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_profile_api(request):
    """
    API endpoint to update user profile.
    """
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_api(request):
    """
    API endpoint for changing password.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return Response(
                {'old_password': ['Wrong password.']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password updated successfully'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats_api(request):
    """
    API endpoint to get user statistics.
    """
    user = request.user
    stats = {}
    
    if hasattr(user, 'customer_profile'):
        customer = user.customer_profile
        stats = {
            'total_orders': customer.orders.count(),
            'completed_orders': customer.orders.filter(
                order_status__in=['COMPLETED', 'DELIVERED']
            ).count(),
            'total_spent': float(customer.calculate_lifetime_value()),
            'average_order_value': float(customer.calculate_average_order_value()),
            'last_purchase_date': customer.get_last_purchase_date(),
            'loyalty_points': 0,
            'wishlist_items': customer.wishlist_items.count(),
        }
        
        # Get loyalty points if available
        if hasattr(customer, 'loyalty_account'):
            stats['loyalty_points'] = customer.loyalty_account.points_balance
    
    elif user.user_type in ['STAFF', 'MANAGER', 'ADMIN']:
        from apps.sales.models import Sale
        # Get sales statistics for staff
        user_sales = Sale.objects.filter(sales_person=user)
        stats = {
            'total_sales': user_sales.count(),
            'total_sales_amount': float(
                user_sales.aggregate(
                    total=models.Sum('total_amount')
                )['total'] or 0
            ),
            'this_month_sales': user_sales.filter(
                sale_date__month=timezone.now().month
            ).count(),
            'average_sale_value': 0,
        }
        
        if stats['total_sales'] > 0:
            stats['average_sale_value'] = stats['total_sales_amount'] / stats['total_sales']
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_activity_api(request):
    """
    API endpoint to get user activity history.
    """
    user = request.user
    activities = []
    
    # Login history
    login_history = user.login_history.order_by('-created_at')[:5]
    for login in login_history:
        activities.append({
            'type': 'login',
            'description': f'Logged in from {login.ip_address}',
            'date': login.created_at,
            'status': login.status
        })
    
    # Order history
    if hasattr(user, 'customer_profile'):
        orders = user.customer_profile.orders.order_by('-order_date')[:5]
        for order in orders:
            activities.append({
                'type': 'order',
                'description': f'Order #{order.display_id} - ₹{order.total_amount}',
                'date': order.order_date,
                'status': order.order_status
            })
    
    # Sort by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    return Response(activities[:10])


# Utility Views

@csrf_exempt
def check_email_availability(request):
    """
    Check if email is available for registration.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email', '').lower()
        
        if email:
            exists = User.objects.filter(email=email).exists()
            return JsonResponse({
                'available': not exists,
                'message': 'Email is available' if not exists else 'Email already registered'
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password_api(request):
    """
    API endpoint for password reset request.
    """
    email = request.data.get('email')
    
    if not email:
        return Response(
            {'email': ['Email is required']}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email, is_active=True)
        # Generate and send password reset token
        # This would integrate with your email service
        # send_password_reset_email.delay(user.id)
        
        return Response({
            'message': 'Password reset instructions have been sent to your email.'
        })
    except User.DoesNotExist:
        # Don't reveal if email exists or not for security
        return Response({
            'message': 'If the email exists in our system, password reset instructions have been sent.'
        })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email_api(request):
    """
    API endpoint for email verification.
    """
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'token': ['Token is required']}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from .models import EmailVerificationToken
        verification_token = EmailVerificationToken.objects.get(
            token=token,
            is_used=False
        )
        
        if verification_token.is_valid():
            user = verification_token.user
            user.is_verified = True
            user.email_verified_at = timezone.now()
            user.save()
            
            verification_token.is_used = True
            verification_token.save()
            
            return Response({'message': 'Email verified successfully'})
        else:
            return Response(
                {'token': ['Token has expired']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except EmailVerificationToken.DoesNotExist:
        return Response(
            {'token': ['Invalid token']}, 
            status=status.HTTP_400_BAD_REQUEST
        )


# Staff Management Views

class StaffListView(LoginRequiredMixin, ListView):
    """
    Staff members list view (for managers/admins).
    """
    model = User
    template_name = 'accounts/staff_list.html'
    context_object_name = 'staff_members'
    paginate_by = 20

    def get_queryset(self):
        # Only show to managers and admins
        if not self.request.user.has_permission('view_all'):
            return User.objects.none()
            
        return User.objects.filter(
            user_type__in=['STAFF', 'MANAGER'],
            is_active=True
        ).order_by('first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_staff'] = self.get_queryset().count()
        return context


class StaffDetailView(LoginRequiredMixin, DetailView):
    """
    Staff member detail view.
    """
    model = User
    template_name = 'accounts/staff_detail.html'
    context_object_name = 'staff_member'

    def get_queryset(self):
        if not self.request.user.has_permission('view_all'):
            return User.objects.none()
            
        return User.objects.filter(
            user_type__in=['STAFF', 'MANAGER', 'ADMIN']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff_member = self.object
        
        # Get staff performance data
        from apps.sales.models import Sale
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        context.update({
            'today_sales': Sale.objects.filter(
                sales_person=staff_member,
                sale_date__date=today
            ).count(),
            'month_sales': Sale.objects.filter(
                sales_person=staff_member,
                sale_date__date__gte=this_month
            ).count(),
            'total_sales': Sale.objects.filter(
                sales_person=staff_member
            ).count(),
            'recent_sales': Sale.objects.filter(
                sales_person=staff_member
            ).order_by('-sale_date')[:5],
        })
        
        return context

# //////////////////////////////////////////////////////////////////////////////////////////////


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DetailView, DeleteView, FormView
)
from django.views import View
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from .models import UserProfile, Role, Permission
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm,
    RoleForm, PasswordResetForm, UserSearchForm, BulkUserActionForm
)
from .serializers import (
    UserSerializer, UserProfileSerializer, RoleSerializer, PermissionSerializer,
    UserRegistrationSerializer, UserLoginSerializer, PasswordChangeSerializer,
    UserListSerializer, UserStatsSerializer
)

User = get_user_model()


# Authentication Views
class LoginView(FormView):
    """User login view"""
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    success_url = reverse_lazy('accounts:dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        
        # Update login IP
        try:
            profile = user.userprofile
            profile.last_login_ip = self.get_client_ip()
            profile.login_attempts = 0
            profile.save()
        except UserProfile.DoesNotExist:
            pass
        
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
        return super().form_valid(form)

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(View):
    """User logout view"""
    
    def get(self, request):
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('accounts:login')


class RegisterView(CreateView):
    """User registration view"""
    template_name = 'accounts/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'accounts/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            profile = user.userprofile
            context['profile'] = profile
            context['entity'] = profile.entity
        except UserProfile.DoesNotExist:
            context['profile'] = None
            context['entity'] = None
        
        # Add dashboard stats based on user role
        context['quick_stats'] = self.get_quick_stats()
        context['recent_activities'] = self.get_recent_activities()
        
        return context

    def get_quick_stats(self):
        """Get quick statistics for dashboard"""
        from apps.sales.models import Sale
        from apps.inventory.models import Product
        from apps.customers.models import Customer
        from apps.vendors.models import Vendor
        from django.utils import timezone
        
        today = timezone.now().date()
        
        stats = {
            'today_sales': Sale.objects.filter(sale_date=today).count(),
            'total_products': Product.objects.filter(status='active').count(),
            'total_customers': Customer.objects.filter(is_active=True).count(),
            'total_vendors': Vendor.objects.filter(is_active=True).count(),
        }
        
        return stats

    def get_recent_activities(self):
        """Get recent activities for dashboard"""
        activities = []
        # Add logic to fetch recent activities
        return activities


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    template_name = 'accounts/profile.html'
    context_object_name = 'profile'

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile view"""
    template_name = 'accounts/profile_edit.html'
    form_class = UserProfileForm
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


# User Management Views
class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """List all users"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    permission_required = 'accounts.view_user'

    def get_queryset(self):
        queryset = User.objects.select_related('userprofile', 'userprofile__role')
        
        # Apply search filters
        search_form = UserSearchForm(self.request.GET)
        if search_form.is_valid():
            search_query = search_form.cleaned_data.get('search_query')
            entity = search_form.cleaned_data.get('entity')
            role = search_form.cleaned_data.get('role')
            is_active = search_form.cleaned_data.get('is_active')
            
            if search_query:
                queryset = queryset.filter(
                    Q(username__icontains=search_query) |
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query)
                )
            
            if entity:
                queryset = queryset.filter(userprofile__entity=entity)
            
            if role:
                queryset = queryset.filter(userprofile__role=role)
            
            if is_active == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active == 'false':
                queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = UserSearchForm(self.request.GET)
        return context


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new user"""
    model = User
    template_name = 'accounts/user_form.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('accounts:user_list')
    permission_required = 'accounts.add_user'

    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """View user details"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    permission_required = 'accounts.view_user'

    def get_queryset(self):
        return User.objects.select_related('userprofile', 'userprofile__role')


# API Views
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User CRUD operations"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.select_related('userprofile')
        
        # Filter by entity if user is not superuser
        if not self.request.user.is_superuser:
            try:
                user_entity = self.request.user.userprofile.entity
                queryset = queryset.filter(userprofile__entity=user_entity)
            except UserProfile.DoesNotExist:
                pass
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle user active status"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'status': 'success', 'is_active': user.is_active})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'mpshoes_users': User.objects.filter(userprofile__entity='mpshoes').count(),
            'mpfootwear_users': User.objects.filter(userprofile__entity='mpfootwear').count(),
            'recent_logins': User.objects.filter(last_login__date=timezone.now().date()).count(),
        }
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for UserProfile CRUD operations"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = UserProfile.objects.select_related('user', 'role')
        
        # Filter by entity if user is not superuser
        if not self.request.user.is_superuser:
            try:
                user_entity = self.request.user.userprofile.entity
                queryset = queryset.filter(entity=user_entity)
            except UserProfile.DoesNotExist:
                pass
        
        return queryset


class RoleViewSet(viewsets.ModelViewSet):
    """ViewSet for Role CRUD operations"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Role.objects.prefetch_related('permissions').filter(is_active=True)


class PermissionViewSet(viewsets.ModelViewSet):
    """ViewSet for Permission CRUD operations"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Permission.objects.filter(is_active=True)


# API Authentication Views
class APILoginView(APIView):
    """API login view"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APILogoutView(APIView):
    """API logout view"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Token.DoesNotExist:
            pass
        
        return Response({'message': 'Logout successful'})


class APIRegisterView(APIView):
    """API registration view"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIPasswordChangeView(APIView):
    """API password change view"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIProfileView(APIView):
    """API profile view"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.userprofile
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        try:
            profile = request.user.userprofile
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


class UserStatsAPIView(APIView):
    """API view for user statistics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'mpshoes_users': User.objects.filter(userprofile__entity='mpshoes').count(),
            'mpfootwear_users': User.objects.filter(userprofile__entity='mpfootwear').count(),
            'recent_logins': User.objects.filter(last_login__date=timezone.now().date()).count(),
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)


# AJAX Views
class CheckUsernameView(View):
    """AJAX view to check username availability"""
    
    def get(self, request):
        username = request.GET.get('username')
        if username:
            is_available = not User.objects.filter(username=username).exists()
            return JsonResponse({'available': is_available})
        return JsonResponse({'available': False})


class CheckEmailView(View):
    """AJAX view to check email availability"""
    
    def get(self, request):
        email = request.GET.get('email')
        user_id = request.GET.get('user_id')
        
        if email:
            queryset = User.objects.filter(email=email)
            if user_id:
                queryset = queryset.exclude(id=user_id)
            
            is_available = not queryset.exists()
            return JsonResponse({'available': is_available})
        
        return JsonResponse({'available': False})


class UserSearchView(LoginRequiredMixin, View):
    """AJAX view for user search"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        entity = request.GET.get('entity', '')
        
        users = User.objects.select_related('userprofile')
        
        if query:
            users = users.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )
        
        if entity:
            users = users.filter(userprofile__entity=entity)
        
        users = users[:10]  # Limit results
        
        results = []
        for user in users:
            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'email': user.email,
                'entity': getattr(user.userprofile, 'entity', None) if hasattr(user, 'userprofile') else None,
                'is_active': user.is_active
            })
        
        return JsonResponse({'users': results})


# Additional utility views
class PasswordResetView(FormView):
    """Password reset request view"""
    template_name = 'accounts/password_reset.html'
    form_class = PasswordResetForm
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        # Send password reset email logic here
        messages.success(self.request, 'Password reset email sent!')
        return super().form_valid(form)


class PasswordResetConfirmView(FormView):
    """Password reset confirmation view"""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        messages.success(self.request, 'Password reset successfully!')
        return super().form_valid(form)


class UserToggleActiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Toggle user active status"""
    permission_required = 'accounts.change_user'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = not user.is_active
        user.save()
        
        status_text = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.username} has been {status_text}.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': user.is_active,
                'message': f'User {status_text} successfully'
            })
        
        return redirect('accounts:user_list')


class UserBulkActionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Handle bulk user actions"""
    permission_required = 'accounts.change_user'

    def post(self, request):
        form = BulkUserActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            user_ids = form.cleaned_data['user_ids'].split(',')
            users = User.objects.filter(id__in=user_ids)
            
            if action == 'activate':
                users.update(is_active=True)
                messages.success(request, f'{users.count()} users activated.')
            
            elif action == 'deactivate':
                users.update(is_active=False)
                messages.success(request, f'{users.count()} users deactivated.')
            
            elif action == 'assign_role':
                role = form.cleaned_data['role']
                UserProfile.objects.filter(user__in=users).update(role=role)
                messages.success(request, f'Role assigned to {users.count()} users.')
            
            elif action == 'remove_role':
                UserProfile.objects.filter(user__in=users).update(role=None)
                messages.success(request, f'Role removed from {users.count()} users.')
        
        return redirect('accounts:user_list')


class AvatarUploadView(LoginRequiredMixin, View):
    """Handle avatar upload"""
    
    def post(self, request):
        if 'avatar' in request.FILES:
            try:
                profile = request.user.userprofile
                profile.avatar = request.FILES['avatar']
                profile.save()
                messages.success(request, 'Avatar updated successfully!')
            except UserProfile.DoesNotExist:
                messages.error(request, 'Profile not found.')
        
        return redirect('accounts:profile')


class UserExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export users to CSV"""
    permission_required = 'accounts.view_user'

    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Entity', 'Department', 'Position', 'Is Active', 'Date Joined'])
        
        users = User.objects.select_related('userprofile')
        for user in users:
            profile = getattr(user, 'userprofile', None)
            writer.writerow([
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                profile.entity if profile else '',
                profile.department if profile else '',
                profile.position if profile else '',
                'Yes' if user.is_active else 'No',
                user.date_joined.strftime('%Y-%m-%d')
            ])
        
        return response

