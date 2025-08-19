from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit, ResizeToFill
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin, Attachment
)

User = get_user_model()


class Category(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Product category model with hierarchical structure.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Hierarchical structure
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Display
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="CSS class for icon")
    color = models.CharField(max_length=7, default='#000000', help_text="Hex color code")
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Ordering
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['parent', 'sort_order']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_full_path(self):
        """
        Get the full category path.
        """
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)

    def get_all_children(self):
        """
        Get all descendant categories.
        """
        children = list(self.children.all())
        for child in self.children.all():
            children.extend(child.get_all_children())
        return children


class Brand(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Product brand model.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    website = models.URLField(blank=True)
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name


class Product(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Product model for inventory management.
    """
    PRODUCT_TYPE_CHOICES = [
        ('SIMPLE', 'Simple Product'),
        ('VARIABLE', 'Variable Product'),
        ('GROUPED', 'Grouped Product'),
        ('DIGITAL', 'Digital Product'),
    ]

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('UNISEX', 'Unisex'),
        ('KIDS', 'Kids'),
    ]

    # Basic Information
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=50, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='SIMPLE')
    
    # Classification
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='UNISEX')
    
    # Description
    short_description = models.TextField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list, blank=True, help_text="List of product features")
    specifications = models.JSONField(default=dict, blank=True, help_text="Product specifications")
    
    # Images
    featured_image = models.ImageField(upload_to='products/featured/', null=True, blank=True)
    featured_image_thumbnail = ImageSpecField(
        source='featured_image',
        processors=[ResizeToFit(300, 300)],
        format='JPEG',
        options={'quality': 85}
    )
    featured_image_small = ImageSpecField(
        source='featured_image',
        processors=[ResizeToFit(150, 150)],
        format='JPEG',
        options={'quality': 80}
    )
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Cost price from supplier"
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum Retail Price"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Inventory
    track_inventory = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    out_of_stock_threshold = models.PositiveIntegerField(default=0)
    
    # Physical Attributes
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, help_text="Weight in kg")
    length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Length in cm")
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Width in cm")
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Height in cm")
    
    # SEO
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    
    # E-commerce
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    allow_backorders = models.BooleanField(default=False)
    
    # Shipping
    requires_shipping = models.BooleanField(default=True)
    shipping_class = models.CharField(max_length=50, blank=True)
    
    # Additional
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    notes = models.TextField(blank=True)
    
    # Supplier
    primary_supplier = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_products'
    )
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='product')

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'brand']),
            models.Index(fields=['is_featured', 'status']),
            models.Index(fields=['gender', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'sku'],
                name='unique_sku_per_entity'
            )
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)

    def generate_sku(self):
        """
        Generate unique SKU.
        """
        prefix = f"{self.entity[:2]}"
        category_code = self.category.name[:3].upper() if self.category else "GEN"
        
        last_product = Product.objects.filter(
            entity=self.entity,
            sku__startswith=f"{prefix}{category_code}",
        ).order_by('sku').last()
        
        if last_product:
            try:
                last_number = int(last_product.sku[-4:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
            
        return f"{prefix}{category_code}{new_number:04d}"

    @property
    def available_quantity(self):
        """
        Get available stock quantity.
        """
        return max(0, self.stock_quantity - self.reserved_quantity)

    @property
    def is_in_stock(self):
        """
        Check if product is in stock.
        """
        return self.available_quantity > self.out_of_stock_threshold

    @property
    def is_low_stock(self):
        """
        Check if product is low in stock.
        """
        return self.available_quantity <= self.low_stock_threshold

    @property
    def discounted_price(self):
        """
        Calculate discounted price.
        """
        if self.discount_percentage > 0:
            discount_amount = (self.selling_price * self.discount_percentage) / 100
            return self.selling_price - discount_amount
        return self.selling_price

    def get_images(self):
        """
        Get all product images.
        """
        return self.images.filter(is_active=True).order_by('sort_order')


class ProductImage(BaseModel):
    """
    Product images model.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Image variations
    thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFit(150, 150)],
        format='JPEG',
        options={'quality': 80}
    )
    medium = ImageSpecField(
        source='image',
        processors=[ResizeToFit(300, 300)],
        format='JPEG',
        options={'quality': 85}
    )
    large = ImageSpecField(
        source='image',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 90}
    )

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"


