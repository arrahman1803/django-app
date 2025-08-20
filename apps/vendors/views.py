from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DetailView, DeleteView, FormView
)
from django.views import View
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Vendor, VendorBill, VendorBillItem, VendorPayment
from .forms import (
    VendorForm, VendorBillForm, VendorPaymentForm, VendorSearchForm,
    VendorBillSearchForm, VendorPaymentSearchForm, BulkVendorActionForm
)
from .serializers import (
    VendorSerializer, VendorBillSerializer, VendorPaymentSerializer,
    VendorListSerializer, VendorBillListSerializer, VendorStatsSerializer
)


# Dashboard View
class VendorDashboardView(LoginRequiredMixin, TemplateView):
    """Vendor management dashboard"""
    template_name = 'vendors/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user entity
        entity = getattr(self.request.user.userprofile, 'entity', None)
        
        context['stats'] = self.get_dashboard_stats(entity)
        context['recent_bills'] = self.get_recent_bills(entity)
        context['recent_payments'] = self.get_recent_payments(entity)
        context['overdue_bills'] = self.get_overdue_bills(entity)
        
        return context

    def get_dashboard_stats(self, entity):
        """Get dashboard statistics"""
        vendors_qs = Vendor.objects.all()
        bills_qs = VendorBill.objects.all()
        payments_qs = VendorPayment.objects.all()
        
        if entity:
            vendors_qs = vendors_qs.filter(entity=entity)
            bills_qs = bills_qs.filter(entity=entity)
            payments_qs = payments_qs.filter(entity=entity)
        
        today = timezone.now().date()
        
        return {
            'total_vendors': vendors_qs.filter(is_active=True).count(),
            'total_bills': bills_qs.count(),
            'pending_bills': bills_qs.filter(status='pending').count(),
            'overdue_bills': bills_qs.filter(status='overdue').count(),
            'total_outstanding': bills_qs.filter(status__in=['pending', 'overdue']).aggregate(
                total=Sum('remaining_amount'))['total'] or 0,
            'payments_today': payments_qs.filter(payment_date=today).aggregate(
                total=Sum('amount'))['total'] or 0,
        }

    def get_recent_bills(self, entity):
        """Get recent vendor bills"""
        bills = VendorBill.objects.select_related('vendor')
        if entity:
            bills = bills.filter(entity=entity)
        return bills.order_by('-created_at')[:5]

    def get_recent_payments(self, entity):
        """Get recent vendor payments"""
        payments = VendorPayment.objects.select_related('vendor')
        if entity:
            payments = payments.filter(entity=entity)
        return payments.order_by('-created_at')[:5]

    def get_overdue_bills(self, entity):
        """Get overdue bills"""
        bills = VendorBill.objects.select_related('vendor').filter(status='overdue')
        if entity:
            bills = bills.filter(entity=entity)
        return bills.order_by('due_date')[:10]


