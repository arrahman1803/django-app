from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin, Address, Attachment
)

User = get_user_model()


class Order(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    E-commerce order model.
    """
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('PACKED', 'Packed'),
        ('SHIPPED', 'Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('PROCESSING', 'Payment Processing'),
        ('COMPLETED', 'Payment Completed'),
        ('FAILED', 'Payment Failed'),
        ('REFUNDED', 'Payment Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
    ]

    FULFILLMENT_STATUS_CHOICES = [
        ('UNFULFILLED', 'Unfulfilled'),
        ('PARTIAL', 'Partially Fulfilled'),
        ('FULFILLED', 'Fulfilled'),
        ('RETURNED', 'Returned'),
    ]

    # Order Identification
    order_number = models.CharField(max_length=50, unique=True)
    display_id = models.CharField(max_length=20, unique=True, blank=True)  # Customer-facing ID
    
    # Customer Information
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15, blank=True)
    
    # Guest Customer Info (for guest checkouts)
    guest_first_name = models.CharField(max_length=100, blank=True)
    guest_last_name = models.CharField(max_length=100, blank=True)
    is_guest_order = models.BooleanField(default=False)
    
    # Order Dates
    order_date = models.DateTimeField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    
    # Financial Information
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    coupon_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status Tracking
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    fulfillment_status = models.CharField(max_length=20, choices=FULFILLMENT_STATUS_CHOICES, default='UNFULFILLED')
    
    # Shipping Information
    shipping_method = models.CharField(max_length=100, blank=True)
    shipping_carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    
    # Billing Address
    billing_first_name = models.CharField(max_length=100)
    billing_last_name = models.CharField(max_length=100)
    billing_company = models.CharField(max_length=200, blank=True)
    billing_address_1 = models.CharField(max_length=200)
    billing_address_2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100, default='India')
    billing_phone = models.CharField(max_length=15, blank=True)
    
    # Shipping Address
    shipping_first_name = models.CharField(max_length=100)
    shipping_last_name = models.CharField(max_length=100)
    shipping_company = models.CharField(max_length=200, blank=True)
    shipping_address_1 = models.CharField(max_length=200)
    shipping_address_2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='India')
    shipping_phone = models.CharField(max_length=15, blank=True)
    
    # Discounts and Coupons
    applied_coupons = models.JSONField(default=list, blank=True)
    loyalty_points_used = models.PositiveIntegerField(default=0)
    loyalty_points_earned = models.PositiveIntegerField(default=0)
    
    # Order Source
    source = models.CharField(
        max_length=50,
        choices=[
            ('WEBSITE', 'Website'),
            ('MOBILE_APP', 'Mobile App'),
            ('PHONE', 'Phone Order'),
            ('STORE', 'In-Store'),
            ('MARKETPLACE', 'Marketplace'),
        ],
        default='WEBSITE'
    )
    
    # Special Instructions
    order_notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    gift_message = models.TextField(blank=True)
    
    # Flags
    is_gift = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    is_expedited = models.BooleanField(default=False)
    
    # Risk Assessment
    fraud_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fraud risk score (0.00 to 1.00)"
    )
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('LOW', 'Low Risk'),
            ('MEDIUM', 'Medium Risk'),
            ('HIGH', 'High Risk'),
        ],
        blank=True
    )
    
    # Currency
    currency = models.CharField(max_length=3, default='INR')
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='order')

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['entity', 'order_date']),
            models.Index(fields=['order_number']),
            models.Index(fields=['display_id']),
            models.Index(fields=['customer', 'order_date']),
            models.Index(fields=['order_status', 'payment_status']),
            models.Index(fields=['tracking_number']),
        ]

    def __str__(self):
        return f"#{self.display_id or self.order_number} - ₹{self.total_amount}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        if not self.display_id:
            self.display_id = self.generate_display_id()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """
        Generate unique internal order number.
        """
        prefix = f"{self.entity[:2]}O"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_order = Order.objects.filter(
            entity=self.entity,
            order_number__startswith=f"{prefix}{date_str}",
        ).order_by('order_number').last()
        
        if last_order:
            last_number = int(last_order.order_number[-6:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:06d}"

    def generate_display_id(self):
        """
        Generate customer-facing display ID.
        """
        prefix = f"{self.entity[:2]}"
        
        last_order = Order.objects.filter(
            entity=self.entity,
        ).order_by('-id').first()
        
        if last_order and last_order.display_id:
            try:
                last_number = int(last_order.display_id[2:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1000
        else:
            new_number = 1000
            
        return f"{prefix}{new_number}"

    @property
    def customer_name(self):
        """
        Get customer full name.
        """
        if self.customer:
            return self.customer.get_full_name()
        elif self.is_guest_order:
            return f"{self.guest_first_name} {self.guest_last_name}".strip()
        else:
            return f"{self.billing_first_name} {self.billing_last_name}".strip()

    @property
    def can_cancel(self):
        """
        Check if order can be cancelled.
        """
        return self.order_status in ['PENDING', 'CONFIRMED', 'PROCESSING']

    @property
    def can_modify(self):
        """
        Check if order can be modified.
        """
        return self.order_status in ['PENDING', 'CONFIRMED']

    @property
    def items_count(self):
        """
        Get total number of items in the order.
        """
        return sum(item.quantity for item in self.items.all())

    def get_shipping_address(self):
        """
        Get formatted shipping address.
        """
        address_parts = [
            self.shipping_address_1,
            self.shipping_address_2,
            self.shipping_city,
            self.shipping_state,
            self.shipping_postal_code,
            self.shipping_country
        ]
        return ', '.join(filter(None, address_parts))

    def get_billing_address(self):
        """
        Get formatted billing address.
        """
        address_parts = [
            self.billing_address_1,
            self.billing_address_2,
            self.billing_city,
            self.billing_state,
            self.billing_postal_code,
            self.billing_country
        ]
        return ', '.join(filter(None, address_parts))


class OrderItem(BaseModel):
    """
    Individual items in an order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Product Information
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        'inventory.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Item Details (stored for historical record)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    product_image = models.URLField(blank=True)
    variant_attributes = models.JSONField(default=dict, blank=True)
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    # Discounts
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Tax
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Calculated Fields
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Fulfillment
    quantity_fulfilled = models.PositiveIntegerField(default=0)
    quantity_returned = models.PositiveIntegerField(default=0)
    
    # Gift Options
    is_gift = models.BooleanField(default=False)
    gift_wrap_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Product Details (for shoes)
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Calculate discount
        if self.discount_percentage > 0:
            self.discount_amount = (self.unit_price * self.quantity * self.discount_percentage) / 100
        
        # Calculate subtotal after discount
        subtotal = (self.unit_price * self.quantity) - self.discount_amount
        
        # Calculate tax
        self.tax_amount = (subtotal * self.tax_rate) / 100
        
        # Calculate line total
        self.line_total = subtotal + self.tax_amount + self.gift_wrap_price
        
        # Store product details
        if not self.product_name and self.product:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            if self.product.featured_image:
                self.product_image = self.product.featured_image.url
                
        super().save(*args, **kwargs)

    @property
    def quantity_pending_fulfillment(self):
        """
        Get quantity still pending fulfillment.
        """
        return self.quantity - self.quantity_fulfilled - self.quantity_returned

    @property
    def can_fulfill(self):
        """
        Check if item can be fulfilled.
        """
        return self.quantity_pending_fulfillment > 0

    @property
    def is_fully_fulfilled(self):
        """
        Check if item is fully fulfilled.
        """
        return self.quantity_fulfilled >= self.quantity


class OrderStatusHistory(BaseModel):
    """
    Track order status changes.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    
    # Status Change
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    
    # Change Details
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    change_reason = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Notification
    customer_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order.display_id}: {self.from_status} → {self.to_status}"


class OrderPayment(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Order payment transactions.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI'),
        ('NET_BANKING', 'Net Banking'),
        ('WALLET', 'Digital Wallet'),
        ('EMI', 'EMI'),
        ('COD', 'Cash on Delivery'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('GIFT_CARD', 'Gift Card'),
        ('STORE_CREDIT', 'Store Credit'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
    ]

    # Basic Information
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_id = models.CharField(max_length=100, unique=True)
    
    # Payment Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Gateway Information
    gateway = models.CharField(max_length=50, blank=True)  # razorpay, stripe, etc.
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    gateway_order_id = models.CharField(max_length=100, blank=True)
    
    # Transaction Details
    transaction_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    initiated_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    failure_reason = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Card Details (masked)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    
    # EMI Details
    emi_duration = models.PositiveIntegerField(null=True, blank=True)
    emi_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # COD Details
    cod_charges = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Order Payment'
        verbose_name_plural = 'Order Payments'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['order', 'payment_status']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['gateway_payment_id']),
        ]

    def __str__(self):
        return f"{self.payment_id} - ₹{self.amount} - {self.payment_status}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = self.generate_payment_id()
        
        # Calculate net amount
        self.net_amount = self.amount - self.transaction_fee
        
        super().save(*args, **kwargs)

    def generate_payment_id(self):
        """
        Generate unique payment ID.
        """
        prefix = f"{self.entity[:2]}PAY"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_payment = OrderPayment.objects.filter(
            entity=self.entity,
            payment_id__startswith=f"{prefix}{date_str}",
        ).order_by('payment_id').last()
        
        if last_payment:
            last_number = int(last_payment.payment_id[-6:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:06d}"

    def mark_completed(self, gateway_response=None):
        """
        Mark payment as completed.
        """
        self.payment_status = 'COMPLETED'
        self.completed_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()

    def mark_failed(self, failure_reason="", gateway_response=None):
        """
        Mark payment as failed.
        """
        self.payment_status = 'FAILED'
        self.failed_at = timezone.now()
        self.failure_reason = failure_reason
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()


class OrderRefund(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Order refund tracking.
    """
    REFUND_REASON_CHOICES = [
        ('CUSTOMER_REQUEST', 'Customer Request'),
        ('DEFECTIVE_PRODUCT', 'Defective Product'),
        ('WRONG_PRODUCT', 'Wrong Product Sent'),
        ('DAMAGED_IN_TRANSIT', 'Damaged in Transit'),
        ('ORDER_CANCELLED', 'Order Cancelled'),
        ('PAYMENT_ISSUE', 'Payment Issue'),
        ('OTHER', 'Other'),
    ]

    REFUND_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Basic Information
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(OrderPayment, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=100, unique=True)
    
    # Refund Details
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    refund_reason = models.CharField(max_length=20, choices=REFUND_REASON_CHOICES)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='PENDING')
    
    # Gateway Information
    gateway_refund_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    refund_notes = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Processing Details
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds'
    )

    class Meta:
        verbose_name = 'Order Refund'
        verbose_name_plural = 'Order Refunds'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['order', 'refund_status']),
            models.Index(fields=['refund_id']),
            models.Index(fields=['gateway_refund_id']),
        ]

    def __str__(self):
        return f"{self.refund_id} - ₹{self.refund_amount} - {self.refund_status}"

    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = self.generate_refund_id()
        super().save(*args, **kwargs)

    def generate_refund_id(self):
        """
        Generate unique refund ID.
        """
        prefix = f"{self.entity[:2]}REF"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_refund = OrderRefund.objects.filter(
            entity=self.entity,
            refund_id__startswith=f"{prefix}{date_str}",
        ).order_by('refund_id').last()
        
        if last_refund:
            last_number = int(last_refund.refund_id[-6:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:06d}"


class OrderShipment(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Order shipment tracking.
    """
    SHIPMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PACKED', 'Packed'),
        ('SHIPPED', 'Shipped'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('RETURNED', 'Returned'),
        ('LOST', 'Lost'),
        ('DAMAGED', 'Damaged'),
    ]

    # Basic Information
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    shipment_id = models.CharField(max_length=100, unique=True)
    
    # Shipping Details
    carrier = models.CharField(max_length=100)
    service_type = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    
    # Status
    shipment_status = models.CharField(max_length=20, choices=SHIPMENT_STATUS_CHOICES, default='PENDING')
    
    # Dates
    packed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Package Details
    package_weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weight in kg"
    )
    package_length = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    package_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    package_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Costs
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    insurance_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Additional Information
    special_instructions = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    
    # Signature and Photo Proof
    delivery_signature = models.CharField(max_length=200, blank=True)
    delivery_photo_url = models.URLField(blank=True)

    class Meta:
        verbose_name = 'Order Shipment'
        verbose_name_plural = 'Order Shipments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'shipment_status']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['carrier', 'shipped_at']),
        ]

    def __str__(self):
        return f"{self.shipment_id} - {self.carrier} - {self.shipment_status}"

    def save(self, *args, **kwargs):
        if not self.shipment_id:
            self.shipment_id = self.generate_shipment_id()
        super().save(*args, **kwargs)

    def generate_shipment_id(self):
        """
        Generate unique shipment ID.
        """
        prefix = f"{self.entity[:2]}SHIP"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_shipment = OrderShipment.objects.filter(
            entity=self.entity,
            shipment_id__startswith=f"{prefix}{date_str}",
        ).order_by('shipment_id').last()
        
        if last_shipment:
            last_number = int(last_shipment.shipment_id[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:04d}"


class OrderShipmentItem(BaseModel):
    """
    Items in a shipment (for partial shipments).
    """
    shipment = models.ForeignKey(OrderShipment, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='shipment_items')
    
    # Quantity being shipped
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Order Shipment Item'
        verbose_name_plural = 'Order Shipment Items'
        unique_together = ['shipment', 'order_item']

    def __str__(self):
        return f"{self.shipment.shipment_id} - {self.order_item.product_name} x {self.quantity}"