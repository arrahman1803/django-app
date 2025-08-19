	from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from apps.core.models import (
    BaseModel, EntityMixin, StatusMixin, UserTrackingMixin, 
    SoftDeleteMixin, Attachment
)

User = get_user_model()


class Sale(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Main sales transaction model.
    """
    SALE_TYPE_CHOICES = [
        ('POS', 'Point of Sale'),
        ('ONLINE', 'Online Order'),
        ('PHONE', 'Phone Order'),
        ('WHOLESALE', 'Wholesale'),
        ('RETURN', 'Return'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('REFUNDED', 'Refunded'),
        ('CANCELLED', 'Cancelled'),
    ]

    SALE_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    ]

    # Basic Information
    sale_number = models.CharField(max_length=50, unique=True)
    sale_type = models.CharField(max_length=20, choices=SALE_TYPE_CHOICES, default='POS')
    sale_date = models.DateTimeField(default=timezone.now)
    
    # Customer Information
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales'
    )
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)
    
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
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
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
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    balance_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    sale_status = models.CharField(max_length=20, choices=SALE_STATUS_CHOICES, default='DRAFT')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Staff Information
    sales_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_made',
        limit_choices_to={'user_type__in': ['STAFF', 'MANAGER', 'ADMIN']}
    )
    
    # Additional Information
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Reference Information
    reference_number = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=50, blank=True)
    
    # Delivery Information
    delivery_date = models.DateField(null=True, blank=True)
    delivery_address = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    
    # Commission
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='sale')

    class Meta:
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['entity', 'sale_date']),
            models.Index(fields=['sale_number']),
            models.Index(fields=['customer', 'sale_date']),
            models.Index(fields=['sales_person', 'sale_date']),
            models.Index(fields=['sale_status', 'payment_status']),
        ]

    def __str__(self):
        return f"{self.sale_number} - ₹{self.total_amount}"

    def save(self, *args, **kwargs):
        if not self.sale_number:
            self.sale_number = self.generate_sale_number()
        
        # Calculate balance
        self.balance_amount = self.total_amount - self.paid_amount
        
        # Update payment status
        if self.paid_amount <= 0:
            self.payment_status = 'PENDING'
        elif self.paid_amount >= self.total_amount:
            self.payment_status = 'PAID'
        else:
            self.payment_status = 'PARTIAL'
            
        # Calculate commission
        if self.commission_rate > 0:
            self.commission_amount = (self.total_amount * self.commission_rate) / 100
            
        super().save(*args, **kwargs)

    def generate_sale_number(self):
        """
        Generate unique sale number.
        """
        prefix = f"{self.entity[:2]}S"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_sale = Sale.objects.filter(
            entity=self.entity,
            sale_number__startswith=f"{prefix}{date_str}",
        ).order_by('sale_number').last()
        
        if last_sale:
            last_number = int(last_sale.sale_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:04d}"

    def get_profit(self):
        """
        Calculate total profit from this sale.
        """
        total_cost = sum(item.cost_price * item.quantity for item in self.items.all())
        return self.total_amount - total_cost

    def get_profit_percentage(self):
        """
        Calculate profit percentage.
        """
        total_cost = sum(item.cost_price * item.quantity for item in self.items.all())
        if total_cost > 0:
            return ((self.total_amount - total_cost) / total_cost) * 100
        return 0


class SaleItem(BaseModel):
    """
    Individual items in a sale.
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    
    # Product Information
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        'inventory.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Item Details
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Discount
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
    
    # Totals
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'

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
        self.line_total = subtotal + self.tax_amount
        
        # Store product details for historical record
        if not self.product_name and self.product:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            if not self.cost_price:
                self.cost_price = self.product.cost_price
                
        super().save(*args, **kwargs)

    @property
    def profit(self):
        """
        Calculate profit for this item.
        """
        return (self.unit_price - self.cost_price) * self.quantity

    @property
    def profit_percentage(self):
        """
        Calculate profit percentage for this item.
        """
        if self.cost_price > 0:
            return ((self.unit_price - self.cost_price) / self.cost_price) * 100
        return 0


class SalePayment(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Payments received for sales.
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT', 'Store Credit'),
        ('WALLET', 'Digital Wallet'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    # Basic Information
    payment_number = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Reference Information
    reference_number = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Bank/Card Details
    bank_name = models.CharField(max_length=100, blank=True)
    card_last_four = models.CharField(max_length=4, blank=True)
    
    # Cheque Details
    cheque_number = models.CharField(max_length=50, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='sale_payment')

    class Meta:
        verbose_name = 'Sale Payment'
        verbose_name_plural = 'Sale Payments'
        indexes = [
            models.Index(fields=['sale', 'payment_date']),
            models.Index(fields=['entity', 'payment_method']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['status', 'payment_date']),
        ]

    def __str__(self):
        return f"{self.payment_number} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)

    def generate_payment_number(self):
        """
        Generate unique payment number.
        """
        prefix = f"{self.entity[:2]}SP"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_payment = SalePayment.objects.filter(
            entity=self.entity,
            payment_number__startswith=f"{prefix}{date_str}",
        ).order_by('payment_number').last()
        
        if last_payment:
            last_number = int(last_payment.payment_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:04d}"


class SaleReturn(BaseModel, EntityMixin, StatusMixin, UserTrackingMixin):
    """
    Sale returns and refunds.
    """
    RETURN_TYPE_CHOICES = [
        ('FULL', 'Full Return'),
        ('PARTIAL', 'Partial Return'),
        ('EXCHANGE', 'Exchange'),
    ]

    RETURN_REASON_CHOICES = [
        ('DEFECTIVE', 'Defective Product'),
        ('WRONG_SIZE', 'Wrong Size'),
        ('WRONG_COLOR', 'Wrong Color'),
        ('DAMAGED', 'Damaged in Transit'),
        ('NOT_AS_DESCRIBED', 'Not as Described'),
        ('CHANGED_MIND', 'Changed Mind'),
        ('OTHER', 'Other'),
    ]

    REFUND_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('REFUNDED', 'Refunded'),
    ]

    # Basic Information
    return_number = models.CharField(max_length=50, unique=True)
    original_sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES)
    return_date = models.DateTimeField(default=timezone.now)
    
    # Return Details
    return_reason = models.CharField(max_length=20, choices=RETURN_REASON_CHOICES)
    return_description = models.TextField(blank=True)
    
    # Financial Information
    return_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    restocking_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='PENDING')
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_returns'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Attachments
    attachments = GenericRelation(Attachment, related_query_name='sale_return')

    class Meta:
        verbose_name = 'Sale Return'
        verbose_name_plural = 'Sale Returns'
        indexes = [
            models.Index(fields=['original_sale', 'return_date']),
            models.Index(fields=['entity', 'refund_status']),
            models.Index(fields=['return_number']),
        ]

    def __str__(self):
        return f"{self.return_number} - ₹{self.return_amount}"

    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = self.generate_return_number()
        
        # Calculate refund amount
        self.refund_amount = self.return_amount - self.restocking_fee
        
        super().save(*args, **kwargs)

    def generate_return_number(self):
        """
        Generate unique return number.
        """
        prefix = f"{self.entity[:2]}R"
        today = timezone.now().date()
        date_str = today.strftime('%Y%m%d')
        
        last_return = SaleReturn.objects.filter(
            entity=self.entity,
            return_number__startswith=f"{prefix}{date_str}",
        ).order_by('return_number').last()
        
        if last_return:
            last_number = int(last_return.return_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{date_str}{new_number:04d}"


class SaleReturnItem(BaseModel):
    """
    Individual items in a sale return.
    """
    return_order = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    original_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name='return_items')
    
    # Return Details
    return_quantity = models.PositiveIntegerField()
    return_reason = models.CharField(max_length=200, blank=True)
    
    # Condition
    item_condition = models.CharField(
        max_length=20,
        choices=[
            ('GOOD', 'Good Condition'),
            ('DAMAGED', 'Damaged'),
            ('DEFECTIVE', 'Defective'),
            ('USED', 'Used'),
        ],
        default='GOOD'
    )
    
    # Restocking
    can_restock = models.BooleanField(default=True)
    restocked = models.BooleanField(default=False)
    restocked_at = models.DateTimeField(null=True, blank=True)
    
    # Financial
    unit_refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Sale Return Item'
        verbose_name_plural = 'Sale Return Items'

    def __str__(self):
        return f"{self.original_item.product_name} x {self.return_quantity}"

    def save(self, *args, **kwargs):
        if not self.unit_refund_amount:
            self.unit_refund_amount = self.original_item.unit_price
        
        self.total_refund_amount = self.unit_refund_amount * self.return_quantity
        super().save(*args, **kwargs)