# Vendor Management Views
class VendorListView(LoginRequiredMixin, ListView):
    """List all vendors"""
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 20

    def get_queryset(self):
        queryset = Vendor.objects.select_related().order_by('-created_at')
        
        # Filter by user entity
        entity = getattr(self.request.user.userprofile, 'entity', None)
        if entity:
            queryset = queryset.filter(entity=entity)
        
        # Apply search filters
        search_form = VendorSearchForm(self.request.GET)
        if search_form.is_valid():
            search_query = search_form.cleaned_data.get('search_query')
            vendor_type = search_form.cleaned_data.get('vendor_type')
            status = search_form.cleaned_data.get('status')
            is_active = search_form.cleaned_data.get('is_active')
            
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(vendor_code__icontains=search_query) |
                    Q(contact_person__icontains=search_query) |
                    Q(phone__icontains=search_query) |
                    Q(email__icontains=search_query)
                )
            
            if vendor_type:
                queryset = queryset.filter(vendor_type=vendor_type)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if is_active == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active == 'false':
                queryset = queryset.filter(is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VendorSearchForm(self.request.GET)
        return context


class VendorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new vendor"""
    model = Vendor
    template_name = 'vendors/vendor_form.html'
    form_class = VendorForm
    success_url = reverse_lazy('vendors:vendor_list')
    permission_required = 'vendors.add_vendor'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity'] = getattr(self.request.user.userprofile, 'entity', None)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Vendor created successfully!')
        return super().form_valid(form)


class VendorDetailView(LoginRequiredMixin, DetailView):
    """View vendor details"""
    model = Vendor
    template_name = 'vendors/vendor_detail.html'
    context_object_name = 'vendor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = self.get_object()
        
        # Get vendor statistics
        context['total_bills'] = vendor.bills.count()
        context['pending_bills'] = vendor.bills.filter(status='pending').count()
        context['overdue_bills'] = vendor.bills.filter(status='overdue').count()
        context['total_payments'] = vendor.payments.count()
        
        # Recent bills and payments
        context['recent_bills'] = vendor.bills.order_by('-created_at')[:5]
        context['recent_payments'] = vendor.payments.order_by('-created_at')[:5]
        
        return context


class VendorEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edit vendor"""
    model = Vendor
    template_name = 'vendors/vendor_form.html'
    form_class = VendorForm
    permission_required = 'vendors.change_vendor'

    def get_success_url(self):
        return reverse('vendors:vendor_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Vendor updated successfully!')
        return super().form_valid(form)


# Vendor Bill Views
class VendorBillListView(LoginRequiredMixin, ListView):
    """List all vendor bills"""
    model = VendorBill
    template_name = 'vendors/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 20

    def get_queryset(self):
        queryset = VendorBill.objects.select_related('vendor').order_by('-created_at')
        
        # Filter by user entity
        entity = getattr(self.request.user.userprofile, 'entity', None)
        if entity:
            queryset = queryset.filter(entity=entity)
        
        # Apply search filters
        search_form = VendorBillSearchForm(self.request.GET)
        if search_form.is_valid():
            search_query = search_form.cleaned_data.get('search_query')
            vendor = search_form.cleaned_data.get('vendor')
            status = search_form.cleaned_data.get('status')
            date_from = search_form.cleaned_data.get('date_from')
            date_to = search_form.cleaned_data.get('date_to')
            
            if search_query:
                queryset = queryset.filter(
                    Q(bill_number__icontains=search_query) |
                    Q(vendor__name__icontains=search_query) |
                    Q(reference_number__icontains=search_query)
                )
            
            if vendor:
                queryset = queryset.filter(vendor=vendor)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if date_from:
                queryset = queryset.filter(bill_date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(bill_date__lte=date_to)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = VendorBillSearchForm(self.request.GET)
        return context


class VendorBillCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new vendor bill"""
    model = VendorBill
    template_name = 'vendors/bill_form.html'
    form_class = VendorBillForm
    success_url = reverse_lazy('vendors:bill_list')
    permission_required = 'vendors.add_vendorbill'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity'] = getattr(self.request.user.userprofile, 'entity', None)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Vendor bill created successfully!')
        return super().form_valid(form)


class VendorBillDetailView(LoginRequiredMixin, DetailView):
    """View vendor bill details"""
    model = VendorBill
    template_name = 'vendors/bill_detail.html'
    context_object_name = 'bill'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bill = self.get_object()
        
        # Get bill items
        context['items'] = bill.items.select_related('product').all()
        
        # Get related payments
        context['payments'] = bill.vendor.payments.filter(
            created_at__gte=bill.created_at
        ).order_by('-created_at')[:10]
        
        return context


# Vendor Payment Views
class VendorPaymentListView(LoginRequiredMixin, ListView):
    """List all vendor payments"""
    model = VendorPayment
    template_name = 'vendors/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        queryset = VendorPayment.objects.select_related('vendor').order_by('-created_at')
        
        # Filter by user entity
        entity = getattr(self.request.user.userprofile, 'entity', None)
        if entity:
            queryset = queryset.filter(entity=entity)
        
        return queryset


class VendorPaymentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new vendor payment"""
    model = VendorPayment
    template_name = 'vendors/payment_form.html'
    form_class = VendorPaymentForm
    success_url = reverse_lazy('vendors:payment_list')
    permission_required = 'vendors.add_vendorpayment'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity'] = getattr(self.request.user.userprofile, 'entity', None)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Payment recorded successfully!')
        return super().form_valid(form)


# API Views
class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for Vendor CRUD operations"""
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Vendor.objects.all()
        
        # Filter by entity
        if not self.request.user.is_superuser:
            try:
                user_entity = self.request.user.userprofile.entity
                queryset = queryset.filter(entity=user_entity)
            except:
                pass
        
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return VendorListSerializer
        return VendorSerializer

    @action(detail=True, methods=['get'])
    def bills(self, request, pk=None):
        """Get bills for a vendor"""
        vendor = self.get_object()
        bills = vendor.bills.all().order_by('-created_at')
        serializer = VendorBillListSerializer(bills, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get payments for a vendor"""
        vendor = self.get_object()
        payments = vendor.payments.all().order_by('-created_at')
        from .serializers import VendorPaymentListSerializer
        serializer = VendorPaymentListSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def outstanding(self, request, pk=None):
        """Get outstanding amount for a vendor"""
        vendor = self.get_object()
        outstanding = vendor.bills.filter(
            status__in=['pending', 'overdue']
        ).aggregate(total=Sum('remaining_amount'))['total'] or 0
        
        return Response({'outstanding_amount': outstanding})


class VendorBillViewSet(viewsets.ModelViewSet):
    """ViewSet for VendorBill CRUD operations"""
    queryset = VendorBill.objects.all()
    serializer_class = VendorBillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = VendorBill.objects.select_related('vendor')
        
        # Filter by entity
        if not self.request.user.is_superuser:
            try:
                user_entity = self.request.user.userprofile.entity
                queryset = queryset.filter(entity=user_entity)
            except:
                pass
        
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return VendorBillListSerializer
        return VendorBillSerializer

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark bill as paid"""
        bill = self.get_object()
        bill.status = 'paid'
        bill.paid_amount = bill.total_amount
        bill.remaining_amount = 0
        bill.save()
        
        return Response({'status': 'success', 'message': 'Bill marked as paid'})


class VendorPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for VendorPayment CRUD operations"""
    queryset = VendorPayment.objects.all()
    serializer_class = VendorPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = VendorPayment.objects.select_related('vendor')
        
        # Filter by entity
        if not self.request.user.is_superuser:
            try:
                user_entity = self.request.user.userprofile.entity
                queryset = queryset.filter(entity=user_entity)
            except:
                pass
        
        return queryset.order_by('-created_at')


# API Dashboard and Stats
class VendorDashboardAPIView(APIView):
    """API view for vendor dashboard data"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entity = getattr(request.user.userprofile, 'entity', None)
        
        # Get statistics
        vendors_qs = Vendor.objects.all()
        bills_qs = VendorBill.objects.all()
        payments_qs = VendorPayment.objects.all()
        
        if entity:
            vendors_qs = vendors_qs.filter(entity=entity)
            bills_qs = bills_qs.filter(entity=entity)
            payments_qs = payments_qs.filter(entity=entity)
        
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1).date()
        
        stats = {
            'total_vendors': vendors_qs.filter(is_active=True).count(),
            'active_vendors': vendors_qs.filter(is_active=True).count(),
            'total_bills': bills_qs.count(),
            'pending_bills': bills_qs.filter(status='pending').count(),
            'overdue_bills': bills_qs.filter(status='overdue').count(),
            'total_outstanding': bills_qs.filter(status__in=['pending', 'overdue']).aggregate(
                total=Sum('remaining_amount'))['total'] or 0,
            'total_payments_today': payments_qs.filter(payment_date=today).aggregate(
                total=Sum('amount'))['total'] or 0,
            'total_payments_month': payments_qs.filter(payment_date__gte=this_month).aggregate(
                total=Sum('amount'))['total'] or 0,
        }
        
        # Get recent data
        recent_bills = VendorBillListSerializer(
            bills_qs.order_by('-created_at')[:5], many=True
        ).data
        
        recent_payments = VendorPaymentListSerializer(
            payments_qs.order_by('-created_at')[:5], many=True
        ).data
        
        overdue_bills = VendorBillListSerializer(
            bills_qs.filter(status='overdue').order_by('due_date')[:10], many=True
        ).data
        
        top_vendors = VendorListSerializer(
            vendors_qs.filter(is_active=True).order_by('-total_purchases')[:5], many=True
        ).data
        
        return Response({
            'stats': stats,
            'recent_bills': recent_bills,
            'recent_payments': recent_payments,
            'overdue_bills': overdue_bills,
            'top_vendors': top_vendors
        })


class VendorStatsAPIView(APIView):
    """API view for vendor statistics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entity = getattr(request.user.userprofile, 'entity', None)
        
        vendors_qs = Vendor.objects.all()
        bills_qs = VendorBill.objects.all()
        payments_qs = VendorPayment.objects.all()
        
        if entity:
            vendors_qs = vendors_qs.filter(entity=entity)
            bills_qs = bills_qs.filter(entity=entity)
            payments_qs = payments_qs.filter(entity=entity)
        
        today = timezone.now().date()
        this_month = timezone.now().replace(day=1).date()
        
        stats = {
            'total_vendors': vendors_qs.count(),
            'active_vendors': vendors_qs.filter(is_active=True).count(),
            'total_bills': bills_qs.count(),
            'pending_bills': bills_qs.filter(status='pending').count(),
            'overdue_bills': bills_qs.filter(status='overdue').count(),
            'total_outstanding': bills_qs.filter(status__in=['pending', 'overdue']).aggregate(
                total=Sum('remaining_amount'))['total'] or 0,
            'total_payments_today': payments_qs.filter(payment_date=today).aggregate(
                total=Sum('amount'))['total'] or 0,
            'total_payments_month': payments_qs.filter(payment_date__gte=this_month).aggregate(
                total=Sum('amount'))['total'] or 0,
        }
        
        serializer = VendorStatsSerializer(stats)
        return Response(serializer.data)


# AJAX Views
class VendorSearchView(LoginRequiredMixin, View):
    """AJAX view for vendor search"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        entity = getattr(request.user.userprofile, 'entity', None)
        
        vendors = Vendor.objects.filter(is_active=True)
        
        if entity:
            vendors = vendors.filter(entity=entity)
        
        if query:
            vendors = vendors.filter(
                Q(name__icontains=query) |
                Q(vendor_code__icontains=query) |
                Q(contact_person__icontains=query)
            )
        
        vendors = vendors[:10]  # Limit results
        
        results = []
        for vendor in vendors:
            results.append({
                'id': vendor.id,
                'vendor_code': vendor.vendor_code,
                'name': vendor.name,
                'contact_person': vendor.contact_person,
                'phone': vendor.phone,
                'email': vendor.email,
                'outstanding_amount': float(vendor.outstanding_amount)
            })
        
        return JsonResponse({'vendors': results})


class VendorDetailsAjaxView(LoginRequiredMixin, View):
    """AJAX view for vendor details"""
    
    def get(self, request, pk):
        try:
            vendor = Vendor.objects.get(pk=pk, is_active=True)
            data = {
                'id': vendor.id,
                'vendor_code': vendor.vendor_code,
                'name': vendor.name,
                'contact_person': vendor.contact_person,
                'phone': vendor.phone,
                'email': vendor.email,
                'address': f"{vendor.address_line1}, {vendor.city}",
                'credit_limit': float(vendor.credit_limit),
                'outstanding_amount': float(vendor.outstanding_amount),
                'payment_terms': vendor.payment_terms,
            }
            return JsonResponse(data)
        except Vendor.DoesNotExist:
            return JsonResponse({'error': 'Vendor not found'}, status=404)


class VendorOutstandingAjaxView(LoginRequiredMixin, View):
    """AJAX view for vendor outstanding amount"""
    
    def get(self, request, pk):
        try:
            vendor = Vendor.objects.get(pk=pk)
            outstanding = vendor.bills.filter(
                status__in=['pending', 'overdue']
            ).aggregate(total=Sum('remaining_amount'))['total'] or 0
            
            return JsonResponse({
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'outstanding_amount': float(outstanding)
            })
        except Vendor.DoesNotExist:
            return JsonResponse({'error': 'Vendor not found'}, status=404)


class CalculateBillTotalView(LoginRequiredMixin, View):
    """AJAX view to calculate bill total"""
    
    def post(self, request):
        import json
        
        try:
            data = json.loads(request.body)
            subtotal = float(data.get('subtotal', 0))
            tax_amount = float(data.get('tax_amount', 0))
            discount_amount = float(data.get('discount_amount', 0))
            
            total_amount = subtotal + tax_amount - discount_amount
            
            return JsonResponse({
                'subtotal': subtotal,
                'tax_amount': tax_amount,
                'discount_amount': discount_amount,
                'total_amount': total_amount
            })
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data'}, status=400)


# Additional Views
class VendorToggleActiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Toggle vendor active status"""
    permission_required = 'vendors.change_vendor'

    def post(self, request, pk):
        vendor = get_object_or_404(Vendor, pk=pk)
        vendor.is_active = not vendor.is_active
        vendor.save()
        
        status_text = 'activated' if vendor.is_active else 'deactivated'
        messages.success(request, f'Vendor {vendor.name} has been {status_text}.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': vendor.is_active,
                'message': f'Vendor {status_text} successfully'
            })
        
        return redirect('vendors:vendor_list')


class VendorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete vendor"""
    model = Vendor
    template_name = 'vendors/vendor_confirm_delete.html'
    success_url = reverse_lazy('vendors:vendor_list')
    permission_required = 'vendors.delete_vendor'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Vendor deleted successfully!')
        return super().delete(request, *args, **kwargs)


class VendorBillMarkPaidView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Mark vendor bill as paid"""
    permission_required = 'vendors.change_vendorbill'

    def post(self, request, pk):
        bill = get_object_or_404(VendorBill, pk=pk)
        bill.status = 'paid'
        bill.paid_amount = bill.total_amount
        bill.remaining_amount = 0
        bill.save()
        
        messages.success(request, f'Bill {bill.bill_number} marked as paid.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Bill marked as paid successfully'
            })
        
        return redirect('vendors:bill_detail', pk=pk)


class VendorExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export vendors to CSV"""
    permission_required = 'vendors.view_vendor'

    def get(self, request):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vendors.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Vendor Code', 'Name', 'Entity', 'Contact Person', 'Phone', 'Email',
            'City', 'Credit Limit', 'Total Purchases', 'Outstanding Amount', 'Status'
        ])
        
        entity = getattr(request.user.userprofile, 'entity', None)
        vendors = Vendor.objects.all()
        if entity:
            vendors = vendors.filter(entity=entity)
        
        for vendor in vendors:
            writer.writerow([
                vendor.vendor_code,
                vendor.name,
                vendor.entity,
                vendor.contact_person,
                vendor.phone,
                vendor.email,
                vendor.city,
                vendor.credit_limit,
                vendor.total_purchases,
                vendor.outstanding_amount,
                vendor.get_status_display()
            ])
        
        return response


# Report Views
class VendorReportsView(LoginRequiredMixin, TemplateView):
    """Vendor reports dashboard"""
    template_name = 'vendors/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity = getattr(self.request.user.userprofile, 'entity', None)
        
        # Add report data here
        context['entity'] = entity
        
        return context


class VendorAgingReportView(LoginRequiredMixin, TemplateView):
    """Vendor aging report"""
    template_name = 'vendors/aging_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity = getattr(self.request.user.userprofile, 'entity', None)
        
        bills = VendorBill.objects.filter(status__in=['pending', 'overdue'])
        if entity:
            bills = bills.filter(entity=entity)
        
        # Calculate aging buckets
        from datetime import date, timedelta
        today = date.today()
        
        aging_data = []
        for bill in bills:
            days_outstanding = (today - bill.due_date).days if bill.due_date else 0
            
            if days_outstanding <= 30:
                bucket = '0-30 days'
            elif days_outstanding <= 60:
                bucket = '31-60 days'
            elif days_outstanding <= 90:
                bucket = '61-90 days'
            else:
                bucket = '90+ days'
            
            aging_data.append({
                'bill': bill,
                'days_outstanding': days_outstanding,
                'bucket': bucket
            })
        
        context['aging_data'] = aging_data
        return context


class PaymentReportView(LoginRequiredMixin, TemplateView):
    """Payment report"""
    template_name = 'vendors/payment_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity = getattr(self.request.user.userprofile, 'entity', None)
        
        payments = VendorPayment.objects.select_related('vendor')
        if entity:
            payments = payments.filter(entity=entity)
        
        # Get date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            from datetime import datetime
            payments = payments.filter(payment_date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        
        if date_to:
            from datetime import datetime
            payments = payments.filter(payment_date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        
        context['payments'] = payments.order_by('-payment_date')
        context['total_amount'] = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        return context