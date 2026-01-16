"""
Tests for products models.
"""
import pytest
from decimal import Decimal
from apps.products.models import Category, Product, TaxType, Unit, ProductBarcode


@pytest.mark.django_db
class TestCategoryModel:
    """Tests for Category model."""

    def test_create_category(self):
        """Test creating a category."""
        category = Category.objects.create(
            name='飲料',
            sort_order=1
        )
        assert category.name == '飲料'
        assert category.is_active is True

    def test_category_hierarchy(self):
        """Test category parent-child relationship."""
        parent = Category.objects.create(name='飲料')
        child = Category.objects.create(name='茶類', parent=parent)

        assert child.parent == parent
        assert parent.children.count() == 1
        assert parent.children.first() == child

    def test_category_full_path(self):
        """Test category full path property."""
        parent = Category.objects.create(name='飲料')
        child = Category.objects.create(name='茶類', parent=parent)

        assert child.full_path == '飲料 > 茶類'

    def test_category_str(self):
        """Test category string representation."""
        parent = Category.objects.create(name='飲料')
        child = Category.objects.create(name='茶類', parent=parent)

        assert str(parent) == '飲料'
        assert '茶類' in str(child)


@pytest.mark.django_db
class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self, create_category):
        """Test creating a product."""
        category = create_category(name='零食')
        product = Product.objects.create(
            name='洋芋片',
            sku='SNK001',
            category=category,
            sale_price=Decimal('35.00'),
            cost_price=Decimal('25.00'),
            status='ACTIVE'
        )

        assert product.name == '洋芋片'
        assert product.sku == 'SNK001'
        assert product.sale_price == Decimal('35.00')
        assert product.category == category

    def test_product_str(self, create_product):
        """Test product string representation."""
        product = create_product(name='測試商品', sku='TEST001')
        assert '測試商品' in str(product)
        assert 'TEST001' in str(product)

    def test_product_with_tax_type(self, create_category):
        """Test product with tax type."""
        tax_type = TaxType.objects.create(
            name='應稅',
            rate=Decimal('5'),
            is_default=True
        )
        product = Product.objects.create(
            name='含稅商品',
            sku='TAX001',
            sale_price=Decimal('100.00'),
            tax_type=tax_type
        )

        assert product.tax_type == tax_type
        assert product.tax_type.rate == Decimal('5')

    def test_product_with_unit(self, create_category):
        """Test product with unit."""
        unit = Unit.objects.create(name='瓶', symbol='btl')
        product = Product.objects.create(
            name='飲料',
            sku='DRK001',
            sale_price=Decimal('25.00'),
            unit=unit
        )

        assert product.unit == unit
        assert product.unit.symbol == 'btl'


@pytest.mark.django_db
class TestProductBarcodeModel:
    """Tests for ProductBarcode model."""

    def test_create_barcode(self, create_product):
        """Test creating a product barcode."""
        product = create_product()
        barcode = ProductBarcode.objects.create(
            product=product,
            barcode='4710000000001',
            barcode_type='EAN13',
            is_primary=True
        )

        assert barcode.barcode == '4710000000001'
        assert barcode.is_primary is True
        assert barcode.product == product

    def test_multiple_barcodes(self, create_product):
        """Test product with multiple barcodes."""
        product = create_product()
        barcode1 = ProductBarcode.objects.create(
            product=product,
            barcode='4710000000001',
            is_primary=True
        )
        barcode2 = ProductBarcode.objects.create(
            product=product,
            barcode='4710000000002',
            is_primary=False
        )

        assert product.barcodes.count() == 2


@pytest.mark.django_db
class TestTaxTypeModel:
    """Tests for TaxType model."""

    def test_create_tax_type(self):
        """Test creating a tax type."""
        tax_type = TaxType.objects.create(
            name='應稅',
            rate=Decimal('5'),
            is_default=True
        )

        assert tax_type.name == '應稅'
        assert tax_type.rate == Decimal('5')

    def test_tax_type_str(self):
        """Test tax type string representation."""
        tax_type = TaxType.objects.create(name='免稅', rate=Decimal('0'))
        assert '免稅' in str(tax_type)


@pytest.mark.django_db
class TestUnitModel:
    """Tests for Unit model."""

    def test_create_unit(self):
        """Test creating a unit."""
        unit = Unit.objects.create(name='公斤', symbol='kg')

        assert unit.name == '公斤'
        assert unit.symbol == 'kg'

    def test_unit_str(self):
        """Test unit string representation."""
        unit = Unit.objects.create(name='個', symbol='pcs')
        assert '個' in str(unit)
