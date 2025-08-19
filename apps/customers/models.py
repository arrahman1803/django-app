from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin, Address, PhoneNumber, Attachment
)

User = get_user_model()


class Customer(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Customer model for managing customer information.
    """
    CUSTOMER_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual'),
        ('BUSINESS', 'Business'),
        ('WHOLESALE', 'Wholesale'),
        ('VIP', 'VIP Customer'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Basic Information
    customer_code = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='INDIVIDUAL')
    
    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    alternate_phone = models.CharField(max_length=15, blank=True)
    
    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    anniversary_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    # Business Details (for business customers)
    gstin = models.CharField(max_length=15, blank=True, help_text="GST Number")
    business_license = models.CharField(max_length=50, blank=True)
    
    # Financial Information
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Preferences
    preferred_communication = models.CharField(
        max_length=20,
        choices=[('EMAIL', 'Email'), ('PHONE', 'Phone'), ('SMS', 'SMS'), ('WHATSAPP', 'WhatsApp')],
        default='PHONE'
    )
    newsletter_subscription = models.BooleanField(default=True)
    sms_marketing = models.BooleanField(default=True)
    
    # Segmentation
    customer_segment = models.CharField(
        max_length=50,
        choices=[
            ('PREMIUM', 'Premium'),
            ('REGULAR', 'Regular'),
            ('OCCASIONAL', 'Occasional'),
            ('FIRST_TIME', 'First Time'),
        ],
        default='REGULAR'
    )
    
    # Source
    acquisition_source = models.CharField(
        max_length=50,
        choices=[
            ('WALK_IN', 'Walk-in'),
            ('REFERRAL', 'Referral'),
            ('ONLINE', 'Online'),
            ('SOCIAL_MEDIA', 'Social Media'),
            ('ADVERTISEMENT', 'Advertisement'),
            ('OTHER', 'Other'),
        ],
        blank=True
    )
    referral_source = models.CharField(max_length=200, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # User Account
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profile'
    )
    
    # Generic Relations
    addresses = GenericRelation(Address, related_query_name='customer')
    phone_numbers = GenericRelation(PhoneNumber, related_query_name='customer')
    attachments = GenericRelation(Attachment, related_query_name='customer')

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['customer_code']),
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['customer_type', 'customer_segment']),
        ]

    def __str__(self):
        if self.customer_type == 'BUSINESS' and self.company_name:
            return f"{self.customer_code} - {self.company_name}"
        return f"{self.customer_code} - {self.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.customer_code:
            self.customer_code = self.generate_customer_code()
        super().save(*args, **kwargs)

    def generate_customer_code(self):
        """
        Generate unique customer code.
        """
        prefix = f"{self.entity[:2]}C"
        
        last_customer = Customer.objects.filter(
            entity=self.entity,
            customer_code__startswith=prefix
        ).order_by('customer_code').last()
        
        if last_customer:
            try:
                last_number = int(last_customer.customer_code[3:])
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
            
        return f"{prefix}{new_number:05d}"

    def get_full_name(self):
        """
        Return full name of the customer.
        """
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """
        Return display name based on customer type.
        """
        if self.customer_type == 'BUSINESS' and self.company_name:
            return self.company_name
        return self.get_full_name()

    def get_primary_address(self):
        """
        Get primary address for the customer.
        """
        return self.addresses.filter(type='HOME').first()

    def get_shipping_address(self):
        """
        Get shipping address for the customer.
        """
        shipping_addr = self.addresses.filter(type='SHIPPING').first()
        return shipping_addr or self.get_primary_address()

    def get_primary_phone(self):
        """
        Get primary phone number for the customer.
        """
        return self.phone_numbers.filter(is_primary=True).first()

    def calculate_lifetime_value(self):
        """
        Calculate customer lifetime value.
        """
        total_spent = self.sales.filter(
            sale_status__in=['CONFIRMED', 'COMPLETED']
        ).aggregate(total=models.Sum('total_amount'))['total']
        return total_spent or Decimal('0.00')

    def calculate_average_order_value(self):
        """
        Calculate average order value.
        """
        sales = self.sales.filter(sale_status__in=['CONFIRMED', 'COMPLETED'])
        if sales.exists():
            total_spent = sales.aggregate(total=models.Sum('total_amount'))['total']
            return total_spent / sales.count()
        return Decimal('0.00')

    def get_last_purchase_date(self):
        """
        Get date of last purchase.
        """
        last_sale = self.sales.filter(
            sale_status__in=['CONFIRMED', 'COMPLETED']
        ).order_by('-sale_date').first()
        return last_sale.sale_date.date() if last_sale else None

    def get_purchase_frequency(self):
        """
        Calculate purchase frequency (purchases per month).
        """
        first_purchase = self.sales.filter(
            sale_status__in=['CONFIRMED', 'COMPLETED']
        ).order_by('sale_date').first()
        
        if not first_purchase:
            return 0
            
        months_since_first_purchase = (
            timezone.now().date() - first_purchase.sale_date.date()
        ).days / 30.44  # Average days in a month
        
        if months_since_first_purchase > 0:
            total_purchases = self.sales.filter(
                sale_status__in=['CONFIRMED', 'COMPLETED']
            ).count()
            return total_purchases / months_since_first_purchase
        return 0


class CustomerGroup(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Customer groups for segmentation and targeted marketing.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Criteria
    criteria = models.JSONField(
        default=dict,
        help_text="JSON criteria for automatic group assignment"
    )
    
    # Discounts and Benefits
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    special_pricing = models.BooleanField(default=False)
    
    # Marketing
    marketing_emails = models.BooleanField(default=True)
    sms_campaigns = models.BooleanField(default=True)
    
    # Additional
    color_code = models.CharField(max_length=7, default='#007bff')
    is_automatic = models.BooleanField(
        default=False,
        help_text="Automatically assign customers based on criteria"
    )

    class Meta:
        verbose_name = 'Customer Group'
        verbose_name_plural = 'Customer Groups'
        indexes = [
            models.Index(fields=['entity', 'status']),
        ]

    def __str__(self):
        return self.name

    def get_customers(self):
        """
        Get all customers in this group.
        """
        return self.customers.filter(status='ACTIVE')

    def get_customer_count(self):
        """
        Get count of customers in this group.
        """
        return self.get_customers().count()


class CustomerGroupMembership(BaseModel):
    """
    Many-to-many relationship between customers and groups.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE, related_name='memberships')
    
    # Membership details
    joined_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    auto_assigned = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Customer Group Membership'
        verbose_name_plural = 'Customer Group Memberships'
        unique_together = ['customer', 'group']

    def __str__(self):
        return f"{self.customer.display_name} - {self.group.name}"


