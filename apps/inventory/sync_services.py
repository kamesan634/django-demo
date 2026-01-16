"""
Inventory synchronization services.
F05-010: 庫存同步機制
Provides real-time inventory sync across warehouses using Redis.
"""
import json
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from django.db import transaction
from django.db.models import F, Sum
from django.core.cache import cache
from django.conf import settings

from apps.core.redis_services import (
    DistributedLockService,
    CacheService,
    NotificationService,
)

logger = logging.getLogger(__name__)

# Cache keys
INVENTORY_CACHE_KEY = 'inventory:{warehouse_id}:{product_id}'
INVENTORY_SUMMARY_KEY = 'inventory:summary:{product_id}'
WAREHOUSE_INVENTORY_KEY = 'warehouse:inventory:{warehouse_id}'
LOW_STOCK_ALERT_KEY = 'inventory:low_stock:{warehouse_id}'
INVENTORY_VERSION_KEY = 'inventory:version:{warehouse_id}:{product_id}'


@dataclass
class InventoryChange:
    """Represents an inventory change event."""
    warehouse_id: int
    product_id: int
    change_type: str  # 'UPDATE', 'RESERVE', 'RELEASE', 'TRANSFER'
    quantity_change: int
    new_quantity: int
    new_available: int
    reference_type: str = ''
    reference_id: Optional[int] = None
    timestamp: str = ''
    user_id: Optional[int] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class InventorySyncService:
    """
    Inventory synchronization service.
    Provides real-time inventory sync using Redis cache and pub/sub.
    """

    # Notification channels
    INVENTORY_CHANNEL = 'inventory:updates'
    LOW_STOCK_CHANNEL = 'inventory:low_stock'
    TRANSFER_CHANNEL = 'inventory:transfer'

    # Cache TTL (seconds)
    INVENTORY_CACHE_TTL = 300  # 5 minutes
    SUMMARY_CACHE_TTL = 600  # 10 minutes
    VERSION_TTL = 86400  # 1 day

    @classmethod
    def get_inventory_lock_key(cls, warehouse_id: int, product_id: int) -> str:
        """Get lock key for inventory item."""
        return f'inventory:lock:{warehouse_id}:{product_id}'

    @classmethod
    def get_cached_inventory(
        cls,
        warehouse_id: int,
        product_id: int
    ) -> Optional[Dict]:
        """
        Get cached inventory data.
        Returns None if not cached.
        """
        cache_key = INVENTORY_CACHE_KEY.format(
            warehouse_id=warehouse_id,
            product_id=product_id
        )
        return CacheService.get(cache_key)

    @classmethod
    def set_cached_inventory(
        cls,
        warehouse_id: int,
        product_id: int,
        data: Dict,
        ttl: int = None
    ) -> None:
        """Cache inventory data."""
        cache_key = INVENTORY_CACHE_KEY.format(
            warehouse_id=warehouse_id,
            product_id=product_id
        )
        CacheService.set(cache_key, data, ttl or cls.INVENTORY_CACHE_TTL)

    @classmethod
    def invalidate_inventory_cache(
        cls,
        warehouse_id: int,
        product_id: int
    ) -> None:
        """Invalidate inventory cache for a specific item."""
        cache_key = INVENTORY_CACHE_KEY.format(
            warehouse_id=warehouse_id,
            product_id=product_id
        )
        CacheService.delete(cache_key)

        # Also invalidate summary cache
        summary_key = INVENTORY_SUMMARY_KEY.format(product_id=product_id)
        CacheService.delete(summary_key)

    @classmethod
    @transaction.atomic
    def sync_update_inventory(
        cls,
        warehouse_id: int,
        product_id: int,
        quantity_change: int,
        movement_type: str,
        reference_type: str = '',
        reference_id: int = None,
        note: str = '',
        user=None
    ) -> Dict:
        """
        Synchronized inventory update with distributed locking.
        Ensures consistency across distributed systems.
        """
        from .models import Inventory, InventoryMovement
        from apps.core.exceptions import InsufficientStockError

        lock_key = cls.get_inventory_lock_key(warehouse_id, product_id)

        with DistributedLockService.distributed_lock(
            lock_key,
            timeout=30,
            blocking_timeout=10
        ):
            # Get or create inventory record with row lock
            inventory, created = Inventory.objects.select_for_update().get_or_create(
                warehouse_id=warehouse_id,
                product_id=product_id,
                defaults={
                    'quantity': 0,
                    'available_quantity': 0,
                    'reserved_quantity': 0,
                    'created_by': user
                }
            )

            # Check stock for decrease
            if quantity_change < 0:
                if inventory.available_quantity < abs(quantity_change):
                    from apps.products.models import Product
                    product = Product.objects.get(id=product_id)
                    raise InsufficientStockError(
                        product_name=product.name,
                        required=abs(quantity_change),
                        available=inventory.available_quantity
                    )

            # Update inventory
            old_quantity = inventory.quantity
            inventory.quantity = F('quantity') + quantity_change
            inventory.updated_by = user
            inventory.save()
            inventory.refresh_from_db()

            # Create movement record
            movement = InventoryMovement.objects.create(
                warehouse_id=warehouse_id,
                product_id=product_id,
                movement_type=movement_type,
                quantity=quantity_change,
                balance=inventory.quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                note=note,
                created_by=user
            )

            # Create change event
            change = InventoryChange(
                warehouse_id=warehouse_id,
                product_id=product_id,
                change_type='UPDATE',
                quantity_change=quantity_change,
                new_quantity=inventory.quantity,
                new_available=inventory.available_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user.id if user else None
            )

            # Update cache and notify
            cls._update_cache_and_notify(inventory, change)

            # Check for low stock alert
            cls._check_low_stock_alert(inventory)

            return {
                'inventory_id': inventory.id,
                'warehouse_id': warehouse_id,
                'product_id': product_id,
                'old_quantity': old_quantity,
                'new_quantity': inventory.quantity,
                'available_quantity': inventory.available_quantity,
                'movement_id': movement.id
            }

    @classmethod
    @transaction.atomic
    def sync_reserve_stock(
        cls,
        warehouse_id: int,
        product_id: int,
        quantity: int,
        reference_type: str = '',
        reference_id: int = None,
        user=None
    ) -> Dict:
        """
        Reserve stock with distributed locking.
        Used when creating orders before actual stock deduction.
        """
        from .models import Inventory
        from apps.core.exceptions import InsufficientStockError

        lock_key = cls.get_inventory_lock_key(warehouse_id, product_id)

        with DistributedLockService.distributed_lock(
            lock_key,
            timeout=30,
            blocking_timeout=10
        ):
            try:
                inventory = Inventory.objects.select_for_update().get(
                    warehouse_id=warehouse_id,
                    product_id=product_id
                )
            except Inventory.DoesNotExist:
                from apps.products.models import Product
                product = Product.objects.get(id=product_id)
                raise InsufficientStockError(
                    product_name=product.name,
                    required=quantity,
                    available=0
                )

            if inventory.available_quantity < quantity:
                from apps.products.models import Product
                product = Product.objects.get(id=product_id)
                raise InsufficientStockError(
                    product_name=product.name,
                    required=quantity,
                    available=inventory.available_quantity
                )

            # Reserve stock
            old_reserved = inventory.reserved_quantity
            inventory.reserved_quantity = F('reserved_quantity') + quantity
            inventory.updated_by = user
            inventory.save()
            inventory.refresh_from_db()

            # Create change event
            change = InventoryChange(
                warehouse_id=warehouse_id,
                product_id=product_id,
                change_type='RESERVE',
                quantity_change=quantity,
                new_quantity=inventory.quantity,
                new_available=inventory.available_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user.id if user else None
            )

            # Update cache and notify
            cls._update_cache_and_notify(inventory, change)

            return {
                'inventory_id': inventory.id,
                'warehouse_id': warehouse_id,
                'product_id': product_id,
                'old_reserved': old_reserved,
                'new_reserved': inventory.reserved_quantity,
                'available_quantity': inventory.available_quantity
            }

    @classmethod
    @transaction.atomic
    def sync_release_stock(
        cls,
        warehouse_id: int,
        product_id: int,
        quantity: int,
        reference_type: str = '',
        reference_id: int = None,
        user=None
    ) -> Dict:
        """
        Release reserved stock with distributed locking.
        Used when cancelling orders or after stock deduction.
        """
        from .models import Inventory

        lock_key = cls.get_inventory_lock_key(warehouse_id, product_id)

        with DistributedLockService.distributed_lock(
            lock_key,
            timeout=30,
            blocking_timeout=10
        ):
            inventory = Inventory.objects.select_for_update().get(
                warehouse_id=warehouse_id,
                product_id=product_id
            )

            # Release stock (don't go below 0)
            old_reserved = inventory.reserved_quantity
            release_amount = min(quantity, inventory.reserved_quantity)
            inventory.reserved_quantity = F('reserved_quantity') - release_amount
            inventory.updated_by = user
            inventory.save()
            inventory.refresh_from_db()

            # Create change event
            change = InventoryChange(
                warehouse_id=warehouse_id,
                product_id=product_id,
                change_type='RELEASE',
                quantity_change=-release_amount,
                new_quantity=inventory.quantity,
                new_available=inventory.available_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user.id if user else None
            )

            # Update cache and notify
            cls._update_cache_and_notify(inventory, change)

            return {
                'inventory_id': inventory.id,
                'warehouse_id': warehouse_id,
                'product_id': product_id,
                'old_reserved': old_reserved,
                'new_reserved': inventory.reserved_quantity,
                'released_quantity': release_amount,
                'available_quantity': inventory.available_quantity
            }

    @classmethod
    @transaction.atomic
    def sync_transfer_stock(
        cls,
        from_warehouse_id: int,
        to_warehouse_id: int,
        product_id: int,
        quantity: int,
        transfer_id: int = None,
        user=None
    ) -> Dict:
        """
        Transfer stock between warehouses with distributed locking.
        Locks both source and destination to prevent deadlocks.
        """
        from .models import Inventory, InventoryMovement
        from apps.core.exceptions import InsufficientStockError

        # Always lock in consistent order to prevent deadlocks
        warehouses = sorted([from_warehouse_id, to_warehouse_id])
        lock_key_1 = cls.get_inventory_lock_key(warehouses[0], product_id)
        lock_key_2 = cls.get_inventory_lock_key(warehouses[1], product_id)

        with DistributedLockService.distributed_lock(lock_key_1, timeout=30):
            with DistributedLockService.distributed_lock(lock_key_2, timeout=30):
                # Get source inventory
                try:
                    from_inventory = Inventory.objects.select_for_update().get(
                        warehouse_id=from_warehouse_id,
                        product_id=product_id
                    )
                except Inventory.DoesNotExist:
                    from apps.products.models import Product
                    product = Product.objects.get(id=product_id)
                    raise InsufficientStockError(
                        product_name=product.name,
                        required=quantity,
                        available=0
                    )

                if from_inventory.available_quantity < quantity:
                    from apps.products.models import Product
                    product = Product.objects.get(id=product_id)
                    raise InsufficientStockError(
                        product_name=product.name,
                        required=quantity,
                        available=from_inventory.available_quantity
                    )

                # Get or create destination inventory
                to_inventory, created = Inventory.objects.select_for_update().get_or_create(
                    warehouse_id=to_warehouse_id,
                    product_id=product_id,
                    defaults={
                        'quantity': 0,
                        'available_quantity': 0,
                        'reserved_quantity': 0,
                        'created_by': user
                    }
                )

                # Decrease source
                from_inventory.quantity = F('quantity') - quantity
                from_inventory.updated_by = user
                from_inventory.save()
                from_inventory.refresh_from_db()

                # Increase destination
                to_inventory.quantity = F('quantity') + quantity
                to_inventory.updated_by = user
                to_inventory.save()
                to_inventory.refresh_from_db()

                # Create movement records
                InventoryMovement.objects.create(
                    warehouse_id=from_warehouse_id,
                    product_id=product_id,
                    movement_type='TRANSFER_OUT',
                    quantity=-quantity,
                    balance=from_inventory.quantity,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    note=f'調撥至倉庫 {to_warehouse_id}',
                    created_by=user
                )

                InventoryMovement.objects.create(
                    warehouse_id=to_warehouse_id,
                    product_id=product_id,
                    movement_type='TRANSFER_IN',
                    quantity=quantity,
                    balance=to_inventory.quantity,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    note=f'自倉庫 {from_warehouse_id} 調撥入庫',
                    created_by=user
                )

                # Create change events and notify
                from_change = InventoryChange(
                    warehouse_id=from_warehouse_id,
                    product_id=product_id,
                    change_type='TRANSFER',
                    quantity_change=-quantity,
                    new_quantity=from_inventory.quantity,
                    new_available=from_inventory.available_quantity,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    user_id=user.id if user else None
                )

                to_change = InventoryChange(
                    warehouse_id=to_warehouse_id,
                    product_id=product_id,
                    change_type='TRANSFER',
                    quantity_change=quantity,
                    new_quantity=to_inventory.quantity,
                    new_available=to_inventory.available_quantity,
                    reference_type='StockTransfer',
                    reference_id=transfer_id,
                    user_id=user.id if user else None
                )

                cls._update_cache_and_notify(from_inventory, from_change)
                cls._update_cache_and_notify(to_inventory, to_change)

                # Check low stock alerts
                cls._check_low_stock_alert(from_inventory)
                cls._check_low_stock_alert(to_inventory)

                # Publish transfer event
                NotificationService.publish(
                    cls.TRANSFER_CHANNEL,
                    {
                        'transfer_id': transfer_id,
                        'from_warehouse_id': from_warehouse_id,
                        'to_warehouse_id': to_warehouse_id,
                        'product_id': product_id,
                        'quantity': quantity,
                        'timestamp': datetime.now().isoformat()
                    }
                )

                return {
                    'from_warehouse': {
                        'warehouse_id': from_warehouse_id,
                        'new_quantity': from_inventory.quantity,
                        'available_quantity': from_inventory.available_quantity
                    },
                    'to_warehouse': {
                        'warehouse_id': to_warehouse_id,
                        'new_quantity': to_inventory.quantity,
                        'available_quantity': to_inventory.available_quantity
                    },
                    'transfer_quantity': quantity
                }

    @classmethod
    def _update_cache_and_notify(cls, inventory, change: InventoryChange) -> None:
        """Update cache and publish notification."""
        # Prepare cache data
        cache_data = {
            'id': inventory.id,
            'warehouse_id': inventory.warehouse_id,
            'product_id': inventory.product_id,
            'quantity': inventory.quantity,
            'available_quantity': inventory.available_quantity,
            'reserved_quantity': inventory.reserved_quantity,
            'updated_at': datetime.now().isoformat()
        }

        # Update cache
        cls.set_cached_inventory(
            inventory.warehouse_id,
            inventory.product_id,
            cache_data
        )

        # Increment version
        version_key = INVENTORY_VERSION_KEY.format(
            warehouse_id=inventory.warehouse_id,
            product_id=inventory.product_id
        )
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection('default')
            redis.incr(version_key)
            redis.expire(version_key, cls.VERSION_TTL)
        except Exception as e:
            logger.warning(f'Failed to increment inventory version: {e}')

        # Publish change notification
        NotificationService.publish(
            cls.INVENTORY_CHANNEL,
            asdict(change)
        )

    @classmethod
    def _check_low_stock_alert(cls, inventory) -> None:
        """Check if inventory is below safety stock and send alert."""
        try:
            from apps.products.models import Product
            product = Product.objects.get(id=inventory.product_id)
            safety_stock = getattr(product, 'safety_stock', 0) or 0

            if safety_stock > 0 and inventory.quantity <= safety_stock:
                # Determine alert level
                if inventory.quantity == 0:
                    level = 'OUT_OF_STOCK'
                elif inventory.quantity <= safety_stock * 0.25:
                    level = 'CRITICAL'
                elif inventory.quantity <= safety_stock * 0.5:
                    level = 'WARNING'
                else:
                    level = 'LOW'

                alert_data = {
                    'warehouse_id': inventory.warehouse_id,
                    'product_id': inventory.product_id,
                    'product_name': product.name,
                    'current_quantity': inventory.quantity,
                    'safety_stock': safety_stock,
                    'shortage': safety_stock - inventory.quantity,
                    'alert_level': level,
                    'timestamp': datetime.now().isoformat()
                }

                # Cache low stock alert
                cache_key = LOW_STOCK_ALERT_KEY.format(
                    warehouse_id=inventory.warehouse_id
                )
                try:
                    existing = CacheService.get(cache_key) or {}
                    existing[str(inventory.product_id)] = alert_data
                    CacheService.set(cache_key, existing, 3600)  # 1 hour
                except Exception as e:
                    logger.warning(f'Failed to cache low stock alert: {e}')

                # Publish alert
                NotificationService.publish(
                    cls.LOW_STOCK_CHANNEL,
                    alert_data
                )

        except Exception as e:
            logger.error(f'Error checking low stock alert: {e}')

    @classmethod
    def get_product_inventory_summary(cls, product_id: int) -> Dict:
        """
        Get inventory summary for a product across all warehouses.
        Uses cache when available.
        """
        cache_key = INVENTORY_SUMMARY_KEY.format(product_id=product_id)
        cached = CacheService.get(cache_key)

        if cached:
            return cached

        from .models import Inventory
        from apps.stores.models import Warehouse

        inventories = Inventory.objects.filter(
            product_id=product_id
        ).select_related('warehouse')

        summary = {
            'product_id': product_id,
            'total_quantity': 0,
            'total_available': 0,
            'total_reserved': 0,
            'warehouses': []
        }

        for inv in inventories:
            summary['total_quantity'] += inv.quantity
            summary['total_available'] += inv.available_quantity
            summary['total_reserved'] += inv.reserved_quantity
            summary['warehouses'].append({
                'warehouse_id': inv.warehouse_id,
                'warehouse_name': inv.warehouse.name,
                'quantity': inv.quantity,
                'available_quantity': inv.available_quantity,
                'reserved_quantity': inv.reserved_quantity
            })

        CacheService.set(cache_key, summary, cls.SUMMARY_CACHE_TTL)
        return summary

    @classmethod
    def get_low_stock_alerts(
        cls,
        warehouse_id: int = None
    ) -> List[Dict]:
        """Get all low stock alerts, optionally filtered by warehouse."""
        from .models import Inventory
        from apps.products.models import Product

        queryset = Inventory.objects.select_related(
            'product', 'warehouse'
        ).filter(
            quantity__lte=F('product__safety_stock'),
            product__status='ACTIVE'
        )

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        alerts = []
        for inv in queryset:
            safety_stock = inv.product.safety_stock or 0
            if safety_stock == 0:
                continue

            if inv.quantity == 0:
                level = 'OUT_OF_STOCK'
            elif inv.quantity <= safety_stock * 0.25:
                level = 'CRITICAL'
            elif inv.quantity <= safety_stock * 0.5:
                level = 'WARNING'
            else:
                level = 'LOW'

            alerts.append({
                'warehouse_id': inv.warehouse_id,
                'warehouse_name': inv.warehouse.name,
                'product_id': inv.product_id,
                'product_name': inv.product.name,
                'product_sku': inv.product.sku,
                'current_quantity': inv.quantity,
                'available_quantity': inv.available_quantity,
                'safety_stock': safety_stock,
                'shortage': safety_stock - inv.quantity,
                'alert_level': level
            })

        # Sort by severity
        level_order = {'OUT_OF_STOCK': 0, 'CRITICAL': 1, 'WARNING': 2, 'LOW': 3}
        alerts.sort(key=lambda x: level_order.get(x['alert_level'], 99))

        return alerts

    @classmethod
    def batch_sync_inventory(
        cls,
        updates: List[Dict],
        user=None
    ) -> Dict:
        """
        Batch update inventory for multiple products.
        Used for bulk operations like stock count adjustments.

        Each update should have:
        - warehouse_id
        - product_id
        - quantity_change
        - movement_type
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(updates)
        }

        for update in updates:
            try:
                result = cls.sync_update_inventory(
                    warehouse_id=update['warehouse_id'],
                    product_id=update['product_id'],
                    quantity_change=update['quantity_change'],
                    movement_type=update['movement_type'],
                    reference_type=update.get('reference_type', ''),
                    reference_id=update.get('reference_id'),
                    note=update.get('note', ''),
                    user=user
                )
                results['success'].append({
                    'warehouse_id': update['warehouse_id'],
                    'product_id': update['product_id'],
                    'result': result
                })
            except Exception as e:
                results['failed'].append({
                    'warehouse_id': update['warehouse_id'],
                    'product_id': update['product_id'],
                    'error': str(e)
                })

        results['success_count'] = len(results['success'])
        results['failed_count'] = len(results['failed'])

        return results

    @classmethod
    def get_inventory_version(
        cls,
        warehouse_id: int,
        product_id: int
    ) -> int:
        """
        Get current inventory version for optimistic locking.
        Used by clients to detect concurrent modifications.
        """
        version_key = INVENTORY_VERSION_KEY.format(
            warehouse_id=warehouse_id,
            product_id=product_id
        )
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection('default')
            version = redis.get(version_key)
            return int(version) if version else 0
        except Exception:
            return 0


class InventoryEventHandler:
    """
    Handles inventory-related events from other modules.
    Provides integration points for sales, purchasing, etc.
    """

    @classmethod
    def on_sale_created(
        cls,
        warehouse_id: int,
        items: List[Dict],
        order_id: int,
        user=None
    ) -> Dict:
        """
        Handle sale order creation - reserve stock.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            result = InventorySyncService.sync_reserve_stock(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                reference_type='SalesOrder',
                reference_id=order_id,
                user=user
            )
            results.append(result)
        return {'reserved': results}

    @classmethod
    def on_sale_completed(
        cls,
        warehouse_id: int,
        items: List[Dict],
        order_id: int,
        user=None
    ) -> Dict:
        """
        Handle sale completion - deduct stock and release reservation.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            # Deduct stock
            deduct_result = InventorySyncService.sync_update_inventory(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity_change=-item['quantity'],
                movement_type='SALE_OUT',
                reference_type='SalesOrder',
                reference_id=order_id,
                user=user
            )

            # Release reservation
            release_result = InventorySyncService.sync_release_stock(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                reference_type='SalesOrder',
                reference_id=order_id,
                user=user
            )

            results.append({
                'deducted': deduct_result,
                'released': release_result
            })
        return {'completed': results}

    @classmethod
    def on_sale_cancelled(
        cls,
        warehouse_id: int,
        items: List[Dict],
        order_id: int,
        user=None
    ) -> Dict:
        """
        Handle sale cancellation - release reserved stock.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            result = InventorySyncService.sync_release_stock(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                reference_type='SalesOrder',
                reference_id=order_id,
                user=user
            )
            results.append(result)
        return {'released': results}

    @classmethod
    def on_purchase_received(
        cls,
        warehouse_id: int,
        items: List[Dict],
        receipt_id: int,
        user=None
    ) -> Dict:
        """
        Handle purchase goods receipt - add stock.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            result = InventorySyncService.sync_update_inventory(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity_change=item['quantity'],
                movement_type='PURCHASE_IN',
                reference_type='GoodsReceipt',
                reference_id=receipt_id,
                user=user
            )
            results.append(result)
        return {'received': results}

    @classmethod
    def on_purchase_returned(
        cls,
        warehouse_id: int,
        items: List[Dict],
        return_id: int,
        user=None
    ) -> Dict:
        """
        Handle purchase return - deduct stock.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            result = InventorySyncService.sync_update_inventory(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity_change=-item['quantity'],
                movement_type='RETURN_OUT',
                reference_type='PurchaseReturn',
                reference_id=return_id,
                user=user
            )
            results.append(result)
        return {'returned': results}

    @classmethod
    def on_customer_return(
        cls,
        warehouse_id: int,
        items: List[Dict],
        return_id: int,
        user=None
    ) -> Dict:
        """
        Handle customer return - add stock back.

        items should have: product_id, quantity
        """
        results = []
        for item in items:
            result = InventorySyncService.sync_update_inventory(
                warehouse_id=warehouse_id,
                product_id=item['product_id'],
                quantity_change=item['quantity'],
                movement_type='RETURN_IN',
                reference_type='SalesReturn',
                reference_id=return_id,
                user=user
            )
            results.append(result)
        return {'returned': results}

    @classmethod
    def on_stock_count_completed(
        cls,
        warehouse_id: int,
        adjustments: List[Dict],
        count_id: int,
        user=None
    ) -> Dict:
        """
        Handle stock count completion - adjust inventory.

        adjustments should have: product_id, difference
        """
        results = []
        for adj in adjustments:
            if adj['difference'] == 0:
                continue

            movement_type = 'COUNT_ADJUST'
            if adj['difference'] > 0:
                note = f'盤盈 +{adj["difference"]}'
            else:
                note = f'盤虧 {adj["difference"]}'

            result = InventorySyncService.sync_update_inventory(
                warehouse_id=warehouse_id,
                product_id=adj['product_id'],
                quantity_change=adj['difference'],
                movement_type=movement_type,
                reference_type='StockCount',
                reference_id=count_id,
                note=note,
                user=user
            )
            results.append(result)
        return {'adjusted': results}
