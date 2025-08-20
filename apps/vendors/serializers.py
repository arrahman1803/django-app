from rest_framework import serializers
from decimal import Decimal
from .models import Vendor, VendorBill, VendorBillItem, VendorPayment


class VendorSerializer(serializers.ModelSerializer):
    """Serializer for Vendor model"""
    
    total_bills = serializers.SerializerMethodField()
    total_payments = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'vendor_code', 'name', 'entity', 'vendor_type', 'contact_person',
            'phone', 'email', 'website', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'tax_number',
            'registration_number', 'bank_account_number', 'bank_name', 'bank_branch',
            'credit_limit', 'payment_terms', 'total_purchases', 'outstanding_amount',
            'notes', 'status', 'is_active', 'total_bills', 'total_payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'vendor_code', 'total_purchases', 'outstanding_amount',
            'created_at', 'updated_at'
        ]

    def get_total_bills(self, obj):
        return obj.bills.count()

    def get_total_payments(self, obj):
        return obj.payments.count()

    def validate_email(self, value):
        """Validate unique email excluding current instance"""
        if value:
            queryset = Vendor.objects.filter(email=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("A vendor with this email already exists.")
        return value

    def validate_credit_limit(self, value):
        """Validate credit limit is non-negative"""
        if value and value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative.")
        return value


class VendorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for vendor list views"""
    
    outstanding_bills = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'vendor_code', 'name', 'entity', 'contact_person', 'phone',
            'email', 'total_purchases', 'outstanding_amount', 'outstanding_bills',
            'status', 'is_active', 'created_at'
        ]

    def get_outstanding_bills(self, obj):
        return obj.bills.filter(status__in=['pending', 'overdue']).count()


class VendorBillItemSerializer(serializers.ModelSerializer):
    """Serializer for VendorBillItem model"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    line_total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = VendorBillItem
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'quantity',
            'unit_price', 'discount', 'tax_rate', 'line_total'
        ]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def validate_tax_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Tax rate must be between 0 and 100.")
        return value


class VendorBillSerializer(serializers.ModelSerializer):
    """Serializer for VendorBill model"""
    
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    items = VendorBillItemSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorBill
        fields = [
            'id', 'bill_number', 'vendor', 'vendor_name', 'entity', 'bill_date',
            'due_date', 'reference_number', 'subtotal', 'tax_amount',
            'discount_amount', 'total_amount', 'paid_amount', 'remaining_amount',
            'status', 'notes', 'items', 'payments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'bill_number', 'total_amount', 'paid_amount', 'remaining_amount',
            'created_at', 'updated_at'
        ]

    def get_payments(self, obj):
        payments = obj.vendor.payments.filter(created_at__gte=obj.created_at)
        return VendorPaymentListSerializer(payments, many=True).data

    def validate(self, attrs):
        bill_date = attrs.get('bill_date')
        due_date = attrs.get('due_date')
        
        if bill_date and due_date and due_date < bill_date:
            raise serializers.ValidationError("Due date cannot be earlier than bill date.")
        
        return attrs


class VendorBillListSerializer(serializers.ModelSerializer):
    """Simplified serializer for vendor bill list views"""
    
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    days_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorBill
        fields = [
            'id', 'bill_number', 'vendor_name', 'entity', 'bill_date',
            'due_date', 'total_amount', 'paid_amount', 'remaining_amount',
            'status', 'days_overdue', 'created_at'
        ]

    def get_days_overdue(self, obj):
        from django.utils import timezone
        if obj.status == 'overdue' and obj.due_date:
            return (timezone.now().date() - obj.due_date).days
        return 0


class VendorBillCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating vendor bills with items"""
    
    items = VendorBillItemSerializer(many=True)
    
    class Meta:
        model = VendorBill
        fields = [
            'vendor', 'entity', 'bill_date', 'due_date', 'reference_number',
            'subtotal', 'tax_amount', 'discount_amount', 'notes', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        bill = VendorBill.objects.create(**validated_data)
        
        for item_data in items_data:
            VendorBillItem.objects.create(bill=bill, **item_data)
        
        # Recalculate totals
        bill.calculate_totals()
        
        return bill

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Update bill fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items
        if items_data:
            # Delete existing items
            instance.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                VendorBillItem.objects.create(bill=instance, **item_data)
            
            # Recalculate totals
            instance.calculate_totals()
        
        return instance


class VendorPaymentSerializer(serializers.ModelSerializer):
    """Serializer for VendorPayment model"""
    
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = VendorPayment
        fields = [
            'id', 'payment_number', 'vendor', 'vendor_name', 'entity',
            'amount', 'payment_date', 'payment_method', 'reference_number',
            'bank_details', 'status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['payment_number', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value


class VendorPaymentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for vendor payment list views"""
    
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = VendorPayment
        fields = [
            'id', 'payment_number', 'vendor_name', 'entity', 'amount',
            'payment_date', 'payment_method', 'status', 'created_at'
        ]


class VendorStatsSerializer(serializers.Serializer):
    """Serializer for vendor statistics"""
    
    total_vendors = serializers.IntegerField()
    active_vendors = serializers.IntegerField()
    total_bills = serializers.IntegerField()
    pending_bills = serializers.IntegerField()
    overdue_bills = serializers.IntegerField()
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payments_today = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payments_month = serializers.DecimalField(max_digits=15, decimal_places=2)


class VendorDashboardSerializer(serializers.Serializer):
    """Serializer for vendor dashboard data"""
    
    recent_bills = VendorBillListSerializer(many=True)
    recent_payments = VendorPaymentListSerializer(many=True)
    overdue_bills = VendorBillListSerializer(many=True)
    top_vendors = VendorListSerializer(many=True)
    stats = VendorStatsSerializer()


class VendorImportSerializer(serializers.Serializer):
    """Serializer for vendor import validation"""
    
    name = serializers.CharField(max_length=255)
    entity = serializers.ChoiceField(choices=[('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')])
    vendor_type = serializers.ChoiceField(choices=Vendor.VENDOR_TYPE_CHOICES, required=False)
    contact_person = serializers.CharField(max_length=255, required=False)
    phone = serializers.CharField(max_length=15, required=False)
    email = serializers.EmailField(required=False)
    address_line1 = serializers.CharField(max_length=255, required=False)
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    country = serializers.CharField(max_length=100, required=False)
    credit_limit = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    payment_terms = serializers.IntegerField(required=False)

    def validate_email(self, value):
        if value and Vendor.objects.filter(email=value).exists():
            raise serializers.ValidationError(f"Vendor with email {value} already exists.")
        return value


class VendorExportSerializer(serializers.ModelSerializer):
    """Serializer for vendor export"""
    
    vendor_type_display = serializers.CharField(source='get_vendor_type_display')
    status_display = serializers.CharField(source='get_status_display')
    
    class Meta:
        model = Vendor
        fields = [
            'vendor_code', 'name', 'entity', 'vendor_type_display', 'contact_person',
            'phone', 'email', 'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'tax_number', 'credit_limit', 'payment_terms',
            'total_purchases', 'outstanding_amount', 'status_display', 'created_at'
        ]


class PaymentSummarySerializer(serializers.Serializer):
    """Serializer for payment summary reports"""
    
    vendor_name = serializers.CharField()
    total_bills = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    overdue_amount = serializers.DecimalField(max_digits=15, decimal_places=2)