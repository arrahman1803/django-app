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