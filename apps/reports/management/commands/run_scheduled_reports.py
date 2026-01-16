"""
Management command to run scheduled reports.
F08-009: 排程報表
"""
import os
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from apps.reports.models import ScheduledReport, ReportExecution, CustomReport
from apps.reports.services import ScheduledReportService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run scheduled reports that are due for execution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous processing)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds (default: 60)',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Process due reports once and exit',
        )
        parser.add_argument(
            '--report-id',
            type=int,
            help='Run a specific scheduled report by ID',
        )

    def handle(self, *args, **options):
        daemon_mode = options['daemon']
        interval = options['interval']
        once = options['once']
        report_id = options.get('report_id')

        if report_id:
            self._run_specific_report(report_id)
            return

        self.stdout.write(self.style.SUCCESS(
            f'Starting scheduled report processor (daemon={daemon_mode}, interval={interval}s)'
        ))

        if once:
            self._process_due_reports()
            return

        if daemon_mode:
            self._run_daemon(interval)
        else:
            self._process_due_reports()

    def _run_daemon(self, interval):
        """Run in daemon mode with continuous processing."""
        import time

        self.stdout.write(self.style.WARNING('Running in daemon mode. Press Ctrl+C to stop.'))

        try:
            while True:
                self._process_due_reports()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down...'))

    def _process_due_reports(self):
        """Process all reports that are due for execution."""
        now = timezone.now()

        # Get all active scheduled reports that are due
        due_reports = ScheduledReport.objects.filter(
            status='ACTIVE',
            next_run_at__lte=now,
            is_deleted=False
        )

        if not due_reports.exists():
            self.stdout.write('No reports due for execution')
            return

        processed = 0
        failed = 0

        for schedule in due_reports:
            try:
                self._execute_scheduled_report(schedule)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to execute scheduled report {schedule.id}: {e}")
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(f'Processed {processed} reports, {failed} failed')
        )

    def _run_specific_report(self, report_id):
        """Run a specific scheduled report."""
        try:
            schedule = ScheduledReport.objects.get(pk=report_id)
            self.stdout.write(f'Running scheduled report: {schedule.name}')
            self._execute_scheduled_report(schedule)
            self.stdout.write(self.style.SUCCESS('Report execution completed'))
        except ScheduledReport.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Scheduled report {report_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))

    def _execute_scheduled_report(self, schedule):
        """Execute a single scheduled report."""
        # Create execution record
        execution = ReportExecution.objects.create(
            scheduled_report=schedule,
            status='RUNNING',
            started_at=timezone.now()
        )

        try:
            # Execute the report
            result = ScheduledReportService.execute_report(schedule, execution)

            # Update execution record
            execution.status = 'COMPLETED'
            execution.completed_at = timezone.now()
            execution.file_path = result.get('file_path', '')
            execution.save()

            # Update schedule
            schedule.last_run_at = timezone.now()
            schedule.last_run_status = 'SUCCESS'
            schedule.calculate_next_run()
            schedule.save()

            self.stdout.write(f'  Completed: {schedule.name}')

        except Exception as e:
            execution.status = 'FAILED'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()

            schedule.last_run_at = timezone.now()
            schedule.last_run_status = 'FAILED'
            schedule.calculate_next_run()
            schedule.save()

            logger.error(f"Scheduled report {schedule.name} failed: {e}")
            raise
