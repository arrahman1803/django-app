from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Vendor, VendorBill, VendorBillItem, VendorPayment


class VendorBillItemInline(admin.TabularInline):
    model = VendorBillItem
    extra = 0
    readonly_fields = ('total_amount',)
    fields = ('product', 'quantity', 'unit_price', 'discount', 'tax_rate', 'total_amount')


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor_code', 'entity', 'contact_person', 'phone', 'email', 'credit_limit', 'status', 'created_at')
    list_filter = ('entity', 'status', 'vendor_type', 'payment_terms', 'created_at')
    search_fields = ('name', 'vendor_code', 'contact_person', 'phone', 'email')
    readonly_fields = ('vendor_code', 'total_purchases', 'outstanding_amount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'vendor_code', 'entity', 'vendor_type', 'status')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'phone', 'email', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Business Details', {
            'fields': ('tax_number', 'registration_number', 'bank_account_number', 'bank_name', 'bank_branch')
        }),
        ('Financial Information', {
            'fields': ('credit_limit', 'payment_terms', 'total_purchases', 'outstanding_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.vendor_code:
            # Generate vendor code based on entity
            prefix = 'MPS' if obj.entity == 'mpshoes' else 'MPF'
            last_vendor = Vendor.objects.filter(entity=obj.entity).order_by('-id').first()
            next_id = 1 if not last_vendor else last_vendor.id + 1
            obj.vendor_code = f"{prefix}V{next_id:04d}"
        super().save_model(request, obj, form, change)


@admin.register(VendorBill)
class VendorBillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'vendor', 'bill_date', 'due_date', 'total_amount', 'paid_amount', 'status', 'created_at')
    list_filter = ('status', 'entity', 'bill_date', 'due_date', 'created_at')
    search_fields = ('bill_number', 'vendor__name', 'reference_number')
    readonly_fields = ('bill_number', 'total_amount', 'paid_amount', 'remaining_amount', 'created_at', 'updated_at')
    inlines = [VendorBillItemInline]
    date_hierarchy = 'bill_date'
    
    fieldsets = (
        ('Bill Information', {
            'fields': ('bill_number', 'vendor', 'entity', 'bill_date', 'due_date', 'reference_number')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'paid_amount', 'remaining_amount')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.bill_number:
            # Generate bill number
            prefix = 'MPS' if obj.entity == 'mpshoes' else 'MPF'
            last_bill = VendorBill.objects.filter(entity=obj.entity).order_by('-id').first()
            next_id = 1 if not last_bill else last_bill.id + 1
            obj.bill_number = f"{prefix}B{next_id:06d}"
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('vendor')


@admin.register(VendorBillItem)
class VendorBillItemAdmin(admin.ModelAdmin):
    list_display = ('bill', 'product', 'quantity', 'unit_price', 'discount', 'tax_rate', 'total_amount')
    list_filter = ('bill__entity', 'bill__bill_date')
    search_fields = ('bill__bill_number', 'product__name', 'product__sku')
    readonly_fields = ('total_amount',)


@admin.register(VendorPayment)
class VendorPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_number', 'vendor', 'payment_date', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'entity', 'payment_date', 'created_at')
    search_fields = ('payment_number', 'vendor__name', 'reference_number')
    readonly_fields = ('payment_number', 'created_at', 'updated_at')
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_number', 'vendor', 'entity', 'payment_date', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'reference_number', 'bank_details', 'status')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.payment_number:
            # Generate payment number
            prefix = 'MPS' if obj.entity == 'mpshoes' else 'MPF'
            last_payment = VendorPayment.objects.filter(entity=obj.entity).order_by('-id').first()
            next_id = 1 if not last_payment else last_payment.id + 1
            obj.payment_number = f"{prefix}P{next_id:06d}"
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('vendor')


# Add custom admin actions
def mark_as_paid(modeladmin, request, queryset):
    queryset.update(status='paid')
mark_as_paid.short_description = "Mark selected bills as paid"

def mark_as_overdue(modeladmin, request, queryset):
    queryset.update(status='overdue')
mark_as_overdue.short_description = "Mark selected bills as overdue"

VendorBillAdmin.actions = [mark_as_paid, mark_as_overdue]