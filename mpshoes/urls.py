from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication
    path('accounts/', include('allauth.urls')),
    path('api/auth/', include('apps.accounts.urls')),
    
    # Core Apps API URLs
    path('api/vendors/', include('apps.vendors.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/reports/', include('apps.reports.urls')),
    
    # E-commerce Frontend URLs
    path('', include('apps.ecommerce.urls')),
    
    # Health Check
    path('health/', TemplateView.as_view(template_name='health_check.html'), name='health_check'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar in development
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Custom error handlers
handler404 = 'apps.ecommerce.views.custom_404'
handler500 = 'apps.ecommerce.views.custom_500'