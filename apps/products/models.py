"""
Product models: Category, Product, ProductVariant, ProductBarcode.
"""
from django.db import models
from apps.core.models import BaseModel


class Category(BaseModel):
    """Product category model with hierarchy support."""
    name = models.CharField(max_length=100, verbose_name='分類名稱')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='父分類'
    )
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'categories'
        verbose_name = '商品分類'
        verbose_name_plural = '商品分類'
        ordering = ['sort_order', 'name']

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} > {self.name}'
        return self.name

    @property
    def full_path(self):
        """Get full category path."""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)


class Unit(BaseModel):
    """Unit of measure model."""
    name = models.CharField(max_length=20, verbose_name='單位名稱')
    symbol = models.CharField(max_length=10, verbose_name='符號')

    class Meta:
        db_table = 'units'
        verbose_name = '單位'
        verbose_name_plural = '單位'

    def __str__(self):
        return f'{self.name} ({self.symbol})'


class TaxType(BaseModel):
    """Tax type model."""
    name = models.CharField(max_length=50, verbose_name='稅別名稱')
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5,
        verbose_name='稅率 (%)'
    )
    is_default = models.BooleanField(default=False, verbose_name='預設')

    class Meta:
        db_table = 'tax_types'
        verbose_name = '稅別'
        verbose_name_plural = '稅別'

    def __str__(self):
        return f'{self.name} ({self.rate}%)'


class Product(BaseModel):
    """Product model."""
    STATUS_CHOICES = [
        ('ACTIVE', '銷售中'),
        ('INACTIVE', '停售'),
        ('DISCONTINUED', '已下架'),
    ]

    name = models.CharField(max_length=200, verbose_name='商品名稱')
    sku = models.CharField(max_length=50, unique=True, verbose_name='SKU')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='分類'
    )
    description = models.TextField(blank=True, verbose_name='商品描述')
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='售價'
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='成本價'
    )
    tax_type = models.ForeignKey(
        TaxType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='稅別'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='單位'
    )
    safety_stock = models.IntegerField(default=0, verbose_name='安全庫存')
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='狀態'
    )
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name='商品圖片'
    )

    class Meta:
        db_table = 'products'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f'{self.name} ({self.sku})'


class ProductVariant(BaseModel):
    """Product variant model (e.g., color, size)."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='商品'
    )
    name = models.CharField(max_length=100, verbose_name='規格名稱')
    sku = models.CharField(max_length=50, unique=True, verbose_name='規格SKU')
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='價格調整'
    )
    is_active = models.BooleanField(default=True, verbose_name='啟用')

    class Meta:
        db_table = 'product_variants'
        verbose_name = '商品規格'
        verbose_name_plural = '商品規格'

    def __str__(self):
        return f'{self.product.name} - {self.name}'

    @property
    def final_price(self):
        """Calculate final price including adjustment."""
        return self.product.sale_price + self.price_adjustment


class ProductBarcode(BaseModel):
    """Product barcode model."""
    TYPE_CHOICES = [
        ('EAN13', 'EAN-13'),
        ('EAN8', 'EAN-8'),
        ('UPC', 'UPC'),
        ('CUSTOM', '自訂'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='barcodes',
        verbose_name='商品'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='barcodes',
        verbose_name='規格'
    )
    barcode = models.CharField(max_length=50, unique=True, verbose_name='條碼')
    barcode_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='EAN13',
        verbose_name='條碼類型'
    )
    is_primary = models.BooleanField(default=False, verbose_name='主條碼')

    class Meta:
        db_table = 'product_barcodes'
        verbose_name = '商品條碼'
        verbose_name_plural = '商品條碼'
        indexes = [
            models.Index(fields=['barcode']),
        ]

    def __str__(self):
        return f'{self.product.name} - {self.barcode}'
