from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'sales'

# API Router
router = DefaultRouter()
router.register(r'sales', views.SaleViewSet)
router.register(r'payments', views.SalePaymentViewSet)
router.register(r'refunds', views.RefundViewSet)

urlpatterns = [
    # Dashboard
    path('', views.SalesDashboardView.as_view(), name='dashboard'),
    
    # POS System
    path('pos/', views.POSView.as_view(), name='pos'),
    path('pos/quick-sale/', views.QuickSaleView.as_view(), name='quick_sale'),
    
    # Sale Management URLs
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/create/', views.SaleCreateView.as_view(), name='sale_create'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('sales/<int:pk>/edit/', views.SaleEditView.as_view(), name='sale_edit'),
    path('sales/<int:pk>/delete/', views.SaleDeleteView.as_view(), name='sale_delete'),
    path('sales/<int:pk>/receipt/', views.SaleReceiptView.as_view(), name='sale_receipt'),
    path('sales/<int:pk>/invoice/', views.SaleInvoiceView.as_view(), name='sale_invoice'),
    path('sales/<int:pk>/duplicate/', views.SaleDuplicateView.as_view(), name='sale_duplicate'),
    path('sales/<int:pk>/refund/', views.SaleRefundView.as_view(), name='sale_refund'),
    path('sales/bulk-action/', views.SaleBulkActionView.as_view(), name='sale_bulk_action'),
    path('sales/export/', views.SaleExportView.as_view(), name='sale_export'),
    
    # Payment URLs
    path('payments/', views.SalePaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.SalePaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/', views.SalePaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<int:pk>/edit/', views.SalePaymentEditView.as_view(), name='payment_edit'),
    path('payments/<int:pk>/receipt/', views.PaymentReceiptView.as_view(), name='payment_receipt'),
    
    # Refund Management URLs
    path('refunds/', views.RefundListView.as_view(), name='refund_list'),
    path('refunds/create/', views.RefundCreateView.as_view(), name='refund_create'),
    path('refunds/<int:pk>/', views.RefundDetailView.as_view(), name='refund_detail'),
    path('refunds/<int:pk>/edit/', views.RefundEditView.as_view(), name='refund_edit'),
    path('refunds/<int:pk>/process/', views.RefundProcessView.as_view(), name='refund_process'),
    path('refunds/<int:pk>/receipt/', views.RefundReceiptView.as_view(), name='refund_receipt'),
    
    # Reports
    path('reports/', views.SalesReportsView.as_view(), name='reports'),
    path('reports/daily/', views.DailySalesReportView.as_view(), name='daily_report'),
    path('reports/monthly/', views.MonthlySalesReportView.as_view(), name='monthly_report'),
    path('reports/yearly/', views.YearlySalesReportView.as_view(), name='yearly_report'),
    path('reports/product-wise/', views.ProductWiseSalesReportView.as_view(), name='product_wise_report'),
    path('reports/customer-wise/', views.CustomerWiseSalesReportView.as_view(), name='customer_wise_report'),
    path('reports/staff-wise/', views.StaffWiseSalesReportView.as_view(), name='staff_wise_report'),
    path('reports/payment-method/', views.PaymentMethodReportView.as_view(), name='payment_method_report'),
    
    # Analytics
    path('analytics/', views.SalesAnalyticsView.as_view(), name='analytics'),
    path('analytics/trends/', views.SalesTrendsView.as_view(), name='sales_trends'),
    path('analytics/performance/', views.SalesPerformanceView.as_view(), name='sales_performance'),
    
    # API URLs
    path('api/', include(router.urls)),
    path('api/dashboard/', views.SalesDashboardAPIView.as_view(), name='api_dashboard'),
    path('api/stats/', views.SalesStatsAPIView.as_view(), name='api_stats'),
    path('api/pos/cart/', views.POSCartAPIView.as_view(), name='api_pos_cart'),
    path('api/pos/checkout/', views.POSCheckoutAPIView.as_view(), name='api_pos_checkout'),
    path('api/pos/products/', views.POSProductSearchAPIView.as_view(), name='api_pos_products'),
    path('api/pos/customers/', views.POSCustomerSearchAPIView.as_view(), name='api_pos_customers'),
    path('api/sales/<int:pk>/items/', views.SaleItemsAPIView.as_view(), name='api_sale_items'),
    path('api/sales/<int:pk>/payments/', views.SalePaymentsAPIView.as_view(), name='api_sale_payments'),
    path('api/recent-sales/', views.RecentSalesAPIView.as_view(), name='api_recent_sales'),
    path('api/top-products/', views.TopProductsAPIView.as_view(), name='api_top_products'),
    path('api/sales-trends/', views.SalesTrendsAPIView.as_view(), name='api_sales_trends'),
    
    # AJAX URLs
    path('ajax/sale-search/', views.SaleSearchView.as_view(), name='ajax_sale_search'),
    path('ajax/product-search/', views.SalesProductSearchView.as_view(), name='ajax_product_search'),
    path('ajax/customer-search/', views.SalesCustomerSearchView.as_view(), name='ajax_customer_search'),
    path('ajax/sale-details/<int:pk>/', views.SaleDetailsAjaxView.as_view(), name='ajax_sale_details'),
    path('ajax/calculate-total/', views.CalculateSaleTotalView.as_view(), name='ajax_calculate_total'),
    path('ajax/apply-discount/', views.ApplyDiscountView.as_view(), name='ajax_apply_discount'),
    path('ajax/quick-customer/', views.QuickCustomerCreateView.as_view(), name='ajax_quick_customer'),
    path('ajax/hold-sale/', views.HoldSaleView.as_view(), name='ajax_hold_sale'),
    path('ajax/retrieve-sale/', views.RetrieveSaleView.as_view(), name='ajax_retrieve_sale'),
    path('ajax/barcode-scan/', views.BarcodeScanView.as_view(), name='ajax_barcode_scan'),
    path('ajax/price-check/', views.PriceCheckView.as_view(), name='ajax_price_check'),
    
    # Print URLs
    path('print/receipt/<int:pk>/', views.PrintReceiptView.as_view(), name='print_receipt'),
    path('print/invoice/<int:pk>/', views.PrintInvoiceView.as_view(), name='print_invoice'),
    path('print/daily-report/', views.PrintDailyReportView.as_view(), name='print_daily_report'),
]