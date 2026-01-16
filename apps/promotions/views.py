"""
Promotions views.
"""
from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.core.views import BaseViewSet
from apps.core.mixins import StandardResponseMixin
from .models import Promotion, Coupon
from .serializers import (
    PromotionSerializer,
    CouponSerializer,
    CalculateDiscountSerializer,
    ValidateCouponSerializer,
)


class PromotionViewSet(StandardResponseMixin, BaseViewSet):
    """Promotion management ViewSet."""
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    search_fields = ['name']
    filterset_fields = ['promotion_type', 'is_active']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active promotions."""
        now = timezone.now()
        active_promotions = self.get_queryset().filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        serializer = self.get_serializer(active_promotions, many=True)
        return self.success_response(data=serializer.data)

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate applicable discounts for cart items."""
        serializer = CalculateDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        items = data['items']
        customer_id = data.get('customer_id')
        store_id = data.get('store_id')
        coupon_code = data.get('coupon_code')

        total_discount = Decimal('0')
        item_discounts = {}
        applied_promotions = []

        # Calculate subtotal
        subtotal = sum(
            Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
            for item in items
        )

        # Get active promotions
        now = timezone.now()
        promotions = Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

        # Filter by store if specified
        if store_id:
            promotions = promotions.filter(
                models.Q(stores__isnull=True) | models.Q(stores__id=store_id)
            ).distinct()

        # Apply promotions (simplified logic)
        for promo in promotions:
            if promo.min_purchase > 0 and subtotal < promo.min_purchase:
                continue

            if promo.promotion_type == 'PERCENTAGE':
                discount = subtotal * promo.discount_value / 100
            elif promo.promotion_type == 'FIXED':
                discount = promo.discount_value
            else:
                discount = Decimal('0')

            if discount > 0:
                total_discount += discount
                applied_promotions.append({
                    'id': promo.id,
                    'name': promo.name,
                    'discount': float(discount)
                })

        # Apply coupon if provided
        coupon_discount = Decimal('0')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                if coupon.is_valid and subtotal >= coupon.min_purchase:
                    if coupon.discount_type == 'PERCENTAGE':
                        coupon_discount = subtotal * coupon.discount_value / 100
                        if coupon.max_discount and coupon_discount > coupon.max_discount:
                            coupon_discount = coupon.max_discount
                    else:
                        coupon_discount = coupon.discount_value

                    total_discount += coupon_discount
                    applied_promotions.append({
                        'id': f'coupon_{coupon.id}',
                        'name': f'優惠券: {coupon.name}',
                        'discount': float(coupon_discount)
                    })
            except Coupon.DoesNotExist:
                pass

        return self.success_response(data={
            'subtotal': float(subtotal),
            'total_discount': float(total_discount),
            'final_amount': float(subtotal - total_discount),
            'item_discounts': item_discounts,
            'applied_promotions': applied_promotions
        })


class CouponViewSet(StandardResponseMixin, BaseViewSet):
    """Coupon management ViewSet."""
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    search_fields = ['code', 'name']
    filterset_fields = ['status', 'discount_type']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate a coupon code."""
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        total_amount = serializer.validated_data.get('total_amount', Decimal('0'))

        try:
            coupon = Coupon.objects.get(code=code)

            if not coupon.is_valid:
                return self.error_response(message='優惠券無效或已過期')

            if total_amount and total_amount < coupon.min_purchase:
                return self.error_response(
                    message=f'消費金額未達最低門檻 ${coupon.min_purchase}'
                )

            # Calculate discount
            if coupon.discount_type == 'PERCENTAGE':
                discount = total_amount * coupon.discount_value / 100
                if coupon.max_discount and discount > coupon.max_discount:
                    discount = coupon.max_discount
            else:
                discount = coupon.discount_value

            return self.success_response(
                message='優惠券有效',
                data={
                    'coupon': CouponSerializer(coupon).data,
                    'discount_amount': float(discount) if total_amount else None
                }
            )

        except Coupon.DoesNotExist:
            return self.error_response(message='找不到此優惠券')
