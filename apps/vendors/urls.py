from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'vendors'

# API Router
router = DefaultRouter()
router.register(r'vendors', views.VendorViewSet)
router.register(r'bills', views.VendorBillViewSet)
router.register(r'payments', views.VendorPaymentViewSet)

urlpatterns = [
    # Vendor Management URLs
    path('', views.VendorListView.as_view(), name='vendor_list'),
    path('create/', views.VendorCreateView.as_view(), name='vendor_create'),
    path('<int:pk>/', views.VendorDetailView.as_view(), name='vendor_detail'),
    path('<int:pk>/edit/', views.VendorEditView.as_view(), name='vendor_edit'),
    path('<int:pk>/delete/', views.VendorDeleteView.as_view(), name='vendor_delete'),
    path('<int:pk>/toggle-active/', views.VendorToggleActiveView.as_view(), name='vendor_toggle_active'),
    path('bulk-action/', views.VendorBulkActionView.as_view(), name='vendor_bulk_action'),
    path('export/', views.VendorExportView.as_view(), name='vendor_export'),
    path('import/', views.VendorImportView.as_view(), name='vendor_import'),
    
    # Vendor Bill URLs
    path('bills/', views.VendorBillListView.as_view(), name='bill_list'),
    path('bills/create/', views.VendorBillCreateView.as_view(), name='bill_create'),
    path('bills/<int:pk>/', views.VendorBillDetailView.as_view(), name='bill_detail'),
    path('bills/<int:pk>/edit/', views.VendorBillEditView.as_view(), name='bill_edit'),
    path('bills/<int:pk>/delete/', views.VendorBillDeleteView.as_view(), name='bill_delete'),
    path('bills/<int:pk>/print/', views.VendorBillPrintView.as_view(), name='bill_print'),
    path('bills/<int:pk>/duplicate/', views.VendorBillDuplicateView.as_view(), name='bill_duplicate'),
    path('bills/<int:pk>/mark-paid/', views.VendorBillMarkPaidView.as_view(), name='bill_mark_paid'),
    path('bills/bulk-action/', views.VendorBillBulkActionView.as_view(), name='bill_bulk_action'),
    
    # Vendor Payment URLs
    path('payments/', views.VendorPaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.VendorPaymentCreateView.as_view(), name='payment_create'),
    path('payments/<int:pk>/', views.VendorPaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<int:pk>/edit/', views.VendorPaymentEditView.as_view(), name='payment_edit'),
    path('payments/<int:pk>/delete/', views.VendorPaymentDeleteView.as_view(), name='payment_delete'),
    path('payments/<int:pk>/receipt/', views.VendorPaymentReceiptView.as_view(), name='payment_receipt'),
    path('payments/bulk-action/', views.VendorPaymentBulkActionView.as_view(), name='payment_bulk_action'),
    
    # Dashboard & Reports
    path('dashboard/', views.VendorDashboardView.as_view(), name='dashboard'),
    path('reports/', views.VendorReportsView.as_view(), name='reports'),
    path('reports/aging/', views.VendorAgingReportView.as_view(), name='aging_report'),
    path('reports/payments/', views.PaymentReportView.as_view(), name='payment_report'),
    
    # API URLs
    path('api/', include(router.urls)),
    path('api/dashboard/', views.VendorDashboardAPIView.as_view(), name='api_dashboard'),
    path('api/stats/', views.VendorStatsAPIView.as_view(), name='api_stats'),
    path('api/bills/<int:pk>/items/', views.VendorBillItemsAPIView.as_view(), name='api_bill_items'),
    path('api/vendors/<int:pk>/bills/', views.VendorBillsByVendorAPIView.as_view(), name='api_vendor_bills'),
    path('api/vendors/<int:pk>/payments/', views.VendorPaymentsByVendorAPIView.as_view(), name='api_vendor_payments'),
    path('api/vendors/<int:pk>/outstanding/', views.VendorOutstandingAPIView.as_view(), name='api_vendor_outstanding'),
    
    # AJAX URLs
    path('ajax/vendor-search/', views.VendorSearchView.as_view(), name='ajax_vendor_search'),
    path('ajax/bill-search/', views.VendorBillSearchView.as_view(), name='ajax_bill_search'),
    path('ajax/payment-search/', views.VendorPaymentSearchView.as_view(), name='ajax_payment_search'),
    path('ajax/vendor-details/<int:pk>/', views.VendorDetailsAjaxView.as_view(), name='ajax_vendor_details'),
    path('ajax/calculate-bill-total/', views.CalculateBillTotalView.as_view(), name='ajax_calculate_bill_total'),
    path('ajax/vendor-outstanding/<int:pk>/', views.VendorOutstandingAjaxView.as_view(), name='ajax_vendor_outstanding'),
]