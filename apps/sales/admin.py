from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from .models import Sale, SaleItem, SalePayment, Refund, RefundItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('line_total',)
    fields = ('product_variant', 'quantity', 'unit_price', 'discount_amount', 'tax_amount', 'line_total')


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('payment_method', 'amount', 'reference_number', 'status', 'created_at')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'customer_info', 'sale_date', 'total_amount', 'payment_status', 'status', 'sale_type', 'created_by')
    list_filter = ('status', 'payment_status', 'sale_type', 'entity', 'sale_date', 'created_at')
    search_fields = ('sale_number', 'customer_name', 'customer_phone', 'customer_email')
    readonly_fields = ('sale_number', 'total_items', 'subtotal', 'total_tax', 'total_discount', 'total_amount', 
                      'paid_amount', 'due_amount', 'created_at', 'updated_at')
    inlines = [SaleItemInline, SalePaymentInline]
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'entity', 'sale_date', 'sale_type', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer', 'customer_name', 'customer_phone', 'customer_email')
        }),
        ('Financial Summary', {
            'fields': ('subtotal', 'total_discount', 'total_tax', 'total_amount', 'paid_amount', 'due_amount', 'payment_status')
        }),
        ('Additional Details', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def customer_info(self, obj):
        if obj.customer:
            return f"{obj.customer.get_full_name()}"
        return f"{obj.customer_name} ({obj.customer_phone})"
    customer_info.short_description = 'Customer'

    def total_items(self, obj):
        return obj.items.aggregate(total=Sum('quantity'))['total'] or 0
    total_items.short_description = 'Items'

    def save_model(self, request, obj, form, change):
        if not obj.sale_number:
            # Generate sale number
            prefix = 'MPS' if obj.entity == 'mpshoes' else 'MPF'
            last_sale = Sale.objects.filter(entity=obj.entity).order_by('-id').first()
            next_id = 1 if not last_sale else last_sale.id + 1
            obj.sale_number = f"{prefix}S{next_id:08d}"
        
        if not obj.created_by_id:
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'created_by')


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product_variant', 'quantity', 'unit_price', 'discount_amount', 'tax_amount', 'line_total')
    list_filter = ('sale__entity', 'sale__sale_date', 'product_variant__product__category')
    search_fields = ('sale__sale_number', 'product_variant__product__name', 'product_variant__sku')
    readonly_fields = ('line_total',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sale', 'product_variant__product')


@admin.register(SalePayment)
class SalePaymentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'payment_method', 'amount', 'status', 'payment_date', 'created_at')
    list_filter = ('payment_method', 'status', 'payment_date', 'created_at')
    search_fields = ('sale__sale_number', 'reference_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'payment_date'

    fieldsets = (
        ('Payment Information', {
            'fields': ('sale', 'payment_method', 'amount', 'payment_date', 'status')
        }),
        ('Reference Details', {
            'fields': ('reference_number', 'transaction_id', 'gateway_response')
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sale')


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0
    readonly_fields = ('refund_amount',)
    fields = ('sale_item', 'quantity', 'reason', 'refund_amount')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('refund_number', 'sale', 'refund_date', 'total_amount', 'refund_method', 'status', 'processed_by')
    list_filter = ('status', 'refund_method', 'refund_date', 'created_at')
    search_fields = ('refund_number', 'sale__sale_number', 'reason')
    readonly_fields = ('refund_number', 'total_amount', 'created_at', 'updated_at')
    inlines = [RefundItemInline]
    date_hierarchy = 'refund_date'

    fieldsets = (
        ('Refund Information', {
            'fields': ('refund_number', 'sale', 'refund_date', 'refund_method', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'processing_fee')
        }),
        ('Details', {
            'fields': ('reason', 'notes', 'processed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.refund_number:
            # Generate refund number
            entity = obj.sale.entity
            prefix = 'MPS' if entity == 'mpshoes' else 'MPF'
            last_refund = Refund.objects.filter(sale__entity=entity).order_by('-id').first()
            next_id = 1 if not last_refund else last_refund.id + 1
            obj.refund_number = f"{prefix}R{next_id:06d}"
        
        if not obj.processed_by_id:
            obj.processed_by = request.user
        
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sale', 'processed_by')


@admin.register(RefundItem)
class RefundItemAdmin(admin.ModelAdmin):
    list_display = ('refund', 'sale_item', 'quantity', 'reason', 'refund_amount')
    list_filter = ('reason', 'refund__refund_date')
    search_fields = ('refund__refund_number', 'sale_item__product_variant__product__name')
    readonly_fields = ('refund_amount',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('refund__sale', 'sale_item__product_variant__product')


# Custom admin actions
def mark_as_completed(modeladmin, request, queryset):
    queryset.update(status='completed')
mark_as_completed.short_description = "Mark selected sales as completed"

def mark_as_cancelled(modeladmin, request, queryset):
    queryset.update(status='cancelled')
mark_as_cancelled.short_description = "Mark selected sales as cancelled"

def mark_payment_completed(modeladmin, request, queryset):
    queryset.update(payment_status='paid')
mark_payment_completed.short_description = "Mark payment as completed"

SaleAdmin.actions = [mark_as_completed, mark_as_cancelled, mark_payment_completed]