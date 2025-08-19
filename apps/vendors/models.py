from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin, Address, PhoneNumber, Attachment
)

User = get_user_model()


class Vendor(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, SoftDeleteMixin):
    """
    Vendor/Supplier model for managing suppliers.
    """
    VENDOR_TYPE_CHOICES = [
        ('MANUFACTURER', 'Manufacturer'),
        ('DISTRIBUTOR', 'Distributor'),
        ('WHOLESALER', 'Wholesaler'),
        ('RETAILER', 'Retailer'),
        ('SERVICE', 'Service Provider'),
    ]

    PAYMENT_TERMS_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('NET_15', 'Net 15 Days'),
        ('NET_30', 'Net 30 Days'),
        ('NET_60', 'Net 60 Days'),
        ('ADVANCE', 'Advance Payment'),
        ('CREDIT', 'Credit'),
    ]

    # Basic Information
    vendor_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique vendor identification code"
    )
    company_name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200, blank=True)
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES)
    
    # Contact Information
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    # Business Details
    gstin = models.CharField(max_length=15, blank=True, help_text="GST Identification Number")
    pan = models.CharField(max_length=10, blank=True, help_text="PAN Number")
    business_license = models.CharField(max_length=50, blank=True)
    
    # Financial Information
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default='NET_30'
    )
    currency = models.CharField(max_length=3, default='INR')
    
    # Rating and Performance
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0')), MinValueValidator(Decimal('5'))]
    )
    
    # Preferences
    preferred_communication = models.CharField(
        max_length=20,
        choices=[('EMAIL', 'Email'), ('PHONE', 'Phone'), ('SMS', 'SMS')],
        default='EMAIL'
    )
    
    # Additional Information
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Relationships
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_profile'
    )
    
    # Generic relations
    addresses = GenericRelation(Address, related_query_name='vendor')
    phone_numbers = GenericRelation(PhoneNumber, related_query_name='vendor')
    attachments = GenericRelation(Attachment, related_query_name='vendor')

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        indexes = [
            models.Index(fields=['vendor_code']),
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['company_name']),
            models.Index(fields=['email']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'vendor_code'],
                name='unique_vendor_code_per_entity'
            )
        ]

    def __str__(self):
        return f"{self.vendor_code} - {self.company_name}"

    def save(self, *args, **kwargs):
        if not self.vendor_code:
            self.vendor_code = self.generate_vendor_code()
        if not self.display_name:
            self.display_name = self.company_name
        super().save(*args, **kwargs)

    def generate_vendor_code(self):
        """
        Generate unique vendor code.
        """
        prefix = f"{self.entity[:2]}V"
        last_vendor = Vendor.objects.filter(
            entity=self.entity,
            vendor_code__startswith=prefix
        ).order_by('vendor_code').last()
        
        if last_vendor:
            last_number = int(last_vendor.vendor_code[3:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{new_number:04d}"

    @property
    def current_balance(self):
        """
        Calculate current outstanding balance.
        """
        return self.bills.filter(
            status__in=['PENDING', 'PARTIALLY_PAID']
        ).aggregate(
            total=models.Sum('outstanding_amount')
        )['total'] or Decimal('0.00')

    @property
    def total_purchases(self):
        """
        Calculate total purchase amount.
        """
        return self.bills.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')

    def get_primary_address(self):
        """
        Get primary address for the vendor.
        """
        return self.addresses.filter(type='BILLING').first()

    def get_primary_phone(self):
        """
        Get primary phone number for the vendor.
        """
        return self.phone_numbers.filter(is_primary=True).first()


class VendorBill(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Vendor bill/invoice model.
    """
    BILL_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    BILL_TYPE_CHOICES = [
        ('PURCHASE', 'Purchase Bill'),
        ('EXPENSE', 'Expense Bill'),
        ('CREDIT_NOTE', 'Credit Note'),
        ('DEBIT_NOTE', 'Debit Note'),
    ]

    # Basic Information
    bill_number = models.CharField(max_length=50)
    vendor_bill_number = models.CharField(max_length=50, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='bills')
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES, default='PURCHASE')
    status = models.CharField(max_length=20, choices=BILL_STATUS_CHOICES, default='DRAFT')
    
    # Dates
    bill_date = models.DateField()
    due_date = models.DateField()
    received_date = models.DateField(null=True, blank=True)
    
    # Financial Details
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Additional Information
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='vendor_bill')

    class Meta:
        verbose_name = 'Vendor Bill'
        verbose_name_plural = 'Vendor Bills'
        indexes = [
            models.Index(fields=['vendor', 'bill_date']),
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['bill_number']),
            models.Index(fields=['due_date', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entity', 'bill_number'],
                name='unique_bill_number_per_entity'
            )
        ]

    def __str__(self):
        return f"{self.bill_number} - {self.vendor.company_name}"

    def save(self, *args, **kwargs):
        if not self.bill_number:
            self.bill_number = self.generate_bill_number()
        
        self.outstanding_amount = self.total_amount - self.paid_amount
        
        # Update status based on payment
        if self.paid_amount <= 0:
            self.status = 'PENDING'
        elif self.paid_amount >= self.total_amount:
            self.status = 'PAID'
        else:
            self.status = 'PARTIALLY_PAID'
            
        super().save(*args, **kwargs)

    def generate_bill_number(self):
        """
        Generate unique bill number.
        """
        prefix = f"{self.entity[:2]}B"
        current_year = self.bill_date.year if self.bill_date else timezone.now().year
        
        last_bill = VendorBill.objects.filter(
            entity=self.entity,
            bill_number__startswith=f"{prefix}{current_year}",
        ).order_by('bill_number').last()
        
        if last_bill:
            last_number = int(last_bill.bill_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{current_year}-{new_number:04d}"


class VendorBillItem(BaseModel):
    """
    Individual items in a vendor bill.
    """
    bill = models.ForeignKey(VendorBill, on_delete=models.CASCADE, related_name='items')
    
    # Item Details
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))]
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Tax Information
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
    
    # Optional product reference
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Vendor Bill Item'
        verbose_name_plural = 'Vendor Bill Items'

    def __str__(self):
        return f"{self.description} - {self.quantity}"

    def save(self, *args, **kwargs):
        self.tax_amount = (self.quantity * self.unit_price * self.tax_rate) / 100
        self.line_total = (self.quantity * self.unit_price) + self.tax_amount
        super().save(*args, **kwargs)


class VendorPayment(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Payments made to vendors.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('UPI', 'UPI'),
        ('CARD', 'Card'),
        ('ONLINE', 'Online Payment'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Basic Information
    payment_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Reference Information
    reference_number = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    
    # Additional Information
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='vendor_payment')

    class Meta:
        verbose_name = 'Vendor Payment'
        verbose_name_plural = 'Vendor Payments'
        indexes = [
            models.Index(fields=['vendor', 'payment_date']),
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['payment_number']),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.vendor.company_name} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)

    def generate_payment_number(self):
        """
        Generate unique payment number.
        """
        prefix = f"{self.entity[:2]}P"
        current_year = self.payment_date.year if self.payment_date else timezone.now().year
        
        last_payment = VendorPayment.objects.filter(
            entity=self.entity,
            payment_number__startswith=f"{prefix}{current_year}",
        ).order_by('payment_number').last()
        
        if last_payment:
            last_number = int(last_payment.payment_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{current_year}-{new_number:04d}"


class VendorBillPayment(BaseModel):
    """
    Link between vendor payments and bills (many-to-many with additional info).
    """
    payment = models.ForeignKey(
        VendorPayment,
        on_delete=models.CASCADE,
        related_name='bill_payments'
    )
    bill = models.ForeignKey(
        VendorBill,
        on_delete=models.CASCADE,
        related_name='bill_payments'
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )

    class Meta:
        verbose_name = 'Vendor Bill Payment'
        verbose_name_plural = 'Vendor Bill Payments'
        unique_together = ['payment', 'bill']

    def __str__(self):
        return f"{self.payment.payment_number} -> {self.bill.bill_number}: ₹{self.allocated_amount}"