class LoyaltyProgram(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Loyalty program configuration.
    """
    PROGRAM_TYPE_CHOICES = [
        ('POINTS', 'Points Based'),
        ('CASHBACK', 'Cashback'),
        ('TIER', 'Tier Based'),
        ('PUNCH_CARD', 'Punch Card'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPE_CHOICES, default='POINTS')
    
    # Points Configuration (for POINTS type)
    points_per_rupee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    rupees_per_point = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    minimum_points_redemption = models.PositiveIntegerField(default=100)
    points_expiry_days = models.PositiveIntegerField(null=True, blank=True)
    
    # Cashback Configuration (for CASHBACK type)
    cashback_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Tier Configuration (for TIER type)
    tier_levels = models.JSONField(
        default=list,
        help_text="List of tier configurations"
    )
    
    # Punch Card Configuration (for PUNCH_CARD type)
    punches_required = models.PositiveIntegerField(default=10)
    reward_description = models.CharField(max_length=200, blank=True)
    
    # General Settings
    welcome_bonus = models.PositiveIntegerField(default=0)
    birthday_bonus = models.PositiveIntegerField(default=0)
    anniversary_bonus = models.PositiveIntegerField(default=0)
    referral_bonus = models.PositiveIntegerField(default=0)
    
    # Terms and Conditions
    terms_and_conditions = models.TextField(blank=True)
    
    # Validity
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Loyalty Program'
        verbose_name_plural = 'Loyalty Programs'
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return self.name

    def is_active(self):
        """
        Check if the loyalty program is currently active.
        """
        today = timezone.now().date()
        return (
            self.status == 'ACTIVE' and
            self.start_date <= today and
            (self.end_date is None or self.end_date >= today)
        )


class CustomerLoyalty(BaseModel, EntityMixin):
    """
    Customer loyalty account and points tracking.
    """
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='loyalty_account'
    )
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='customer_accounts'
    )
    
    # Points Balance
    points_balance = models.PositiveIntegerField(default=0)
    total_points_earned = models.PositiveIntegerField(default=0)
    total_points_redeemed = models.PositiveIntegerField(default=0)
    
    # Cashback Balance (for cashback programs)
    cashback_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Tier Information (for tier-based programs)
    current_tier = models.CharField(max_length=50, blank=True)
    tier_progress = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    next_tier_requirement = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Punch Card (for punch card programs)
    current_punches = models.PositiveIntegerField(default=0)
    completed_cards = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    enrolled_date = models.DateField(default=timezone.now)
    last_activity_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Customer Loyalty Account'
        verbose_name_plural = 'Customer Loyalty Accounts'
        unique_together = ['customer', 'program']
        indexes = [
            models.Index(fields=['entity', 'is_active']),
            models.Index(fields=['customer', 'program']),
        ]

    def __str__(self):
        return f"{self.customer.display_name} - {self.program.name}"

    def add_points(self, points, description="", reference_type="", reference_id=None):
        """
        Add points to customer's account.
        """
        self.points_balance += points
        self.total_points_earned += points
        self.last_activity_date = timezone.now().date()
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            loyalty_account=self,
            transaction_type='EARN',
            points=points,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            balance_after=self.points_balance
        )

    def redeem_points(self, points, description="", reference_type="", reference_id=None):
        """
        Redeem points from customer's account.
        """
        if points > self.points_balance:
            raise ValueError("Insufficient points balance")
            
        self.points_balance -= points
        self.total_points_redeemed += points
        self.last_activity_date = timezone.now().date()
        self.save()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            loyalty_account=self,
            transaction_type='REDEEM',
            points=points,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            balance_after=self.points_balance
        )

    def calculate_points_for_amount(self, amount):
        """
        Calculate points earned for a given purchase amount.
        """
        if self.program.program_type == 'POINTS':
            return int(amount * self.program.points_per_rupee)
        return 0

    def calculate_cashback_for_amount(self, amount):
        """
        Calculate cashback for a given purchase amount.
        """
        if (self.program.program_type == 'CASHBACK' and 
            amount >= self.program.minimum_order_amount):
            return (amount * self.program.cashback_percentage) / 100
        return Decimal('0.00')


class LoyaltyTransaction(BaseModel, EntityMixin):
    """
    Track all loyalty point transactions.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('EARN', 'Points Earned'),
        ('REDEEM', 'Points Redeemed'),
        ('EXPIRE', 'Points Expired'),
        ('ADJUST', 'Manual Adjustment'),
        ('BONUS', 'Bonus Points'),
    ]

    loyalty_account = models.ForeignKey(
        CustomerLoyalty,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    # Transaction Details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    points = models.IntegerField()  # Can be negative for redemptions
    description = models.CharField(max_length=200, blank=True)
    
    # Reference
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=50, blank=True)
    
    # Balance tracking
    balance_before = models.PositiveIntegerField(default=0)
    balance_after = models.PositiveIntegerField(default=0)
    
    # Expiry (for earned points)
    expires_at = models.DateField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Loyalty Transaction'
        verbose_name_plural = 'Loyalty Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['loyalty_account', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
            models.Index(fields=['expires_at', 'is_expired']),
        ]

    def __str__(self):
        return f"{self.loyalty_account.customer.display_name} - {self.transaction_type} - {self.points} points"


