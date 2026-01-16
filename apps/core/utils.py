"""
Utility functions for the application.
"""
import random
import string
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def generate_order_number(prefix='ORD'):
    """
    Generate a unique order number.
    Format: {prefix}YYYYMMDDHHmmss{random 4 digits}
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f'{prefix}{timestamp}{random_suffix}'


def generate_code(prefix='', length=8):
    """
    Generate a random code with optional prefix.
    """
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=length))
    return f'{prefix}{code}' if prefix else code


def round_currency(amount):
    """
    Round currency amount to integer (Taiwan uses whole numbers).
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    return int(amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def calculate_tax(amount, tax_rate=5):
    """
    Calculate tax amount.
    Default tax rate is 5% (Taiwan business tax).
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    tax_rate_decimal = Decimal(str(tax_rate)) / Decimal('100')
    tax_amount = amount * tax_rate_decimal
    return round_currency(tax_amount)


def calculate_subtotal(quantity, unit_price, discount=0):
    """
    Calculate subtotal: (quantity * unit_price) - discount
    """
    subtotal = Decimal(str(quantity)) * Decimal(str(unit_price))
    if discount:
        subtotal -= Decimal(str(discount))
    return round_currency(subtotal)


def mask_phone(phone):
    """
    Mask phone number: 0912****78
    """
    if not phone or len(phone) < 6:
        return phone
    return f'{phone[:4]}****{phone[-2:]}'


def mask_email(email):
    """
    Mask email: t***@example.com
    """
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        return email
    return f'{local[0]}***@{domain}'


def validate_taiwan_phone(phone):
    """
    Validate Taiwan phone number format.
    Valid formats: 09XXXXXXXX (10 digits starting with 09)
    """
    import re
    pattern = r'^09\d{8}$'
    return bool(re.match(pattern, phone))


def validate_taiwan_tax_id(tax_id):
    """
    Validate Taiwan business tax ID (統一編號).
    8-digit number with check digit validation.
    """
    if not tax_id or len(tax_id) != 8 or not tax_id.isdigit():
        return False

    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    total = 0

    for i, digit in enumerate(tax_id):
        product = int(digit) * weights[i]
        total += product // 10 + product % 10

    if tax_id[6] == '7':
        return total % 10 == 0 or (total + 1) % 10 == 0

    return total % 10 == 0
