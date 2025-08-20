from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import Category, Brand, Product, ProductVariant, StockMovement, StockAlert


class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories"""
    
    class Meta:
        model = Category
        fields = [
            'name', 'entity', 'parent', 'description', 'image',
            'meta_title', 'meta_description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Title'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'SEO Description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.entity = kwargs.pop('entity', None)
        super().__init__(*args, **kwargs)
        
        # Filter parent categories by entity
        if self.entity:
            self.fields['parent'].queryset = Category.objects.filter(
                entity=self.entity,
                is_active=True
            )
            self.fields['entity'].initial = self.entity
        
        # Exclude self from parent choices when editing
        if self.instance.pk:
            self.fields['parent'].queryset = self.fields['parent'].queryset.exclude(pk=self.instance.pk)

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        
        # Prevent circular relationships
        if parent and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise ValidationError("A category cannot be its own parent.")
        
        return cleaned_data


class BrandForm(forms.ModelForm):
    """Form for creating/editing brands"""
    
    class Meta:
        model = Brand
        fields = [
            'name', 'entity', 'description', 'logo', 'website', 
            'contact_email', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand Name'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.brand.com'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@brand.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.entity = kwargs.pop('entity', None)
        super().__init__(*args, **kwargs)
        
        if self.entity:
            self.fields['entity'].initial = self.entity


class ProductForm(forms.ModelForm):
    """Form for creating/editing products"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'entity', 'category', 'brand', 'description', 'material',
            'gender', 'age_group', 'season', 'cost_price', 'selling_price',
            'discount_price', 'tax_rate', 'primary_image', 'gallery_images',
            'meta_title', 'meta_description', 'tags', 'is_featured',
            'status', 'track_inventory', 'allow_backorder',
            'min_stock_level', 'max_stock_level', 'weight', 'dimensions'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'entity': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'material': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Leather, Canvas'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'age_group': forms.Select(attrs={'class': 'form-control'}),
            'season': forms.Select(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
            'gallery_images': forms.FileInput(attrs={'class': 'form-control', 'multiple': True}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Title'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma separated tags'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'track_inventory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_backorder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': 'kg'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'L x W x H (cm)'}),
        }

    def __init__(self, *args, **kwargs):
        self.entity = kwargs.pop('entity', None)
        super().__init__(*args, **kwargs)
        
        # Filter categories and brands by entity
        if self.entity:
            self.fields['category'].queryset = Category.objects.filter(
                entity=self.entity,
                is_active=True
            )
            self.fields['brand'].queryset = Brand.objects.filter(
                entity=self.entity,
                is_active=True
            )
            self.fields['entity'].initial = self.entity

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        discount_price = cleaned_data.get('discount_price')
        
        if cost_price and selling_price and selling_price < cost_price:
            raise ValidationError("Selling price cannot be less than cost price.")
        
        if discount_price and selling_price and discount_price > selling_price:
            raise ValidationError("Discount price cannot be greater than selling price.")
        
        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    """Form for creating/editing product variants"""
    
    class Meta:
        model = ProductVariant
        fields = [
            'product', 'size', 'color', 'sku', 'barcode', 'cost_price',
            'selling_price', 'discount_price', 'stock_quantity', 'reorder_level',
            'max_stock_level', 'weight', 'dimensions', 'image',
            'is_active', 'track_inventory', 'allow_backorder'
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8, 9, 10'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Black, Brown'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stock Keeping Unit'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Barcode'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'L x W x H (cm)'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'track_inventory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_backorder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku:
            queryset = ProductVariant.objects.filter(sku=sku)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("A product variant with this SKU already exists.")
        return sku


# Inline formset for product variants
ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class StockMovementForm(forms.ModelForm):
    """Form for recording stock movements"""
    
    class Meta:
        model = StockMovement
        fields = [
            'product_variant', 'movement_type', 'quantity', 'reason',
            'reference_number', 'notes'
        ]
        widgets = {
            'product_variant': forms.Select(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for stock movement'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity


class StockAdjustmentForm(forms.Form):
    """Form for bulk stock adjustments"""
    
    adjustment_type = forms.ChoiceField(
        choices=[('add', 'Add Stock'), ('remove', 'Remove Stock'), ('set', 'Set Stock Level')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'})
    )
    reason = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for adjustment'})
    )
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'})
    )
    variant_ids = forms.CharField(
        widget=forms.HiddenInput()
    )


class ProductSearchForm(forms.Form):
    """Form for searching products"""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    entity = forms.ChoiceField(
        choices=[('', 'All Entities'), ('mpshoes', 'MPshoes'), ('mpfootwear', 'MPfootwear')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        empty_label='All Brands',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Product.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_featured = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Featured'), ('false', 'Not Featured')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price_min = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Price'})
    )
    price_max = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Price'})
    )


class StockAlertForm(forms.ModelForm):
    """Form for managing stock alerts"""
    
    class Meta:
        model = StockAlert
        fields = ['product_variant', 'alert_type', 'threshold', 'message']
        widgets = {
            'product_variant': forms.Select(attrs={'class': 'form-control'}),
            'alert_type': forms.Select(attrs={'class': 'form-control'}),
            'threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BulkProductActionForm(forms.Form):
    """Form for bulk product actions"""
    
    ACTION_CHOICES = [
        ('activate', 'Activate Products'),
        ('deactivate', 'Deactivate Products'),
        ('feature', 'Mark as Featured'),
        ('unfeature', 'Remove Featured'),
        ('update_prices', 'Update Prices'),
        ('export', 'Export Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price_adjustment_type = forms.ChoiceField(
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    price_adjustment_value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    product_ids = forms.CharField(
        widget=forms.HiddenInput()
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'update_prices':
            price_type = cleaned_data.get('price_adjustment_type')
            price_value = cleaned_data.get('price_adjustment_value')
            
            if not price_type or not price_value:
                raise ValidationError("Price adjustment type and value are required for price updates.")
        
        return cleaned_data


class ProductImportForm(forms.Form):
    """Form for importing products from CSV/Excel"""
    
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
    create_variants = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith(('.csv', '.xlsx', '.xls')):
                raise ValidationError("Please upload a CSV or Excel file.")
            
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size should not exceed 10MB.")
        
        return file


class QuickStockUpdateForm(forms.Form):
    """Quick form for updating stock levels"""
    
    sku = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter SKU',
            'autofocus': True
        })
    )
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Stock Level'
        })
    )
    reason = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for update'
        })
    )

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku:
            try:
                ProductVariant.objects.get(sku=sku, is_active=True)
            except ProductVariant.DoesNotExist:
                raise ValidationError("Product variant with this SKU does not exist.")
        return sku

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise ValidationError("Stock quantity cannot be negative.")
        return quantity