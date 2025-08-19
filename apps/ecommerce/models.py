from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin
)

User = get_user_model()


class ShoppingCart(BaseModel, EntityMixin):
    """
    Shopping cart for customers.
    """
    CART_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ABANDONED', 'Abandoned'),
        ('CONVERTED', 'Converted to Order'),
        ('EXPIRED', 'Expired'),
    ]

    # Customer Information
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shopping_carts'
    )
    session_key = models.CharField(max_length=40, blank=True)  # For guest users
    
    # Status
    status = models.CharField(max_length=20, choices=CART_STATUS_CHOICES, default='ACTIVE')
    
    # Totals
    items_count = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Conversion Tracking
    converted_to_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_cart'
    )
    
    # Applied Discounts
    applied_coupons = models.JSONField(default=list, blank=True)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['session_key', 'status']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        if self.customer:
            return f"Cart - {self.customer.display_name}"
        return f"Guest Cart - {self.session_key}"

    def save(self, *args, **kwargs):
        # Set expiry for guest carts
        if not self.customer and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """
        Calculate cart totals.
        """
        items = self.items.filter(is_active=True)
        self.items_count = items.count()
        self.subtotal = sum(item.line_total for item in items)
        self.save()

    def add_item(self, product, quantity=1, variant=None, **kwargs):
        """
        Add item to cart.
        """
        # Check if item already exists
        existing_item = self.items.filter(
            product=product,
            product_variant=variant,
            is_active=True
        ).first()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.save()
            return existing_item
        else:
            return CartItem.objects.create(
                cart=self,
                product=product,
                product_variant=variant,
                quantity=quantity,
                **kwargs
            )

    def remove_item(self, product, variant=None):
        """
        Remove item from cart.
        """
        self.items.filter(
            product=product,
            product_variant=variant,
            is_active=True
        ).update(is_active=False)
        self.calculate_totals()

    def clear(self):
        """
        Clear all items from cart.
        """
        self.items.filter(is_active=True).update(is_active=False)
        self.calculate_totals()

    def is_expired(self):
        """
        Check if cart is expired.
        """
        return self.expires_at and timezone.now() > self.expires_at


class CartItem(BaseModel):
    """
    Items in shopping cart.
    """
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    
    # Product Information
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        'inventory.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Quantity and Pricing
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Product Details (cached for performance)
    product_name = models.CharField(max_length=200)
    product_image = models.URLField(blank=True)
    
    # Variant Details
    variant_attributes = models.JSONField(default=dict, blank=True)
    
    # Calculated Fields
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Customization (for shoes)
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    
    # Notes
    special_instructions = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        indexes = [
            models.Index(fields=['cart', 'is_active']),
            models.Index(fields=['product', 'product_variant']),
        ]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Cache product details
        if not self.product_name and self.product:
            self.product_name = self.product.name
            if self.product.featured_image:
                self.product_image = self.product.featured_image.url
                
        # Set unit price if not provided
        if not self.unit_price and self.product:
            if self.product_variant:
                self.unit_price = self.product_variant.get_price('selling_price')
            else:
                self.unit_price = self.product.discounted_price
                
        # Calculate line total
        self.line_total = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # Update cart totals
        if self.cart_id:
            self.cart.calculate_totals()

    def get_variant_display(self):
        """
        Get display text for variant attributes.
        """
        if self.variant_attributes:
            return ', '.join([f"{k}: {v}" for k, v in self.variant_attributes.items()])
        return ''


class Coupon(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Discount coupons for e-commerce.
    """
    COUPON_TYPE_CHOICES = [
        ('PERCENTAGE', 'Percentage Discount'),
        ('FIXED', 'Fixed Amount Discount'),
        ('FREE_SHIPPING', 'Free Shipping'),
        ('BOGO', 'Buy One Get One'),
    ]