"""
Tests for core utility functions.
"""
import pytest
from decimal import Decimal
from apps.core.utils import (
    generate_order_number,
    generate_code,
    round_currency,
    calculate_tax,
    calculate_subtotal,
    mask_phone,
    mask_email,
    validate_taiwan_phone,
    validate_taiwan_tax_id,
)


class TestGenerateOrderNumber:
    """Tests for generate_order_number function."""

    def test_generate_order_number_default_prefix(self):
        """Test generating order number with default prefix."""
        order_number = generate_order_number()
        assert order_number.startswith('ORD')
        assert len(order_number) == 21  # ORD + 14 timestamp + 4 random

    def test_generate_order_number_custom_prefix(self):
        """Test generating order number with custom prefix."""
        order_number = generate_order_number('POS')
        assert order_number.startswith('POS')

    def test_generate_order_number_unique(self):
        """Test that generated order numbers are unique."""
        numbers = [generate_order_number() for _ in range(50)]
        assert len(numbers) == len(set(numbers))


class TestGenerateCode:
    """Tests for generate_code function."""

    def test_generate_code_default(self):
        """Test generating code with default settings."""
        code = generate_code()
        assert len(code) == 8
        assert code.isalnum()

    def test_generate_code_with_prefix(self):
        """Test generating code with prefix."""
        code = generate_code(prefix='SKU-')
        assert code.startswith('SKU-')
        assert len(code) == 12  # 4 prefix + 8 code

    def test_generate_code_custom_length(self):
        """Test generating code with custom length."""
        code = generate_code(length=12)
        assert len(code) == 12


class TestRoundCurrency:
    """Tests for round_currency function."""

    def test_round_currency_decimal(self):
        """Test rounding decimal to integer."""
        assert round_currency(Decimal('100.4')) == 100
        assert round_currency(Decimal('100.5')) == 101
        assert round_currency(Decimal('100.6')) == 101

    def test_round_currency_float(self):
        """Test rounding float to integer."""
        assert round_currency(99.4) == 99
        assert round_currency(99.5) == 100

    def test_round_currency_int(self):
        """Test with integer input."""
        assert round_currency(100) == 100


class TestCalculateTax:
    """Tests for calculate_tax function."""

    def test_calculate_tax_default_rate(self):
        """Test tax calculation with default 5% rate."""
        tax = calculate_tax(Decimal('1000'))
        assert tax == 50  # 1000 * 5% = 50

    def test_calculate_tax_custom_rate(self):
        """Test tax calculation with custom rate."""
        tax = calculate_tax(Decimal('1000'), tax_rate=10)
        assert tax == 100  # 1000 * 10% = 100

    def test_calculate_tax_with_float(self):
        """Test tax calculation with float input."""
        tax = calculate_tax(2000.0)
        assert tax == 100  # 2000 * 5% = 100

    def test_calculate_tax_rounding(self):
        """Test tax calculation rounding."""
        tax = calculate_tax(Decimal('999'))
        assert tax == 50  # 999 * 5% = 49.95, rounds to 50


class TestCalculateSubtotal:
    """Tests for calculate_subtotal function."""

    def test_calculate_subtotal_basic(self):
        """Test basic subtotal calculation."""
        subtotal = calculate_subtotal(2, 100)
        assert subtotal == 200

    def test_calculate_subtotal_with_discount(self):
        """Test subtotal calculation with discount."""
        subtotal = calculate_subtotal(2, 100, discount=50)
        assert subtotal == 150  # (2 * 100) - 50

    def test_calculate_subtotal_decimal_price(self):
        """Test subtotal with decimal prices."""
        subtotal = calculate_subtotal(3, Decimal('99.99'))
        assert subtotal == 300  # 299.97 rounds to 300


class TestMaskPhone:
    """Tests for mask_phone function."""

    def test_mask_phone_normal(self):
        """Test masking normal phone number."""
        masked = mask_phone('0912345678')
        assert masked == '0912****78'

    def test_mask_phone_short(self):
        """Test with short phone number."""
        assert mask_phone('12345') == '12345'

    def test_mask_phone_empty(self):
        """Test with empty phone."""
        assert mask_phone('') == ''
        assert mask_phone(None) is None


class TestMaskEmail:
    """Tests for mask_email function."""

    def test_mask_email_normal(self):
        """Test masking normal email."""
        masked = mask_email('test@example.com')
        assert masked == 't***@example.com'

    def test_mask_email_single_char_local(self):
        """Test with single character local part."""
        masked = mask_email('t@example.com')
        assert masked == 't@example.com'

    def test_mask_email_invalid(self):
        """Test with invalid email."""
        assert mask_email('invalid') == 'invalid'
        assert mask_email('') == ''
        assert mask_email(None) is None


class TestValidateTaiwanPhone:
    """Tests for validate_taiwan_phone function."""

    def test_valid_phone(self):
        """Test valid Taiwan phone numbers."""
        assert validate_taiwan_phone('0912345678') is True
        assert validate_taiwan_phone('0987654321') is True

    def test_invalid_phone_wrong_prefix(self):
        """Test phone with wrong prefix."""
        assert validate_taiwan_phone('0812345678') is False

    def test_invalid_phone_wrong_length(self):
        """Test phone with wrong length."""
        assert validate_taiwan_phone('091234567') is False  # 9 digits
        assert validate_taiwan_phone('09123456789') is False  # 11 digits

    def test_invalid_phone_non_digits(self):
        """Test phone with non-digit characters."""
        assert validate_taiwan_phone('09123456ab') is False


class TestValidateTaiwanTaxId:
    """Tests for validate_taiwan_tax_id function."""

    def test_valid_tax_ids(self):
        """Test valid Taiwan tax IDs."""
        # Some valid example tax IDs
        assert validate_taiwan_tax_id('04595257') is True  # 台積電
        assert validate_taiwan_tax_id('22099131') is True  # 鴻海

    def test_invalid_tax_id_wrong_length(self):
        """Test tax ID with wrong length."""
        assert validate_taiwan_tax_id('1234567') is False  # 7 digits
        assert validate_taiwan_tax_id('123456789') is False  # 9 digits

    def test_invalid_tax_id_non_digits(self):
        """Test tax ID with non-digit characters."""
        assert validate_taiwan_tax_id('1234567a') is False

    def test_invalid_tax_id_empty(self):
        """Test with empty tax ID."""
        assert validate_taiwan_tax_id('') is False
        assert validate_taiwan_tax_id(None) is False

    def test_invalid_tax_id_checksum(self):
        """Test tax ID with invalid checksum."""
        assert validate_taiwan_tax_id('12345678') is False
