"""
Tests for inventory services.
"""
import pytest
from decimal import Decimal
from apps.inventory.services import InventoryService
from apps.inventory.models import Inventory, InventoryMovement
from apps.core.exceptions import InsufficientStockError


@pytest.mark.django_db
class TestInventoryServiceAdjustStock:
    """Tests for InventoryService.adjust_stock method."""

    def test_adjust_stock_increase(self, warehouse, create_product, admin_user):
        """Test increasing stock."""
        product = create_product(name='測試商品', sku='INV001')

        inventory = InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            note='採購入庫',
            user=admin_user
        )

        assert inventory.quantity == 100
        assert inventory.available_quantity == 100

        # Check movement log was created
        movement = InventoryMovement.objects.get(
            warehouse_id=warehouse.id,
            product_id=product.id
        )
        assert movement.quantity == 100
        assert movement.movement_type == 'PURCHASE_IN'
        assert movement.balance == 100

    def test_adjust_stock_decrease(self, warehouse, create_product, admin_user):
        """Test decreasing stock."""
        product = create_product(name='測試商品', sku='INV002')

        # First add stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Then decrease
        inventory = InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=-30,
            movement_type='SALE_OUT',
            user=admin_user
        )

        assert inventory.quantity == 70
        assert inventory.available_quantity == 70

    def test_adjust_stock_insufficient(self, warehouse, create_product, admin_user):
        """Test decreasing stock when insufficient."""
        product = create_product(name='測試商品', sku='INV003')

        # Add some stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=10,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Try to decrease more than available
        with pytest.raises(InsufficientStockError):
            InventoryService.adjust_stock(
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=-20,
                movement_type='SALE_OUT',
                user=admin_user
            )

    def test_adjust_stock_creates_inventory_if_not_exists(self, warehouse, create_product, admin_user):
        """Test that inventory record is created if it doesn't exist."""
        product = create_product(name='新商品', sku='INV004')

        # Ensure no inventory exists
        assert not Inventory.objects.filter(
            warehouse_id=warehouse.id,
            product_id=product.id
        ).exists()

        inventory = InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        assert Inventory.objects.filter(
            warehouse_id=warehouse.id,
            product_id=product.id
        ).exists()
        assert inventory.quantity == 50

    def test_adjust_stock_with_reference(self, warehouse, create_product, admin_user):
        """Test adjust stock with reference info."""
        product = create_product(name='測試商品', sku='INV005')

        inventory = InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            reference_type='PurchaseOrder',
            reference_id=123,
            note='採購單 PO123 入庫',
            user=admin_user
        )

        movement = InventoryMovement.objects.get(
            warehouse_id=warehouse.id,
            product_id=product.id
        )
        assert movement.reference_type == 'PurchaseOrder'
        assert movement.reference_id == 123
        assert '採購單 PO123 入庫' in movement.note


@pytest.mark.django_db
class TestInventoryServiceReserveStock:
    """Tests for InventoryService.reserve_stock method."""

    def test_reserve_stock_success(self, warehouse, create_product, admin_user):
        """Test successful stock reservation."""
        product = create_product(name='測試商品', sku='RES001')

        # First add stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Reserve stock
        inventory = InventoryService.reserve_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
            user=admin_user
        )

        assert inventory.quantity == 100
        assert inventory.reserved_quantity == 30
        assert inventory.available_quantity == 70

    def test_reserve_stock_insufficient(self, warehouse, create_product, admin_user):
        """Test reserving more stock than available."""
        product = create_product(name='測試商品', sku='RES002')

        # Add some stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=10,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        # Try to reserve more than available
        with pytest.raises(InsufficientStockError):
            InventoryService.reserve_stock(
                warehouse_id=warehouse.id,
                product_id=product.id,
                quantity=20,
                user=admin_user
            )


@pytest.mark.django_db
class TestInventoryServiceReleaseStock:
    """Tests for InventoryService.release_stock method."""

    def test_release_stock_success(self, warehouse, create_product, admin_user):
        """Test successful stock release."""
        product = create_product(name='測試商品', sku='REL001')

        # Add and reserve stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )
        InventoryService.reserve_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
            user=admin_user
        )

        # Release reserved stock
        inventory = InventoryService.release_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=20,
            user=admin_user
        )

        assert inventory.quantity == 100
        assert inventory.reserved_quantity == 10
        assert inventory.available_quantity == 90

    def test_release_stock_more_than_reserved(self, warehouse, create_product, admin_user):
        """Test releasing more than reserved (should cap at 0)."""
        product = create_product(name='測試商品', sku='REL002')

        # Add and reserve stock
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=100,
            movement_type='PURCHASE_IN',
            user=admin_user
        )
        InventoryService.reserve_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=10,
            user=admin_user
        )

        # Release more than reserved
        inventory = InventoryService.release_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=50,  # More than reserved
            user=admin_user
        )

        assert inventory.reserved_quantity == 0
        assert inventory.available_quantity == 100


@pytest.mark.django_db
class TestInventoryServiceGetLowStockProducts:
    """Tests for InventoryService.get_low_stock_products method."""

    def test_get_low_stock_products(self, warehouse, create_product, admin_user):
        """Test getting low stock products."""
        # Create product with safety stock
        product = create_product(name='低庫存商品', sku='LOW001')
        product.safety_stock = 50
        product.save()

        # Add stock below safety level
        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        low_stock = InventoryService.get_low_stock_products()

        assert low_stock.filter(product_id=product.id).exists()

    def test_get_low_stock_products_filter_by_warehouse(self, warehouse, create_product, admin_user):
        """Test filtering low stock by warehouse."""
        product = create_product(name='低庫存商品', sku='LOW002')
        product.safety_stock = 50
        product.save()

        InventoryService.adjust_stock(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=30,
            movement_type='PURCHASE_IN',
            user=admin_user
        )

        low_stock = InventoryService.get_low_stock_products(warehouse_id=warehouse.id)

        assert low_stock.filter(
            product_id=product.id,
            warehouse_id=warehouse.id
        ).exists()
