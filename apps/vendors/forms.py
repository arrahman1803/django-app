from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Vendor, VendorBill, VendorBillItem, VendorPayment


class VendorForm(forms.ModelForm):
    """Form for creating/editing vendors"""
    
    class Meta:
        model = Vendor
        fields = [
            'name', 'entity', 'vendor_type', 'contact_person', 'phone', 'email', 'website',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'tax_number', 'registration_number', 'bank_account_number', 'bank_name', 'bank_branch',
            'credit_limit', 'payment_terms', 'notes', 'status', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vendor Name'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'vendor_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXXXXXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'vendor@example.com'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.example.com'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apartment, suite, etc.'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'value': 'India'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST Number'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registration Number'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank Account Number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank Name'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch Name'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_terms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Days'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes...'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check for duplicate email excluding current instance
            queryset = Vendor.objects.filter(email=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("A vendor with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Basic phone validation
            import re
            if not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
                raise ValidationError("Please enter a valid phone number.")
        return phone


class VendorBillForm(forms.ModelForm):
    """Form for creating/editing vendor bills"""
    
    class Meta:
        model = VendorBill
        fields = [
            'vendor', 'entity', 'bill_date', 'due_date', 'reference_number',
            'subtotal', 'tax_amount', 'discount_amount', 'notes', 'status'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'bill_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference/Invoice Number'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.entity = kwargs.pop('entity', None)
        super().__init__(*args, **kwargs)
        
        # Filter vendors by entity if provided
        if self.entity:
            self.fields['vendor'].queryset = Vendor.objects.filter(
                entity=self.entity, 
                is_active=True
            )
            self.fields['entity'].initial = self.entity

    def clean(self):
        cleaned_data = super().clean()
        bill_date = cleaned_data.get('bill_date')
        due_date = cleaned_data.get('due_date')
        
        if bill_date and due_date and due_date < bill_date:
            raise ValidationError("Due date cannot be earlier than bill date.")
        
        return cleaned_data


class VendorBillItemForm(forms.ModelForm):
    """Form for vendor bill items"""
    
    class Meta:
        model = VendorBillItem
        fields = ['product', 'quantity', 'unit_price', 'discount', 'tax_rate']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")
        return unit_price


# Inline formset for vendor bill items
VendorBillItemFormSet = inlineformset_factory(
    VendorBill,
    VendorBillItem,
    form=VendorBillItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class VendorPaymentForm(forms.ModelForm):
    """Form for vendor payments"""
    
    class Meta:
        model = VendorPayment
        fields = [
            'vendor', 'entity', 'amount', 'payment_date', 'payment_method',
            'reference_number', 'bank_details', 'notes', 'status'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction Reference'}),
            'bank_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Bank details if applicable'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Payment notes...'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.entity = kwargs.pop('entity', None)
        super().__init__(*args, **kwargs)
        
        # Filter vendors by entity
        if self.entity:
            self.fields['vendor'].queryset = Vendor.objects.filter(
                entity=self.entity,
                is_active=True
            )
            self.fields['entity'].initial = self.entity

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        return amount


class VendorSearchForm(forms.Form):
    """Form for searching vendors"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search vendors...'
        })
    )
    entity = forms.ChoiceField(
        choices=[('', 'All Entities'), ('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    vendor_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Vendor.VENDOR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Vendor.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class VendorBillSearchForm(forms.Form):
    """Form for searching vendor bills"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search bills...'
        })
    )
    entity = forms.ChoiceField(
        choices=[('', 'All Entities'), ('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.filter(is_active=True),
        required=False,
        empty_label='All Vendors',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + VendorBill.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class VendorPaymentSearchForm(forms.Form):
    """Form for searching vendor payments"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search payments...'
        })
    )
    entity = forms.ChoiceField(
        choices=[('', 'All Entities'), ('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.filter(is_active=True),
        required=False,
        empty_label='All Vendors',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=[('', 'All Methods')] + VendorPayment.PAYMENT_METHOD_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + VendorPayment.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class BulkVendorActionForm(forms.Form):
    """Form for bulk vendor actions"""
    
    ACTION_CHOICES = [
        ('activate', 'Activate Vendors'),
        ('deactivate', 'Deactivate Vendors'),
        ('change_status', 'Change Status'),
        ('export', 'Export Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=Vendor.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    vendor_ids = forms.CharField(
        widget=forms.HiddenInput()
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        status = cleaned_data.get('status')
        
        if action == 'change_status' and not status:
            raise ValidationError("Status is required for status change action.")
        
        return cleaned_data


class VendorImportForm(forms.Form):
    """Form for importing vendors from CSV/Excel"""
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    entity = forms.ChoiceField(
        choices=[('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith(('.csv', '.xlsx', '.xls')):
                raise ValidationError("Please upload a CSV or Excel file.")
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("File size should not exceed 5MB.")
        
        return file