"""
Reports serializers.
"""
from rest_framework import serializers
from .models import CustomReport, ScheduledReport, ReportExecution


class CustomReportSerializer(serializers.ModelSerializer):
    """CustomReport serializer."""
    report_type_display = serializers.CharField(
        source='get_report_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.display_name',
        read_only=True,
        default=''
    )

    class Meta:
        model = CustomReport
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'description', 'config', 'columns', 'filters',
            'sort_by', 'sort_order', 'is_public',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ScheduledReportSerializer(serializers.ModelSerializer):
    """ScheduledReport serializer."""
    frequency_display = serializers.CharField(
        source='get_frequency_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    custom_report_name = serializers.CharField(
        source='custom_report.name',
        read_only=True,
        default=''
    )
    created_by_name = serializers.CharField(
        source='created_by.display_name',
        read_only=True,
        default=''
    )

    class Meta:
        model = ScheduledReport
        fields = [
            'id', 'name', 'custom_report', 'custom_report_name',
            'report_type', 'frequency', 'frequency_display',
            'run_time', 'run_day', 'status', 'status_display',
            'export_format', 'recipients',
            'last_run_at', 'last_run_status', 'next_run_at',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['last_run_at', 'last_run_status', 'next_run_at', 'created_at', 'updated_at']


class ReportExecutionSerializer(serializers.ModelSerializer):
    """ReportExecution serializer."""
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    scheduled_report_name = serializers.CharField(
        source='scheduled_report.name',
        read_only=True
    )

    class Meta:
        model = ReportExecution
        fields = [
            'id', 'scheduled_report', 'scheduled_report_name',
            'status', 'status_display',
            'started_at', 'completed_at',
            'file_path', 'error_message', 'recipients_notified',
            'created_at'
        ]
        read_only_fields = ['created_at']