class DailySales(BaseModel, EntityMixin):
    """
    Daily sales summary for quick reporting.
    """
    date = models.DateField()
    
    # Sales Summary
    total_sales_count = models.PositiveIntegerField(default=0)
    total_sales_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_items_sold = models.PositiveIntegerField(default=0)
    
    # Payment Summary
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    upi_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Returns Summary
    total_returns_count = models.PositiveIntegerField(default=0)
    total_returns_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Profit Summary
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    profit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Staff Summary
    sales_staff_count = models.PositiveIntegerField(default=0)
    
    # Customer Summary
    new_customers = models.PositiveIntegerField(default=0)
    repeat_customers = models.PositiveIntegerField(default=0)
    
    # Additional metrics
    average_sale_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    largest_sale_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Daily Sales Summary'
        verbose_name_plural = 'Daily Sales Summaries'
        unique_together = ['entity', 'date']
        indexes = [
            models.Index(fields=['entity', 'date']),
        ]

    def __str__(self):
        return f"{self.entity} - {self.date} - ₹{self.total_sales_amount}"

    def calculate_metrics(self):
        """
        Calculate all metrics for the day.
        """
        sales = Sale.objects.filter(
            entity=self.entity,
            sale_date__date=self.date,
            sale_status__in=['CONFIRMED', 'COMPLETED']
        )
        
        # Basic counts
        self.total_sales_count = sales.count()
        self.total_sales_amount = sum(sale.total_amount for sale in sales)
        self.total_items_sold = sum(sale.items.count() for sale in sales)
        
        # Payment method breakdown
        payments = SalePayment.objects.filter(
            sale__in=sales,
            status='COMPLETED'
        )
        
        self.cash_sales = sum(p.amount for p in payments if p.payment_method == 'CASH')
        self.card_sales = sum(p.amount for p in payments if p.payment_method == 'CARD')
        self.upi_sales = sum(p.amount for p in payments if p.payment_method == 'UPI')
        self.other_sales = sum(p.amount for p in payments if p.payment_method not in ['CASH', 'CARD', 'UPI'])
        
        # Returns
        returns = SaleReturn.objects.filter(
            entity=self.entity,
            return_date__date=self.date
        )
        self.total_returns_count = returns.count()
        self.total_returns_amount = sum(ret.return_amount for ret in returns)
        
        # Profit calculations
        self.total_cost = sum(sale.items.aggregate(
            total=models.Sum(models.F('cost_price') * models.F('quantity'))
        )['total'] or Decimal('0') for sale in sales)
        
        self.total_profit = self.total_sales_amount - self.total_cost
        
        if self.total_cost > 0:
            self.profit_percentage = (self.total_profit / self.total_cost) * 100
        
        # Average and largest sale
        if self.total_sales_count > 0:
            self.average_sale_value = self.total_sales_amount / self.total_sales_count
            self.largest_sale_value = max(sale.total_amount for sale in sales)
        
        # Staff count
        self.sales_staff_count = sales.values('sales_person').distinct().count()
        
        self.save()


