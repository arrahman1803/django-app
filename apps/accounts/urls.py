from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

# API Router
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'profiles', views.UserProfileViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'permissions', views.PermissionViewSet)

urlpatterns = [
    # Authentication URLs
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    
    # Profile URLs
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/avatar/', views.AvatarUploadView.as_view(), name='avatar_upload'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # User Management URLs (Admin)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', views.UserEditView.as_view(), name='user_edit'),
    path('users/<int:pk>/toggle-active/', views.UserToggleActiveView.as_view(), name='user_toggle_active'),
    path('users/bulk-action/', views.UserBulkActionView.as_view(), name='user_bulk_action'),
    path('users/export/', views.UserExportView.as_view(), name='user_export'),
    
    # Role Management URLs
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/<int:pk>/edit/', views.RoleEditView.as_view(), name='role_edit'),
    path('roles/<int:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),
    
    # Permission Management URLs
    path('permissions/', views.PermissionListView.as_view(), name='permission_list'),
    path('permissions/create/', views.PermissionCreateView.as_view(), name='permission_create'),
    path('permissions/<int:pk>/edit/', views.PermissionEditView.as_view(), name='permission_edit'),
    
    # API URLs
    path('api/', include(router.urls)),
    path('api/auth/login/', views.APILoginView.as_view(), name='api_login'),
    path('api/auth/logout/', views.APILogoutView.as_view(), name='api_logout'),
    path('api/auth/register/', views.APIRegisterView.as_view(), name='api_register'),
    path('api/auth/password-change/', views.APIPasswordChangeView.as_view(), name='api_password_change'),
    path('api/auth/password-reset/', views.APIPasswordResetView.as_view(), name='api_password_reset'),
    path('api/auth/password-reset-confirm/', views.APIPasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    path('api/profile/', views.APIProfileView.as_view(), name='api_profile'),
    path('api/stats/', views.UserStatsAPIView.as_view(), name='api_user_stats'),
    
    # AJAX URLs
    path('ajax/check-username/', views.CheckUsernameView.as_view(), name='ajax_check_username'),
    path('ajax/check-email/', views.CheckEmailView.as_view(), name='ajax_check_email'),
    path('ajax/user-search/', views.UserSearchView.as_view(), name='ajax_user_search'),
]