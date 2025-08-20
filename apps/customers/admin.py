from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Customer, CustomerAddress, CustomerGroup, LoyaltyProgram, LoyaltyTransaction, CustomerNote


class CustomerAddressInline(admin.TabularInline):
    model = CustomerAddress
    extra = 0
    fields = ('address_type', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'is_default', 'is_active')


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 0
    readonly_fields = ('created_by', 'created_at')
    fields = ('note', 'is_internal', 'created_by', 'created_at')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_code', 'full_name', 'email', 'phone', 'customer_group', 'total_orders', 'total_spent', 'loyalty_points', 'is_active')
    list_filter = ('customer_group', 'is_active', 'gender', 'entity', 'created_at', 'last_purchase_date')
    search_fields = ('customer_code', 'first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('customer_code', 'total_orders', 'total_spent', 'loyalty_points', 'last_purchase_date', 'created_at', 'updated_at')
    inlines = [CustomerAddressInline, CustomerNoteInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('customer_code', 'entity', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'gender', 'profile_picture')
        }),
        ('Customer Details', {
            'fields': ('customer_group', 'preferred_contact_method', 'language_preference')
        }),
        ('Purchase History', {
            'fields': ('total_orders', 'total_spent', 'loyalty_points', 'last_purchase_date')
        }),
        ('Marketing & Communication', {
            'fields': ('accepts_marketing', 'email_verified', 'phone_verified')
        }),
        ('Account Settings', {
            'fields': ('is_active', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

    def save_model(self, request, obj, form, change):
        if not obj.customer_code:
            # Generate customer code
            prefix = 'MPS' if obj.entity == 'mpshoes' else 'MPF'
            last_customer = Customer.objects.filter(entity=obj.entity).order_by('-id').first()
            next_id = 1 if not last_customer else last_customer.id + 1
            obj.customer_code = f"{prefix}C{next_id:06d}"
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer_group')


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ('customer', 'address_type', 'city', 'state', 'postal_code', 'is_default', 'is_active')
    list_filter = ('address_type', 'is_default', 'is_active', 'state', 'created_at')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__email', 'address_line1', 'city')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'address_type', 'contact_name', 'contact_phone')
        }),
        ('Address Details', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('delivery_instructions',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer')


@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'discount_percentage', 'member_count', 'is_active', 'created_at')
    list_filter = ('entity', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('member_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'entity', 'description')
        }),
        ('Benefits', {
            'fields': ('discount_percentage', 'special_pricing', 'free_shipping_threshold')
        }),
        ('Conditions', {
            'fields': ('minimum_orders', 'minimum_spent', 'conditions')
        }),
        ('Settings', {
            'fields': ('is_active', 'auto_assign')
        }),
        ('Statistics', {
            'fields': ('member_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def member_count(self, obj):
        return obj.customers.count()
    member_count.short_description = 'Members'


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'points_per_currency', 'currency_per_point', 'is_active', 'created_at')
    list_filter = ('entity', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('total_members', 'total_points_issued', 'total_points_redeemed', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Program Information', {
            'fields': ('name', 'entity', 'description')
        }),
        ('Point System', {
            'fields': ('points_per_currency', 'currency_per_point', 'minimum_points_redeem')
        }),
        ('Rules & Conditions', {
            'fields': ('point_expiry_days', 'max_points_per_transaction', 'terms_conditions')
        }),
        ('Statistics', {
            'fields': ('total_members', 'total_points_issued', 'total_points_redeemed')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_members(self, obj):
        return Customer.objects.filter(loyalty_points__gt=0).count()
    total_members.short_description = 'Total Members'

    def total_points_issued(self, obj):
        return LoyaltyTransaction.objects.filter(
            transaction_type='earned',
            program=obj
        ).aggregate(total=Sum('points'))['total'] or 0
    total_points_issued.short_description = 'Points Issued'

    def total_points_redeemed(self, obj):
        return LoyaltyTransaction.objects.filter(
            transaction_type='redeemed',
            program=obj
        ).aggregate(total=Sum('points'))['total'] or 0
    total_points_redeemed.short_description = 'Points Redeemed'


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'transaction_type', 'points', 'transaction_date', 'reference_type', 'reference_id', 'expiry_date')
    list_filter = ('transaction_type', 'program', 'transaction_date', 'expiry_date')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__email', 'reference_id', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('customer', 'program', 'transaction_type', 'points', 'transaction_date')
        }),
        ('Reference Details', {
            'fields': ('reference_type', 'reference_id', 'description')
        }),
        ('Expiry Information', {
            'fields': ('expiry_date', 'is_expired')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'program')


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ('customer', 'note_preview', 'is_internal', 'created_by', 'created_at')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('customer__first_name', 'customer__last_name', 'customer__email', 'note')
    readonly_fields = ('created_at',)
    
    def note_preview(self, obj):
        return obj.note[:50] + "..." if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'created_by')


# Custom admin actions
def activate_customers(modeladmin, request, queryset):
    queryset.update(is_active=True)
activate_customers.short_description = "Activate selected customers"

def deactivate_customers(modeladmin, request, queryset):
    queryset.update(is_active=False)
deactivate_customers.short_description = "Deactivate selected customers"

def enable_marketing(modeladmin, request, queryset):
    queryset.update(accepts_marketing=True)
enable_marketing.short_description = "Enable marketing for selected customers"

def disable_marketing(modeladmin, request, queryset):
    queryset.update(accepts_marketing=False)
disable_marketing.short_description = "Disable marketing for selected customers"

CustomerAdmin.actions = [activate_customers, deactivate_customers, enable_marketing, disable_marketing]