"""
Management command to process audit log queue.
F06-007: 操作紀錄佇列
BR06-007-02: 背景排程每 5 秒批次處理佇列
"""
import time
import json
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.core.models import AuditLog
from apps.core.redis_services import AuditQueueService
from apps.accounts.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process audit log queue from Redis to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous processing)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Processing interval in seconds (default: 5)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process per batch (default: 100)',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Process queue once and exit',
        )

    def handle(self, *args, **options):
        daemon_mode = options['daemon']
        interval = options['interval']
        batch_size = options['batch_size']
        once = options['once']

        self.stdout.write(self.style.SUCCESS(
            f'Starting audit log processor (daemon={daemon_mode}, interval={interval}s, batch={batch_size})'
        ))

        if once:
            self._process_batch(batch_size)
            return

        if daemon_mode:
            self._run_daemon(interval, batch_size)
        else:
            self._process_batch(batch_size)

    def _run_daemon(self, interval, batch_size):
        """Run in daemon mode with continuous processing."""
        self.stdout.write(self.style.WARNING('Running in daemon mode. Press Ctrl+C to stop.'))

        try:
            while True:
                processed = self._process_batch(batch_size)
                if processed == 0:
                    # No items processed, wait before next check
                    time.sleep(interval)
                else:
                    # Items were processed, continue immediately if more might be available
                    if processed >= batch_size:
                        continue
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down...'))

    def _process_batch(self, batch_size):
        """Process a batch of audit logs."""
        logs = AuditQueueService.pop_batch(batch_size)

        if not logs:
            return 0

        processed_count = 0
        failed_count = 0

        # Cache user lookups
        user_cache = {}

        for log_entry in logs:
            try:
                # Get or lookup user
                user_id = log_entry.get('userId')
                user = None
                if user_id:
                    if user_id not in user_cache:
                        try:
                            user_cache[user_id] = User.objects.get(pk=user_id)
                        except User.DoesNotExist:
                            user_cache[user_id] = None
                    user = user_cache[user_id]

                # Parse created_at
                created_at_str = log_entry.get('createdAt')
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = timezone.now()
                else:
                    created_at = timezone.now()

                # Parse old/new values
                old_value = log_entry.get('oldValue')
                new_value = log_entry.get('newValue')

                if isinstance(old_value, str):
                    try:
                        old_value = json.loads(old_value)
                    except (json.JSONDecodeError, TypeError):
                        pass

                if isinstance(new_value, str):
                    try:
                        new_value = json.loads(new_value)
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Create audit log record
                AuditLog.objects.create(
                    audit_id=log_entry.get('id', ''),
                    user=user,
                    username=log_entry.get('username', ''),
                    action=log_entry.get('action', 'UNKNOWN'),
                    module=log_entry.get('module', 'UNKNOWN'),
                    target_id=log_entry.get('targetId'),
                    target_type=log_entry.get('targetType'),
                    old_value=old_value,
                    new_value=new_value,
                    ip_address=log_entry.get('ip'),
                    user_agent=log_entry.get('userAgent', '')[:500] if log_entry.get('userAgent') else None,
                    created_at=created_at,
                )

                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process audit log: {e}")
                # Move to dead letter queue
                AuditQueueService.move_to_dead_letter(log_entry, str(e))
                failed_count += 1

        # Record processed count
        if processed_count > 0:
            AuditQueueService.record_processed(processed_count)

        self.stdout.write(
            f'Processed {processed_count} logs, {failed_count} failed'
        )

        return processed_count
