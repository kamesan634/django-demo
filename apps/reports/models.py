"""
Reports models: CustomReport, ScheduledReport.
"""
from django.db import models
from apps.core.models import BaseModel


class CustomReport(BaseModel):
    """Custom report template model."""
    REPORT_TYPES = [
        ('SALES', '銷售報表'),
        ('INVENTORY', '庫存報表'),
        ('PURCHASE', '採購報表'),
        ('CUSTOMER', '客戶報表'),
        ('PRODUCT', '商品報表'),
    ]

    name = models.CharField(max_length=100, verbose_name='報表名稱')
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES,
        verbose_name='報表類型'
    )
    description = models.TextField(blank=True, verbose_name='描述')
    # JSON field for report configuration
    config = models.JSONField(
        default=dict,
        verbose_name='報表設定'
    )
    # Columns to include
    columns = models.JSONField(
        default=list,
        verbose_name='欄位設定'
    )
    # Filter conditions
    filters = models.JSONField(
        default=dict,
        verbose_name='篩選條件'
    )
    # Sort settings
    sort_by = models.CharField(max_length=50, blank=True, verbose_name='排序欄位')
    sort_order = models.CharField(
        max_length=4,
        choices=[('ASC', '升冪'), ('DESC', '降冪')],
        default='DESC',
        verbose_name='排序方向'
    )
    is_public = models.BooleanField(default=False, verbose_name='公開報表')

    class Meta:
        db_table = 'custom_reports'
        verbose_name = '自訂報表'
        verbose_name_plural = '自訂報表'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ScheduledReport(BaseModel):
    """Scheduled report job model."""
    FREQUENCY_CHOICES = [
        ('DAILY', '每日'),
        ('WEEKLY', '每週'),
        ('MONTHLY', '每月'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', '啟用'),
        ('PAUSED', '暫停'),
        ('DISABLED', '停用'),
    ]

    name = models.CharField(max_length=100, verbose_name='排程名稱')
    custom_report = models.ForeignKey(
        CustomReport,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedules',
        verbose_name='自訂報表'
    )
    report_type = models.CharField(
        max_length=50,
        verbose_name='報表類型'
    )
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        verbose_name='執行頻率'
    )
    run_time = models.TimeField(verbose_name='執行時間')
    run_day = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='執行日(週:1-7/月:1-31)'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='狀態'
    )
    # Export settings
    export_format = models.CharField(
        max_length=10,
        choices=[('CSV', 'CSV'), ('EXCEL', 'Excel'), ('PDF', 'PDF')],
        default='EXCEL',
        verbose_name='匯出格式'
    )
    # Recipients
    recipients = models.JSONField(
        default=list,
        verbose_name='收件人'
    )
    # Last run info
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='上次執行時間')
    last_run_status = models.CharField(max_length=20, blank=True, verbose_name='上次執行狀態')
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name='下次執行時間')

    class Meta:
        db_table = 'scheduled_reports'
        verbose_name = '排程報表'
        verbose_name_plural = '排程報表'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_frequency_display()})'

    def calculate_next_run(self):
        """Calculate next run time based on frequency."""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        run_datetime = timezone.make_aware(
            timezone.datetime.combine(now.date(), self.run_time)
        )

        if self.frequency == 'DAILY':
            if run_datetime <= now:
                run_datetime += timedelta(days=1)
        elif self.frequency == 'WEEKLY':
            days_ahead = self.run_day - now.isoweekday()
            if days_ahead <= 0 or (days_ahead == 0 and run_datetime <= now):
                days_ahead += 7
            run_datetime = run_datetime.replace(day=now.day) + timedelta(days=days_ahead)
        elif self.frequency == 'MONTHLY':
            if now.day > self.run_day or (now.day == self.run_day and run_datetime <= now):
                # Next month
                if now.month == 12:
                    run_datetime = run_datetime.replace(year=now.year + 1, month=1, day=self.run_day)
                else:
                    run_datetime = run_datetime.replace(month=now.month + 1, day=self.run_day)
            else:
                run_datetime = run_datetime.replace(day=self.run_day)

        self.next_run_at = run_datetime
        return run_datetime


class ReportExecution(BaseModel):
    """Report execution log model."""
    STATUS_CHOICES = [
        ('PENDING', '待執行'),
        ('RUNNING', '執行中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失敗'),
    ]

    scheduled_report = models.ForeignKey(
        ScheduledReport,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='排程報表'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='狀態'
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='開始時間')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    file_path = models.CharField(max_length=500, blank=True, verbose_name='檔案路徑')
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    recipients_notified = models.JSONField(default=list, verbose_name='已通知收件人')

    class Meta:
        db_table = 'report_executions'
        verbose_name = '報表執行紀錄'
        verbose_name_plural = '報表執行紀錄'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.scheduled_report.name} - {self.created_at}'
