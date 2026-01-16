"""
Management command to sync inventory data.
F05-010: 庫存同步機制

Usage:
    python manage.py sync_inventory --action=cache_all
    python manage.py sync_inventory --action=check_alerts
    python manage.py sync_inventory --action=clear_cache
    python manage.py sync_inventory --action=monitor --interval=60
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db.models import F

from apps.inventory.models import Inventory
from apps.inventory.sync_services import InventorySyncService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Inventory synchronization operations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            default='cache_all',
            choices=['cache_all', 'check_alerts', 'clear_cache', 'monitor'],
            help='Action to perform'
        )
        parser.add_argument(
            '--warehouse',
            type=int,
            default=None,
            help='Filter by warehouse ID'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for processing'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds for monitor mode'
        )

    def handle(self, *args, **options):
        action = options['action']
        warehouse_id = options['warehouse']
        batch_size = options['batch_size']
        interval = options['interval']

        self.stdout.write(f'Starting inventory sync: action={action}')

        if action == 'cache_all':
            self.cache_all_inventory(warehouse_id, batch_size)
        elif action == 'check_alerts':
            self.check_and_publish_alerts(warehouse_id)
        elif action == 'clear_cache':
            self.clear_inventory_cache(warehouse_id)
        elif action == 'monitor':
            self.monitor_inventory(warehouse_id, interval)

    def cache_all_inventory(self, warehouse_id, batch_size):
        """Cache all inventory data to Redis."""
        queryset = Inventory.objects.select_related('warehouse', 'product').all()

        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        total = queryset.count()
        self.stdout.write(f'Caching {total} inventory records...')

        synced = 0
        errors = 0

        for i, inventory in enumerate(queryset.iterator(chunk_size=batch_size)):
            try:
                cache_data = {
                    'id': inventory.id,
                    'warehouse_id': inventory.warehouse_id,
                    'warehouse_name': inventory.warehouse.name,
                    'product_id': inventory.product_id,
                    'product_name': inventory.product.name,
                    'product_sku': inventory.product.sku,
                    'quantity': inventory.quantity,
                    'available_quantity': inventory.available_quantity,
                    'reserved_quantity': inventory.reserved_quantity,
                }
                InventorySyncService.set_cached_inventory(
                    inventory.warehouse_id,
                    inventory.product_id,
                    cache_data
                )
                synced += 1

                if (i + 1) % 100 == 0:
                    self.stdout.write(f'Progress: {i + 1}/{total}')

            except Exception as e:
                errors += 1
                logger.error(f'Error caching inventory {inventory.id}: {e}')

        self.stdout.write(self.style.SUCCESS(
            f'Cached {synced} inventory records, {errors} errors'
        ))

    def check_and_publish_alerts(self, warehouse_id):
        """Check inventory levels and publish alerts."""
        self.stdout.write('Checking inventory levels...')

        alerts = InventorySyncService.get_low_stock_alerts(warehouse_id)

        # Group by alert level
        by_level = {
            'OUT_OF_STOCK': [],
            'CRITICAL': [],
            'WARNING': [],
            'LOW': []
        }

        for alert in alerts:
            by_level[alert['alert_level']].append(alert)

        self.stdout.write(f'\nAlert Summary:')
        self.stdout.write(f'  OUT_OF_STOCK: {len(by_level["OUT_OF_STOCK"])}')
        self.stdout.write(f'  CRITICAL:     {len(by_level["CRITICAL"])}')
        self.stdout.write(f'  WARNING:      {len(by_level["WARNING"])}')
        self.stdout.write(f'  LOW:          {len(by_level["LOW"])}')
        self.stdout.write(f'  Total:        {len(alerts)}')

        # Publish alerts via notification service
        from apps.core.redis_services import NotificationService

        for alert in alerts[:50]:  # Limit to 50 most critical
            NotificationService.publish(
                InventorySyncService.LOW_STOCK_CHANNEL,
                alert
            )

        self.stdout.write(self.style.SUCCESS(
            f'Published {min(len(alerts), 50)} alerts to notification channel'
        ))

    def clear_inventory_cache(self, warehouse_id):
        """Clear inventory cache."""
        self.stdout.write('Clearing inventory cache...')

        queryset = Inventory.objects.all()
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)

        cleared = 0
        for inventory in queryset.iterator(chunk_size=500):
            InventorySyncService.invalidate_inventory_cache(
                inventory.warehouse_id,
                inventory.product_id
            )
            cleared += 1

        self.stdout.write(self.style.SUCCESS(
            f'Cleared cache for {cleared} inventory records'
        ))

    def monitor_inventory(self, warehouse_id, interval):
        """Continuously monitor inventory and publish alerts."""
        self.stdout.write(f'Starting inventory monitor (interval: {interval}s)...')
        self.stdout.write('Press Ctrl+C to stop')

        try:
            while True:
                # Check alerts
                alerts = InventorySyncService.get_low_stock_alerts(warehouse_id)

                critical_count = len([
                    a for a in alerts
                    if a['alert_level'] in ('OUT_OF_STOCK', 'CRITICAL')
                ])

                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                self.stdout.write(
                    f'[{timestamp}] Total alerts: {len(alerts)}, '
                    f'Critical: {critical_count}'
                )

                # Publish critical alerts
                from apps.core.redis_services import NotificationService
                for alert in alerts:
                    if alert['alert_level'] in ('OUT_OF_STOCK', 'CRITICAL'):
                        NotificationService.publish(
                            InventorySyncService.LOW_STOCK_CHANNEL,
                            alert
                        )

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('\nMonitor stopped')