class SalesTarget(BaseModel, EntityMixin, UserTrackingMixin):
    """
    Sales targets for staff members.
    """
    TARGET_PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    TARGET_TYPE_CHOICES = [
        ('AMOUNT', 'Sales Amount'),
        ('QUANTITY', 'Items Quantity'),
        ('CUSTOMERS', 'New Customers'),
    ]

    # Basic Information
    staff_member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sales_targets'
    )
    target_period = models.CharField(max_length=20, choices=TARGET_PERIOD_CHOICES)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    
    # Period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Target
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    achieved_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Performance
    achievement_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Incentives
    incentive_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    incentive_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Sales Target'
        verbose_name_plural = 'Sales Targets'
        indexes = [
            models.Index(fields=['staff_member', 'start_date', 'end_date']),
            models.Index(fields=['entity', 'target_period']),
        ]
        unique_together = ['staff_member', 'target_period', 'start_date', 'target_type']

    def __str__(self):
        return f"{self.staff_member.get_full_name()} - {self.target_period} - {self.target_value}"

    def calculate_achievement(self):
        """
        Calculate achievement for the target period.
        """
        sales = Sale.objects.filter(
            entity=self.entity,
            sales_person=self.staff_member,
            sale_date__date__gte=self.start_date,
            sale_date__date__lte=self.end_date,
            sale_status__in=['CONFIRMED', 'COMPLETED']
        )
        
        if self.target_type == 'AMOUNT':
            self.achieved_value = sum(sale.total_amount for sale in sales)
        elif self.target_type == 'QUANTITY':
            self.achieved_value = sum(sale.items.count() for sale in sales)
        elif self.target_type == 'CUSTOMERS':
            self.achieved_value = sales.values('customer').distinct().count()
        
        # Calculate achievement percentage
        if self.target_value > 0:
            self.achievement_percentage = (self.achieved_value / self.target_value) * 100
        
        # Calculate incentive
        if self.achievement_percentage >= 100 and self.incentive_percentage > 0:
            base_amount = self.achieved_value if self.target_type == 'AMOUNT' else self.target_value
            self.incentive_amount = (base_amount * self.incentive_percentage) / 100
        
        self.save()