class ProductVariant(BaseModel, StatusMixin):
    """
    Product variants for variable products (different sizes, colors, etc.).
    """
    parent_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    
    # Variant Information
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=50, blank=True)
    
    # Variant Attributes
    attributes = models.JSONField(
        default=dict,
        help_text="Variant attributes like size, color, etc."
    )
    
    # Pricing (can override parent pricing)
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(null=True, blank=True)
    
    # Physical Attributes (can override parent)
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    
    # Images
    featured_image = models.ImageField(upload_to='products/variants/', null=True, blank=True)

    class Meta:
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        indexes = [
            models.Index(fields=['parent_product', 'status']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f"{self.parent_product.name} - {self.name}"

    @property
    def available_quantity(self):
        """
        Get available stock quantity.
        """
        return max(0, self.stock_quantity - self.reserved_quantity)

    def get_price(self, price_type='selling_price'):
        """
        Get price, fallback to parent product if not set.
        """
        variant_price = getattr(self, price_type)
        if variant_price:
            return variant_price
        return getattr(self.parent_product, price_type)


class StockMovement(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Track all stock movements for products and variants.
    """
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('TRANSFER', 'Transfer'),
        ('ADJUSTMENT', 'Adjustment'),
        ('DAMAGE', 'Damage'),
        ('RETURN', 'Return'),
    ]

    REFERENCE_TYPE_CHOICES = [
        ('PURCHASE', 'Purchase Order'),
        ('SALE', 'Sale Order'),
        ('TRANSFER', 'Stock Transfer'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('MANUAL', 'Manual Entry'),
    ]

    # Product Reference
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements'
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    
    # Movement Details
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Positive for IN, Negative for OUT")
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Stock Levels
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    
    # Reference
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPE_CHOICES)
    reference_number = models.CharField(max_length=50, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    
    # Additional Information
    reason = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['entity', 'movement_type']),
            models.Index(fields=['reference_type', 'reference_number']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} - {self.quantity}"


class StockAdjustment(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Stock adjustments for inventory corrections.
    """
    ADJUSTMENT_TYPE_CHOICES = [
        ('INCREASE', 'Increase Stock'),
        ('DECREASE', 'Decrease Stock'),
        ('RECOUNT', 'Stock Recount'),
    ]

    REASON_CHOICES = [
        ('DAMAGE', 'Damaged Goods'),
        ('THEFT', 'Theft'),
        ('EXPIRED', 'Expired'),
        ('RECOUNT', 'Physical Recount'),
        ('RETURN', 'Supplier Return'),
        ('OTHER', 'Other'),
    ]

    # Basic Information
    adjustment_number = models.CharField(max_length=50, unique=True)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    adjustment_date = models.DateField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    
    # Approval
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_adjustments'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        indexes = [
            models.Index(fields=['entity', 'adjustment_date']),
            models.Index(fields=['adjustment_number']),
        ]

    def __str__(self):
        return f"{self.adjustment_number} - {self.adjustment_type}"

    def save(self, *args, **kwargs):
        if not self.adjustment_number:
            self.adjustment_number = self.generate_adjustment_number()
        super().save(*args, **kwargs)

    def generate_adjustment_number(self):
        """
        Generate unique adjustment number.
        """
        prefix = f"{self.entity[:2]}ADJ"
        current_year = self.adjustment_date.year
        
        last_adjustment = StockAdjustment.objects.filter(
            entity=self.entity,
            adjustment_number__startswith=f"{prefix}{current_year}",
        ).order_by('adjustment_number').last()
        
        if last_adjustment:
            last_number = int(last_adjustment.adjustment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{current_year}-{new_number:04d}"


class StockAdjustmentItem(BaseModel):
    """
    Individual items in a stock adjustment.
    """
    adjustment = models.ForeignKey(
        StockAdjustment,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Quantities
    current_quantity = models.PositiveIntegerField()
    adjusted_quantity = models.PositiveIntegerField()
    difference = models.IntegerField(help_text="Adjusted - Current")
    
    # Pricing
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Additional Information
    reason = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Stock Adjustment Item'
        verbose_name_plural = 'Stock Adjustment Items'

    def __str__(self):
        return f"{self.product.name} - {self.difference}"

    def save(self, *args, **kwargs):
        self.difference = self.adjusted_quantity - self.current_quantity
        self.total_cost = abs(self.difference) * self.unit_cost
        super().save(*args, **kwargs)


class Supplier(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Alternative suppliers for products.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers')
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='supplied_products')
    
    # Supplier specific details
    supplier_sku = models.CharField(max_length=50, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_quantity = models.PositiveIntegerField(default=1)
    lead_time_days = models.PositiveIntegerField(default=0)
    
    # Priority
    is_primary = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Product Supplier'
        verbose_name_plural = 'Product Suppliers'
        unique_together = ['product', 'vendor']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
            models.Index(fields=['vendor', 'priority']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.vendor.company_name}"