"""
Inventory services.
"""
from django.db import transaction
from .models import Inventory, InventoryMovement
from apps.core.exceptions import InsufficientStockError


class InventoryService:
    """Inventory business logic service."""

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        warehouse_id,
        product_id,
        quantity,
        movement_type,
        reference_type='',
        reference_id=None,
        note='',
        user=None
    ):
        """
        Adjust inventory stock and create movement log.
        Positive quantity = increase, negative = decrease.
        """
        inventory, created = Inventory.objects.select_for_update().get_or_create(
            warehouse_id=warehouse_id,
            product_id=product_id,
            defaults={
                'quantity': 0,
                'available_quantity': 0,
                'created_by': user
            }
        )

        # Check if we have enough stock for decrease
        if quantity < 0 and inventory.available_quantity < abs(quantity):
            from apps.products.models import Product
            product = Product.objects.get(id=product_id)
            raise InsufficientStockError(
                product_name=product.name,
                required=abs(quantity),
                available=inventory.available_quantity
            )

        # Update inventory
        inventory.quantity += quantity
        inventory.available_quantity = inventory.quantity - inventory.reserved_quantity
        inventory.updated_by = user
        inventory.save()

        # Create movement log
        InventoryMovement.objects.create(
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type=movement_type,
            quantity=quantity,
            balance=inventory.quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
            created_by=user
        )

        return inventory

    @staticmethod
    @transaction.atomic
    def reserve_stock(warehouse_id, product_id, quantity, user=None):
        """Reserve stock for an order."""
        inventory = Inventory.objects.select_for_update().get(
            warehouse_id=warehouse_id,
            product_id=product_id
        )

        if inventory.available_quantity < quantity:
            from apps.products.models import Product
            product = Product.objects.get(id=product_id)
            raise InsufficientStockError(
                product_name=product.name,
                required=quantity,
                available=inventory.available_quantity
            )

        inventory.reserved_quantity += quantity
        inventory.available_quantity = inventory.quantity - inventory.reserved_quantity
        inventory.updated_by = user
        inventory.save()

        return inventory

    @staticmethod
    @transaction.atomic
    def release_stock(warehouse_id, product_id, quantity, user=None):
        """Release reserved stock."""
        inventory = Inventory.objects.select_for_update().get(
            warehouse_id=warehouse_id,
            product_id=product_id
        )

        inventory.reserved_quantity = max(0, inventory.reserved_quantity - quantity)
        inventory.available_quantity = inventory.quantity - inventory.reserved_quantity
        inventory.updated_by = user
        inventory.save()

        return inventory

    @staticmethod
    def get_low_stock_products(warehouse_id=None):
        """Get products with stock below safety level."""
        from django.db.models import F

        queryset = Inventory.objects.select_related('product', 'warehouse').filter(
            quantity__lte=F('product__safety_stock'),
            product__status='ACTIVE'
        )

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        return queryset
