from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'inventory'

# API Router
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'brands', views.BrandViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'variants', views.ProductVariantViewSet)
router.register(r'stock-movements', views.StockMovementViewSet)
router.register(r'stock-alerts', views.StockAlertViewSet)

urlpatterns = [
    # Dashboard
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    
    # Category Management URLs
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', views.CategoryEditView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Brand Management URLs
    path('brands/', views.BrandListView.as_view(), name='brand_list'),
    path('brands/create/', views.BrandCreateView.as_view(), name='brand_create'),
    path('brands/<int:pk>/', views.BrandDetailView.as_view(), name='brand_detail'),
    path('brands/<int:pk>/edit/', views.BrandEditView.as_view(), name='brand_edit'),
    path('brands/<int:pk>/delete/', views.BrandDeleteView.as_view(), name='brand_delete'),
    
    # Product Management URLs
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductEditView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/<int:pk>/duplicate/', views.ProductDuplicateView.as_view(), name='product_duplicate'),
    path('products/<int:pk>/variants/', views.ProductVariantListView.as_view(), name='product_variants'),
    path('products/<int:pk>/gallery/', views.ProductGalleryView.as_view(), name='product_gallery'),
    path('products/bulk-action/', views.ProductBulkActionView.as_view(), name='product_bulk_action'),
    path('products/export/', views.ProductExportView.as_view(), name='product_export'),
    path('products/import/', views.ProductImportView.as_view(), name='product_import'),
    
    # Product Variant URLs
    path('variants/', views.ProductVariantListAllView.as_view(), name='variant_list'),
    path('variants/create/', views.ProductVariantCreateView.as_view(), name='variant_create'),
    path('variants/<int:pk>/', views.ProductVariantDetailView.as_view(), name='variant_detail'),
    path('variants/<int:pk>/edit/', views.ProductVariantEditView.as_view(), name='variant_edit'),
    path('variants/<int:pk>/delete/', views.ProductVariantDeleteView.as_view(), name='variant_delete'),
    path('variants/bulk-action/', views.ProductVariantBulkActionView.as_view(), name='variant_bulk_action'),
    
    # Stock Management URLs
    path('stock/', views.StockListView.as_view(), name='stock_list'),
    path('stock/movements/', views.StockMovementListView.as_view(), name='stock_movement_list'),
    path('stock/movements/create/', views.StockMovementCreateView.as_view(), name='stock_movement_create'),
    path('stock/adjustments/', views.StockAdjustmentView.as_view(), name='stock_adjustment'),
    path('stock/quick-update/', views.QuickStockUpdateView.as_view(), name='quick_stock_update'),
    path('stock/reorder/', views.ReorderListView.as_view(), name='reorder_list'),
    path('stock/low-stock/', views.LowStockView.as_view(), name='low_stock'),
    
    # Stock Alert URLs
    path('alerts/', views.StockAlertListView.as_view(), name='alert_list'),
    path('alerts/create/', views.StockAlertCreateView.as_view(), name='alert_create'),
    path('alerts/<int:pk>/resolve/', views.StockAlertResolveView.as_view(), name='alert_resolve'),
    path('alerts/bulk-resolve/', views.StockAlertBulkResolveView.as_view(), name='alert_bulk_resolve'),
    
    # Reports
    path('reports/', views.InventoryReportsView.as_view(), name='reports'),
    path('reports/stock-valuation/', views.StockValuationReportView.as_view(), name='stock_valuation_report'),
    path('reports/movement/', views.StockMovementReportView.as_view(), name='stock_movement_report'),
    path('reports/aging/', views.InventoryAgingReportView.as_view(), name='aging_report'),
    path('reports/abc-analysis/', views.ABCAnalysisReportView.as_view(), name='abc_analysis'),
    
    # API URLs
    path('api/', include(router.urls)),
    path('api/dashboard/', views.InventoryDashboardAPIView.as_view(), name='api_dashboard'),
    path('api/stats/', views.InventoryStatsAPIView.as_view(), name='api_stats'),
    path('api/products/<int:pk>/variants/', views.ProductVariantsByProductAPIView.as_view(), name='api_product_variants'),
    path('api/variants/<int:pk>/stock-history/', views.VariantStockHistoryAPIView.as_view(), name='api_variant_stock_history'),
    path('api/low-stock/', views.LowStockAPIView.as_view(), name='api_low_stock'),
    path('api/stock-alerts/', views.StockAlertsAPIView.as_view(), name='api_stock_alerts'),
    path('api/barcode/<str:barcode>/', views.ProductByBarcodeAPIView.as_view(), name='api_product_by_barcode'),
    path('api/sku/<str:sku>/', views.ProductBySKUAPIView.as_view(), name='api_product_by_sku'),
    
    # AJAX URLs
    path('ajax/product-search/', views.ProductSearchView.as_view(), name='ajax_product_search'),
    path('ajax/variant-search/', views.VariantSearchView.as_view(), name='ajax_variant_search'),
    path('ajax/category-products/<int:pk>/', views.CategoryProductsAjaxView.as_view(), name='ajax_category_products'),
    path('ajax/brand-products/<int:pk>/', views.BrandProductsAjaxView.as_view(), name='ajax_brand_products'),
    path('ajax/product-details/<int:pk>/', views.ProductDetailsAjaxView.as_view(), name='ajax_product_details'),
    path('ajax/variant-details/<int:pk>/', views.VariantDetailsAjaxView.as_view(), name='ajax_variant_details'),
    path('ajax/check-sku/', views.CheckSKUView.as_view(), name='ajax_check_sku'),
    path('ajax/check-barcode/', views.CheckBarcodeView.as_view(), name='ajax_check_barcode'),
    path('ajax/bulk-stock-update/', views.BulkStockUpdateView.as_view(), name='ajax_bulk_stock_update'),
]