class CustomerWishlist(BaseModel):
    """
    Customer wishlist for products.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    product_variant = models.ForeignKey(
        'inventory.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='wishlisted_by'
    )
    
    # Preferences
    preferred_size = models.CharField(max_length=20, blank=True)
    preferred_color = models.CharField(max_length=50, blank=True)
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Notifications
    notify_on_sale = models.BooleanField(default=True)
    notify_on_restock = models.BooleanField(default=True)
    notify_on_price_drop = models.BooleanField(default=True)
    
    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Customer Wishlist Item'
        verbose_name_plural = 'Customer Wishlist Items'
        unique_together = ['customer', 'product', 'product_variant']
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['product', 'notify_on_restock']),
        ]

    def __str__(self):
        return f"{self.customer.display_name} - {self.product.name}"


class CustomerFeedback(BaseModel, EntityMixin):
    """
    Customer feedback and reviews.
    """
    FEEDBACK_TYPE_CHOICES = [
        ('PRODUCT_REVIEW', 'Product Review'),
        ('SERVICE_FEEDBACK', 'Service Feedback'),
        ('STORE_REVIEW', 'Store Review'),
        ('COMPLAINT', 'Complaint'),
        ('SUGGESTION', 'Suggestion'),
    ]

    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    # Feedback Details
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200)
    feedback_text = models.TextField()
    
    # Reference (if related to specific product/sale)
    related_product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback'
    )
    related_sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback'
    )
    
    # Status
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_responded = models.BooleanField(default=False)
    
    # Response
    response_text = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_responses'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_purchase = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Customer Feedback'
        verbose_name_plural = 'Customer Feedback'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'feedback_type']),
            models.Index(fields=['related_product', 'is_public']),
            models.Index(fields=['rating', 'is_public']),
        ]

    def __str__(self):
        return f"{self.customer.display_name} - {self.feedback_type} - {self.rating or 'No'} rating"


class CustomerCommunication(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Track all communications with customers.
    """
    COMMUNICATION_TYPE_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('CALL', 'Phone Call'),
        ('WHATSAPP', 'WhatsApp'),
        ('MEETING', 'In-Person Meeting'),
        ('LETTER', 'Letter/Post'),
    ]

    COMMUNICATION_PURPOSE_CHOICES = [
        ('MARKETING', 'Marketing'),
        ('SUPPORT', 'Customer Support'),
        ('FOLLOW_UP', 'Follow-up'),
        ('REMINDER', 'Reminder'),
        ('NOTIFICATION', 'Notification'),
        ('SURVEY', 'Survey/Feedback'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='communications'
    )
    
    # Communication Details
    communication_type = models.CharField(max_length=20, choices=COMMUNICATION_TYPE_CHOICES)
    communication_purpose = models.CharField(max_length=20, choices=COMMUNICATION_PURPOSE_CHOICES)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    # Status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Response
    customer_response = models.TextField(blank=True)
    response_received_at = models.DateTimeField(null=True, blank=True)
    
    # Campaign (if part of marketing campaign)
    campaign_name = models.CharField(max_length=100, blank=True)
    campaign_id = models.CharField(max_length=50, blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='customer_communication')

    class Meta:
        verbose_name = 'Customer Communication'
        verbose_name_plural = 'Customer Communications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'communication_type']),
            models.Index(fields=['communication_purpose', 'sent_at']),
            models.Index(fields=['campaign_id', 'is_sent']),
        ]

    def __str__(self):
        return f"{self.customer.display_name} - {self.communication_type} - {self.subject}"

    def mark_as_sent(self):
        """
        Mark communication as sent.
        """
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save()

    def mark_as_delivered(self):
        """
        Mark communication as delivered.
        """
        self.is_delivered = True
        self.delivered_at = timezone.now()
        self.save()

    def mark_as_read(self):
        """
        Mark communication as read by customer.
        """
        self.is_read = True
        self.read_at = timezone.now()
        self.save()