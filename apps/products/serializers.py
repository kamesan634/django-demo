"""
Product serializers.
"""
from django.db import models
from rest_framework import serializers
from .models import Category, Product, ProductVariant, ProductBarcode, Unit, TaxType


class UnitSerializer(serializers.ModelSerializer):
    """Unit serializer."""
    class Meta:
        model = Unit
        fields = ['id', 'name', 'symbol']


class TaxTypeSerializer(serializers.ModelSerializer):
    """TaxType serializer."""
    class Meta:
        model = TaxType
        fields = ['id', 'name', 'rate', 'is_default']


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer with children."""
    children = serializers.SerializerMethodField()
    full_path = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'parent', 'sort_order',
            'is_active', 'full_path', 'children',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.filter(is_deleted=False, is_active=True)
        return CategorySerializer(children, many=True).data


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Category tree serializer (recursive)."""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_deleted=False, is_active=True)
        return CategoryTreeSerializer(children, many=True).data


class ProductBarcodeSerializer(serializers.ModelSerializer):
    """ProductBarcode serializer."""
    class Meta:
        model = ProductBarcode
        fields = [
            'id', 'barcode', 'barcode_type', 'is_primary',
            'variant', 'created_at'
        ]
        read_only_fields = ['created_at']


class ProductVariantSerializer(serializers.ModelSerializer):
    """ProductVariant serializer."""
    final_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    barcodes = ProductBarcodeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'sku', 'price_adjustment',
            'final_price', 'is_active', 'barcodes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stock_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category', 'category_name',
            'sale_price', 'cost_price', 'status', 'status_display',
            'stock_quantity', 'image', 'created_at'
        ]

    def get_stock_quantity(self, obj):
        """Get total stock quantity across all warehouses."""
        total = obj.inventory_items.aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or 0


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer."""
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    unit = UnitSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True, required=False)
    tax_type = TaxTypeSerializer(read_only=True)
    tax_type_id = serializers.IntegerField(write_only=True, required=False)
    variants = ProductVariantSerializer(many=True, read_only=True)
    barcodes = ProductBarcodeSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'description',
            'category', 'category_id',
            'sale_price', 'cost_price',
            'tax_type', 'tax_type_id',
            'unit', 'unit_id',
            'safety_stock', 'status', 'status_display',
            'image', 'variants', 'barcodes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """Product create serializer with nested variants and barcodes."""
    variants = ProductVariantSerializer(many=True, required=False)
    barcodes = ProductBarcodeSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'category',
            'sale_price', 'cost_price', 'tax_type', 'unit',
            'safety_stock', 'status', 'image',
            'variants', 'barcodes'
        ]

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        barcodes_data = validated_data.pop('barcodes', [])

        product = Product.objects.create(**validated_data)

        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)

        for barcode_data in barcodes_data:
            ProductBarcode.objects.create(product=product, **barcode_data)

        return product


class BarcodeSearchResultSerializer(serializers.Serializer):
    """Barcode search result serializer."""
    product = ProductListSerializer()
    variant = ProductVariantSerializer(allow_null=True)
    barcode = serializers.CharField()
