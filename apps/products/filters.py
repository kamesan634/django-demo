"""
Product filters.
"""
from django_filters import rest_framework as filters
from .models import Product


class ProductFilter(filters.FilterSet):
    """Product filter set."""
    name = filters.CharFilter(lookup_expr='icontains')
    sku = filters.CharFilter(lookup_expr='exact')
    category = filters.NumberFilter(field_name='category_id')
    min_price = filters.NumberFilter(field_name='sale_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='sale_price', lookup_expr='lte')
    status = filters.ChoiceFilter(choices=Product.STATUS_CHOICES)
    is_active = filters.BooleanFilter(method='filter_is_active')

    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'status']

    def filter_is_active(self, queryset, name, value):
        if value:
            return queryset.filter(status='ACTIVE')
        return queryset.exclude(status='ACTIVE')
