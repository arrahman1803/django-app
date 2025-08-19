from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid

from apps.core.models import (
    BaseModel, EntityMixin, UserTrackingMixin, Attachment
)

User = get_user_model()


class PaymentGateway(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Payment gateway configuration.
    """
    GATEWAY_TYPE_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('STRIPE', 'Stripe'),
        ('PAYTM', 'Paytm'),
        ('PAYPAL', 'PayPal'),
        ('PHONEPE', 'PhonePe'),
        ('GPAY', 'Google Pay'),
        ('CUSTOM', 'Custom Gateway'),
    ]

    name = models.CharField(max_length=100)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPE_CHOICES)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    is_test_mode = models.BooleanField(default=True)
    
    # Credentials (encrypted in production)
    api_key = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    webhook_secret = models.CharField(max_length=200, blank=True)
    
    # Endpoints
    api_url = models.URLField(blank=True)
    webhook_url = models.URLField(blank=True)
    
    # Supported Methods
    supported_methods = models.JSONField(
        default=list,
        help_text="List of supported payment methods"
    )
    
    # Fees
    transaction_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000')
    )
    transaction_fee_fixed = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Limits
    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00')
    )
    maximum_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Processing
    auto_capture = models.BooleanField(default=True)
    settlement_time_hours = models.PositiveIntegerField(default=24)
    
    # Display
    display_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='payment_gateways/', null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Payment Gateway'
        verbose_name_plural = 'Payment Gateways'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['entity', 'is_active']),
            models.Index(fields=['gateway_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.display_name or self.name} ({self.gateway_type})"

    def calculate_fee(self, amount):
        """
        Calculate transaction fee for given amount.
        """
        percentage_fee = (amount * self.transaction_fee_percentage) / 100
        return percentage_fee + self.transaction_fee_fixed


class Payment(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Generic payment model for all types of payments.
    """
    PAYMENT_TYPE_CHOICES = [
        ('ORDER', 'Order Payment'),
        ('INVOICE', 'Invoice Payment'),
        ('SUBSCRIPTION', 'Subscription Payment'),
        ('REFUND', 'Refund'),
        ('PAYOUT', 'Payout'),
        ('TOP_UP', 'Wallet Top-up'),
        ('OTHER', 'Other'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('AUTHORIZED', 'Authorized'),
        ('CAPTURED', 'Captured'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
        ('PARTIALLY_REFUNDED', 'Partially Refunded'),
        ('DISPUTED', 'Disputed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI'),
        ('NET_BANKING', 'Net Banking'),
        ('WALLET', 'Digital Wallet'),
        ('EMI', 'EMI'),
        ('BNPL', 'Buy Now Pay Later'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('GIFT_CARD', 'Gift Card'),
        ('STORE_CREDIT', 'Store Credit'),
        ('COD', 'Cash on Delivery'),
    ]

    # Basic Information
    payment_id = models.CharField(max_length=100, unique=True, db_index=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    
    # Amount Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    currency = models.CharField(max_length=3, default='INR')
    
    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Gateway Information
    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    gateway_payment_id = models.CharField(max_length=200, blank=True, db_index=True)
    gateway_order_id = models.CharField(max_length=200, blank=True)
    
    # Customer Information
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    
    # Generic Foreign Key for related object (order, invoice, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Fee Information
    gateway_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Card Information (masked)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    
    # Bank Information
    bank_name = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    
    # UPI Information
    upi_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(default=timezone.now)
    authorized_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Failure Information
    failure_reason = models.CharField(max_length=200, blank=True)
    failure_code = models.CharField(max_length=50, blank=True)
    
    # Gateway Response
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Risk Assessment
    risk_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Risk score from 0.00 to 1.00"
    )
    
    # Additional Information
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Reconciliation
    is_reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='payment')

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['entity', 'payment_status']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['gateway_payment_id']),
            models.Index(fields=['customer', 'initiated_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['payment_method', 'payment_status']),
        ]

    def __str__(self):
        return f"{self.payment_id} - ₹{self.amount} - {self.payment_status}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = self.generate_payment_id()
        
        # Calculate net amount
        self.net_amount = self.amount - self.gateway_fee
        
        super().save(*args, **kwargs)

    def generate_payment_id(self):
        """
        Generate unique payment ID.
        """
        prefix = f"{self.entity[:2]}PAY"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_payment = Payment.objects.filter(
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
            self.gateway_response.update(gateway_response)
        self.save()

    def mark_failed(self, failure_reason="", failure_code="", gateway_response=None):
        """
        Mark payment as failed.
        """
        self.payment_status = 'FAILED'
        self.failed_at = timezone.now()
        self.failure_reason = failure_reason
        self.failure_code = failure_code
        if gateway_response:
            self.gateway_response.update(gateway_response)
        self.save()


class PaymentRefund(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Payment refund tracking.
    """
    REFUND_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    REFUND_TYPE_CHOICES = [
        ('FULL', 'Full Refund'),
        ('PARTIAL', 'Partial Refund'),
        ('CHARGEBACK', 'Chargeback'),
    ]

    # Basic Information
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=100, unique=True)
    refund_type = models.CharField(max_length=20, choices=REFUND_TYPE_CHOICES, default='FULL')
    
    # Refund Details
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    refund_reason = models.CharField(max_length=200)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='PENDING')
    
    # Gateway Information
    gateway_refund_id = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Processing Information
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds'
    )
    
    # Gateway Response
    gateway_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    
    # Additional Information
    internal_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Payment Refund'
        verbose_name_plural = 'Payment Refunds'
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['payment', 'refund_status']),
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
        
        last_refund = PaymentRefund.objects.filter(
            entity=self.entity,
            refund_id__startswith=f"{prefix}{date_str}",
        ).order_by('refund_id').last()
        
        if last_refund:
            last_number = int(last_refund.refund_id[-6:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:06d}"


class Wallet(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Customer wallet for storing credits and cashback.
    """
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    # Balance
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    cashback_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    promotional_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Limits
    daily_spend_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    monthly_spend_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)
    frozen_reason = models.CharField(max_length=200, blank=True)
    frozen_at = models.DateTimeField(null=True, blank=True)
    
    # Security
    pin_hash = models.CharField(max_length=128, blank=True)
    last_transaction_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Customer Wallet'
        verbose_name_plural = 'Customer Wallets'
        indexes = [
            models.Index(fields=['entity', 'is_active']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"{self.customer.display_name} - Wallet (₹{self.balance})"

    @property
    def total_balance(self):
        """
        Get total available balance.
        """
        return self.balance + self.cashback_balance + self.promotional_balance

    def add_balance(self, amount, transaction_type='TOP_UP', description='', reference=None):
        """
        Add balance to wallet.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
            
        self.balance += amount
        self.last_transaction_at = timezone.now()
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=str(reference.id) if reference else ''
        )

    def deduct_balance(self, amount, transaction_type='PURCHASE', description='', reference=None):
        """
        Deduct balance from wallet.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.total_balance:
            raise ValueError("Insufficient wallet balance")
            
        # Deduct from balances in order: promotional -> cashback -> main
        remaining = amount
        
        if remaining > 0 and self.promotional_balance > 0:
            deduct_promotional = min(remaining, self.promotional_balance)
            self.promotional_balance -= deduct_promotional
            remaining -= deduct_promotional
            
        if remaining > 0 and self.cashback_balance > 0:
            deduct_cashback = min(remaining, self.cashback_balance)
            self.cashback_balance -= deduct_cashback
            remaining -= deduct_cashback
            
        if remaining > 0:
            self.balance -= remaining
            
        self.last_transaction_at = timezone.now()
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=-amount,  # Negative for deduction
            balance_after=self.total_balance,
            description=description,
            reference_id=str(reference.id) if reference else ''
        )


class WalletTransaction(BaseModel, EntityMixin):
    """
    Wallet transaction history.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('TOP_UP', 'Top Up'),
        ('PURCHASE', 'Purchase'),
        ('REFUND', 'Refund'),
        ('CASHBACK', 'Cashback'),
        ('PROMOTION', 'Promotional Credit'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('EXPIRY', 'Balance Expiry'),
        ('TRANSFER', 'Transfer'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction Details
    transaction_id = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Positive for credit, negative for debit"
    )
    
    # Balance Tracking
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Reference Information
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    
    # Additional Information
    description = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Processing
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )

    class Meta:
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['transaction_type', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)

    def generate_transaction_id(self):
        """
        Generate unique transaction ID.
        """
        prefix = f"{self.entity[:2]}WT"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_transaction = WalletTransaction.objects.filter(
            entity=self.entity,
            transaction_id__startswith=f"{prefix}{date_str}",
        ).order_by('transaction_id').last()
        
        if last_transaction:
            last_number = int(last_transaction.transaction_id[-8:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:08d}"


class GiftCard(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Gift card model.
    """
    GIFT_CARD_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('REDEEMED', 'Fully Redeemed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('SUSPENDED', 'Suspended'),
    ]

    # Basic Information
    code = models.CharField(max_length=20, unique=True)
    
    # Amount
    initial_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    current_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Validity
    issued_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    
    # Status
    gift_card_status = models.CharField(max_length=20, choices=GIFT_CARD_STATUS_CHOICES, default='ACTIVE')
    
    # Purchaser Information
    purchaser = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchased_gift_cards'
    )
    purchase_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gift_cards'
    )
    
    # Recipient Information
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=15, blank=True)
    
    # Message
    gift_message = models.TextField(blank=True)
    
    # Usage Restrictions
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    applicable_categories = models.ManyToManyField(
        'inventory.Category',
        blank=True,
        help_text="If empty, applies to all categories"
    )
    applicable_products = models.ManyToManyField(
        'inventory.Product',
        blank=True,
        help_text="If empty, applies to all products"
    )
    
    # Usage Tracking
    times_used = models.PositiveIntegerField(default=0)
    first_used_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Gift Card'
        verbose_name_plural = 'Gift Cards'
        indexes = [
            models.Index(fields=['entity', 'gift_card_status']),
            models.Index(fields=['code']),
            models.Index(fields=['expiry_date', 'gift_card_status']),
        ]

    def __str__(self):
        return f"{self.code} - ₹{self.current_balance}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)

    def generate_code(self):
        """
        Generate unique gift card code.
        """
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not GiftCard.objects.filter(code=code).exists():
                return code

    def is_valid(self):
        """
        Check if gift card is valid for use.
        """
        return (
            self.gift_card_status == 'ACTIVE' and
            self.current_balance > 0 and
            self.expiry_date >= timezone.now().date()
        )

    def can_redeem(self, amount, order=None):
        """
        Check if gift card can be redeemed for given amount.
        """
        if not self.is_valid():
            return False
            
        if amount > self.current_balance:
            return False
            
        # Check minimum order amount
        if order and order.subtotal < self.minimum_order_amount:
            return False
            
        return True

    def redeem(self, amount, order=None, description=''):
        """
        Redeem gift card amount.
        """
        if not self.can_redeem(amount, order):
            raise ValueError("Cannot redeem gift card")
            
        self.current_balance -= amount
        self.times_used += 1
        
        if not self.first_used_at:
            self.first_used_at = timezone.now()
        self.last_used_at = timezone.now()
        
        if self.current_balance <= 0:
            self.gift_card_status = 'REDEEMED'
            
        self.save()
        
        # Create transaction record
        GiftCardTransaction.objects.create(
            gift_card=self,
            transaction_type='REDEMPTION',
            amount=-amount,
            balance_after=self.current_balance,
            order=order,
            description=description
        )


class GiftCardTransaction(BaseModel, EntityMixin):
    """
    Gift card transaction history.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('ISSUED', 'Issued'),
        ('REDEMPTION', 'Redemption'),
        ('REFUND', 'Refund'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('EXPIRY', 'Expired'),
        ('CANCELLATION', 'Cancelled'),
    ]

    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction Details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Positive for credit, negative for debit"
    )
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reference
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gift_card_transactions'
    )
    
    # Additional Information
    description = models.CharField(max_length=500, blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gift_card_transactions'
    )

    class Meta:
        verbose_name = 'Gift Card Transaction'
        verbose_name_plural = 'Gift Card Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gift_card', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.gift_card.code} - {self.transaction_type} - ₹{self.amount}"


class PaymentWebhook(BaseModel, EntityMixin):
    """
    Track payment gateway webhooks.
    """
    WEBHOOK_STATUS_CHOICES = [
        ('RECEIVED', 'Received'),
        ('PROCESSING', 'Processing'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('IGNORED', 'Ignored'),
    ]

    # Basic Information
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name='webhooks')
    webhook_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, choices=WEBHOOK_STATUS_CHOICES, default='RECEIVED')
    
    # Data
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict, blank=True)
    
    # Processing
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    
    # Related Payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhooks'
    )
    
    # Error Information
    error_message = models.TextField(blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    signature_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Payment Webhook'
        verbose_name_plural = 'Payment Webhooks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gateway', 'event_type']),
            models.Index(fields=['webhook_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.webhook_id} - {self.event_type} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.webhook_id:
            self.webhook_id = str(uuid.uuid4())
        super().save(*args, **kwargs)