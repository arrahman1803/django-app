from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Category, Brand, Product, ProductVariant, StockMovement, StockAlert


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'parent', 'is_active', 'product_count', 'created_at')
    list_filter = ('entity', 'is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'entity', 'parent', 'description')
        }),
        ('SEO & Display', {
            'fields': ('meta_title', 'meta_description', 'image', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity', 'is_active', 'product_count', 'created_at')
    list_filter = ('entity', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'entity', 'description')
        }),
        ('Brand Details', {
            'fields': ('logo', 'website', 'contact_email', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ('total_stock', 'available_stock', 'reserved_stock')
    fields = ('size', 'color', 'sku', 'barcode', 'cost_price', 'selling_price', 'stock_quantity', 
              'total_stock', 'available_stock', 'reserved_stock', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'entity', 'total_stock', 'status', 'created_at')
    list_filter = ('status', 'entity', 'category', 'brand', 'is_featured', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('slug', 'total_variants', 'total_stock', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'entity', 'category', 'brand', 'description')
        }),
        ('Product Details', {
            'fields': ('material', 'gender', 'age_group', 'season', 'weight', 'dimensions')
        }),
        ('Pricing & Stock', {
            'fields': ('cost_price', 'selling_price', 'discount_price', 'tax_rate', 'total_stock')
        }),
        ('Images & Media', {
            'fields': ('primary_image', 'gallery_images')
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags', 'is_featured')
        }),
        ('Status & Settings', {
            'fields': ('status', 'track_inventory', 'allow_backorder', 'min_stock_level', 'max_stock_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_variants(self, obj):
        return obj.variants.count()
    total_variants.short_description = 'Variants'

    def total_stock(self, obj):
        return obj.variants.aggregate(total=Sum('stock_quantity'))['total'] or 0
    total_stock.short_description = 'Total Stock'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category', 'brand')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'color', 'sku', 'selling_price', 'stock_quantity', 'available_stock', 'is_active')
    list_filter = ('product__entity', 'size', 'color', 'is_active', 'created_at')
    search_fields = ('product__name', 'sku', 'barcode')
    readonly_fields = ('total_stock', 'available_stock', 'reserved_stock', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'size', 'color', 'sku', 'barcode')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'discount_price')
        }),
        ('Stock Information', {
            'fields': ('stock_quantity', 'total_stock', 'available_stock', 'reserved_stock', 
                      'reorder_level', 'max_stock_level')
        }),
        ('Physical Details', {
            'fields': ('weight', 'dimensions', 'image')
        }),
        ('Settings', {
            'fields': ('is_active', 'track_inventory', 'allow_backorder')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'movement_type', 'quantity', 'stock_after', 'date', 'reason', 'created_by')
    list_filter = ('movement_type', 'date', 'product_variant__product__entity', 'created_at')
    search_fields = ('product_variant__product__name', 'product_variant__sku', 'reason', 'reference_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Stock Movement Details', {
            'fields': ('product_variant', 'movement_type', 'quantity', 'stock_before', 'stock_after', 'date')
        }),
        ('Reference Information', {
            'fields': ('reason', 'reference_number', 'notes', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product_variant__product', 'created_by')


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'alert_type', 'current_stock', 'threshold', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'is_resolved', 'product_variant__product__entity', 'created_at')
    search_fields = ('product_variant__product__name', 'product_variant__sku')
    readonly_fields = ('created_at', 'resolved_at')
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('product_variant', 'alert_type', 'current_stock', 'threshold', 'message')
        }),
        ('Status', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product_variant__product', 'resolved_by')


# Custom admin actions
def activate_products(modeladmin, request, queryset):
    queryset.update(status='active')
activate_products.short_description = "Activate selected products"

def deactivate_products(modeladmin, request, queryset):
    queryset.update(status='inactive')
deactivate_products.short_description = "Deactivate selected products"

def mark_as_featured(modeladmin, request, queryset):
    queryset.update(is_featured=True)
mark_as_featured.short_description = "Mark selected products as featured"

ProductAdmin.actions = [activate_products, deactivate_products, mark_as_featured]