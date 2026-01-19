"""
Tests for promotions views.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from datetime import timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestPromotionViewSet:
    """Tests for PromotionViewSet."""

    def test_list_promotions(self, admin_client, db):
        """Test listing promotions."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='Summer Sale',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now,
            end_date=now + timedelta(days=30),
            is_active=True
        )

        response = admin_client.get('/api/v1/promotions/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_promotions_unauthenticated(self, api_client):
        """Test listing promotions without authentication."""
        response = api_client.get('/api/v1/promotions/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_promotion_detail(self, admin_client, db):
        """Test getting promotion detail."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        promo = Promotion.objects.create(
            name='Winter Sale',
            promotion_type='FIXED',
            discount_value=Decimal('100'),
            start_date=now,
            end_date=now + timedelta(days=15),
            is_active=True
        )

        response = admin_client.get(f'/api/v1/promotions/{promo.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Winter Sale'

    def test_create_promotion(self, admin_client):
        """Test creating a promotion."""
        now = timezone.now()
        data = {
            'name': 'New Year Sale',
            'promotion_type': 'PERCENTAGE',
            'discount_value': '15.00',
            'start_date': now.isoformat(),
            'end_date': (now + timedelta(days=10)).isoformat(),
            'is_active': True
        }

        response = admin_client.post('/api/v1/promotions/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Year Sale'

    def test_update_promotion(self, admin_client, db):
        """Test updating a promotion."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        promo = Promotion.objects.create(
            name='Old Promo',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('5'),
            start_date=now,
            end_date=now + timedelta(days=7),
            is_active=True
        )

        data = {
            'name': 'Updated Promo',
            'promotion_type': 'PERCENTAGE',
            'discount_value': '10.00',
            'start_date': promo.start_date.isoformat(),
            'end_date': promo.end_date.isoformat(),
            'is_active': True
        }

        response = admin_client.put(f'/api/v1/promotions/{promo.id}/', data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Promo'

    def test_delete_promotion(self, admin_client, db):
        """Test deleting a promotion."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        promo = Promotion.objects.create(
            name='To Delete',
            promotion_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now,
            end_date=now + timedelta(days=5),
            is_active=False
        )

        response = admin_client.delete(f'/api/v1/promotions/{promo.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_promotions_by_is_active(self, admin_client, db):
        """Test filtering promotions by is_active."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='Active Promo',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('20'),
            start_date=now,
            end_date=now + timedelta(days=20),
            is_active=True
        )

        response = admin_client.get('/api/v1/promotions/?is_active=true')

        assert response.status_code == status.HTTP_200_OK

    def test_get_active_promotions(self, admin_client, db):
        """Test getting currently active promotions."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        # Create active promotion
        Promotion.objects.create(
            name='Active Now',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('15'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            is_active=True
        )
        # Create expired promotion
        Promotion.objects.create(
            name='Expired',
            promotion_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=1),
            is_active=True
        )
        # Create future promotion
        Promotion.objects.create(
            name='Future',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('20'),
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=30),
            is_active=True
        )

        response = admin_client.get('/api/v1/promotions/active/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        # Should only return the active promotion
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['name'] == 'Active Now'

    def test_calculate_discount_percentage(self, admin_client, db):
        """Test calculating percentage discount."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='10% Off',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            is_active=True,
            min_purchase=Decimal('0')
        )

        data = {
            'items': [
                {'product_id': 1, 'quantity': 2, 'unit_price': '100.00'}
            ]
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['subtotal'] == 200.0
        assert response.data['data']['total_discount'] == 20.0  # 10% of 200
        assert response.data['data']['final_amount'] == 180.0

    def test_calculate_discount_fixed(self, admin_client, db):
        """Test calculating fixed discount."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='$50 Off',
            promotion_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            is_active=True,
            min_purchase=Decimal('0')
        )

        data = {
            'items': [
                {'product_id': 1, 'quantity': 1, 'unit_price': '200.00'}
            ]
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subtotal'] == 200.0
        assert response.data['data']['total_discount'] == 50.0
        assert response.data['data']['final_amount'] == 150.0

    def test_calculate_discount_min_purchase_not_met(self, admin_client, db):
        """Test discount not applied when min purchase not met."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='Big Spender',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('20'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            is_active=True,
            min_purchase=Decimal('500')
        )

        data = {
            'items': [
                {'product_id': 1, 'quantity': 1, 'unit_price': '100.00'}
            ]
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subtotal'] == 100.0
        assert response.data['data']['total_discount'] == 0  # Min purchase not met
        assert response.data['data']['final_amount'] == 100.0

    def test_calculate_discount_with_coupon(self, admin_client, db):
        """Test calculating discount with coupon code."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='SAVE50',
            name='Save $50',
            discount_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('0')
        )

        data = {
            'items': [
                {'product_id': 1, 'quantity': 2, 'unit_price': '100.00'}
            ],
            'coupon_code': 'SAVE50'
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subtotal'] == 200.0
        assert response.data['data']['total_discount'] == 50.0

    def test_calculate_discount_with_percentage_coupon(self, admin_client, db):
        """Test calculating discount with percentage coupon."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='PERCENT20',
            name='20% Off',
            discount_type='PERCENTAGE',
            discount_value=Decimal('20'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('0'),
            max_discount=Decimal('100')
        )

        data = {
            'items': [
                {'product_id': 1, 'quantity': 5, 'unit_price': '100.00'}
            ],
            'coupon_code': 'PERCENT20'
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['subtotal'] == 500.0
        # 20% of 500 = 100, which equals max_discount
        assert response.data['data']['total_discount'] == 100.0

    def test_calculate_discount_invalid_coupon(self, admin_client, db):
        """Test calculating discount with invalid coupon code."""
        data = {
            'items': [
                {'product_id': 1, 'quantity': 1, 'unit_price': '100.00'}
            ],
            'coupon_code': 'INVALID'
        }

        response = admin_client.post('/api/v1/promotions/calculate/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Invalid coupon is ignored, no discount applied
        assert response.data['data']['total_discount'] == 0

    def test_search_promotions(self, admin_client, db):
        """Test searching promotions by name."""
        from apps.promotions.models import Promotion

        now = timezone.now()
        Promotion.objects.create(
            name='Searchable Promo',
            promotion_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now,
            end_date=now + timedelta(days=30),
            is_active=True
        )

        response = admin_client.get('/api/v1/promotions/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCouponViewSet:
    """Tests for CouponViewSet."""

    def test_list_coupons(self, admin_client, db):
        """Test listing coupons."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='SAVE10',
            name='Save 10%',
            discount_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now,
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE'
        )

        response = admin_client.get('/api/v1/coupons/')

        assert response.status_code == status.HTTP_200_OK

    def test_get_coupon_detail(self, admin_client, db):
        """Test getting coupon detail."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        coupon = Coupon.objects.create(
            code='SAVE20',
            name='Save 20%',
            discount_type='FIXED',
            discount_value=Decimal('200'),
            start_date=now,
            end_date=now + timedelta(days=14),
            usage_limit=50,
            status='ACTIVE'
        )

        response = admin_client.get(f'/api/v1/coupons/{coupon.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 'SAVE20'

    def test_create_coupon(self, admin_client):
        """Test creating a coupon."""
        now = timezone.now()
        data = {
            'code': 'NEWCODE',
            'name': 'New Coupon',
            'discount_type': 'PERCENTAGE',
            'discount_value': '15.00',
            'start_date': now.isoformat(),
            'end_date': (now + timedelta(days=30)).isoformat(),
            'usage_limit': 200,
            'status': 'ACTIVE'
        }

        response = admin_client.post('/api/v1/coupons/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 'NEWCODE'

    def test_update_coupon(self, admin_client, db):
        """Test updating a coupon."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        coupon = Coupon.objects.create(
            code='OLDCODE',
            name='Old Coupon',
            discount_type='PERCENTAGE',
            discount_value=Decimal('5'),
            start_date=now,
            end_date=now + timedelta(days=7),
            usage_limit=10,
            status='ACTIVE'
        )

        data = {
            'code': 'OLDCODE',
            'name': 'Updated Coupon',
            'discount_type': 'PERCENTAGE',
            'discount_value': '10.00',
            'start_date': coupon.start_date.isoformat(),
            'end_date': coupon.end_date.isoformat(),
            'usage_limit': 100,
            'status': 'ACTIVE'
        }

        response = admin_client.put(f'/api/v1/coupons/{coupon.id}/', data)

        assert response.status_code == status.HTTP_200_OK

    def test_delete_coupon(self, admin_client, db):
        """Test deleting a coupon."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TODELETE',
            name='To Delete',
            discount_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now,
            end_date=now + timedelta(days=5),
            usage_limit=5,
            status='ACTIVE'
        )

        response = admin_client.delete(f'/api/v1/coupons/{coupon.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_validate_coupon(self, admin_client, db):
        """Test validating a coupon code."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='VALID100',
            name='Valid Coupon',
            discount_type='FIXED',
            discount_value=Decimal('100'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE'
        )

        response = admin_client.post('/api/v1/coupons/validate/', {'code': 'VALID100'})

        assert response.status_code == status.HTTP_200_OK

    def test_validate_invalid_coupon(self, admin_client, db):
        """Test validating an invalid coupon code."""
        response = admin_client.post('/api/v1/coupons/validate/', {'code': 'INVALID'})

        # API returns 400 with error message when coupon is not found
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_expired_coupon(self, admin_client, db):
        """Test validating an expired coupon."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='EXPIRED',
            name='Expired Coupon',
            discount_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now - timedelta(days=30),
            end_date=now - timedelta(days=1),
            usage_limit=100,
            status='ACTIVE'
        )

        response = admin_client.post('/api/v1/coupons/validate/', {'code': 'EXPIRED'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_coupons_by_status(self, admin_client, db):
        """Test filtering coupons by status."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='ACTIVE1',
            name='Active Coupon',
            discount_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now,
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE'
        )

        response = admin_client.get('/api/v1/coupons/?status=ACTIVE')

        assert response.status_code == status.HTTP_200_OK

    def test_validate_coupon_with_amount(self, admin_client, db):
        """Test validating a coupon with total amount."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='PERCENT15',
            name='15% Off',
            discount_type='PERCENTAGE',
            discount_value=Decimal('15'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('0')
        )

        response = admin_client.post(
            '/api/v1/coupons/validate/',
            {'code': 'PERCENT15', 'total_amount': '200.00'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['discount_amount'] == 30.0  # 15% of 200

    def test_validate_coupon_min_purchase_not_met(self, admin_client, db):
        """Test validating a coupon when min purchase not met."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='BIGSPENDER',
            name='Big Spender Discount',
            discount_type='FIXED',
            discount_value=Decimal('100'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('500')
        )

        response = admin_client.post(
            '/api/v1/coupons/validate/',
            {'code': 'BIGSPENDER', 'total_amount': '100.00'}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_coupon_with_max_discount(self, admin_client, db):
        """Test validating a percentage coupon with max discount limit."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='MAXCAP',
            name='Capped Discount',
            discount_type='PERCENTAGE',
            discount_value=Decimal('50'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('0'),
            max_discount=Decimal('50')
        )

        response = admin_client.post(
            '/api/v1/coupons/validate/',
            {'code': 'MAXCAP', 'total_amount': '200.00'}
        )

        assert response.status_code == status.HTTP_200_OK
        # 50% of 200 = 100, but max is 50
        assert response.data['data']['discount_amount'] == 50.0

    def test_validate_fixed_coupon_with_amount(self, admin_client, db):
        """Test validating a fixed amount coupon."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='FIXED50',
            name='$50 Off',
            discount_type='FIXED',
            discount_value=Decimal('50'),
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE',
            min_purchase=Decimal('0')
        )

        response = admin_client.post(
            '/api/v1/coupons/validate/',
            {'code': 'FIXED50', 'total_amount': '200.00'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['discount_amount'] == 50.0

    def test_search_coupons(self, admin_client, db):
        """Test searching coupons."""
        from apps.promotions.models import Coupon

        now = timezone.now()
        Coupon.objects.create(
            code='SEARCHME',
            name='Searchable Coupon',
            discount_type='PERCENTAGE',
            discount_value=Decimal('10'),
            start_date=now,
            end_date=now + timedelta(days=30),
            usage_limit=100,
            status='ACTIVE'
        )

        response = admin_client.get('/api/v1/coupons/?search=Searchable')

        assert response.status_code == status.HTTP_200_OK
