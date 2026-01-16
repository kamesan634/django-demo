"""
Core serializers for the application.
"""
from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """Base serializer with common fields."""
    created_at = serializers.DateTimeField(
        read_only=True,
        format='%Y-%m-%d %H:%M:%S'
    )
    updated_at = serializers.DateTimeField(
        read_only=True,
        format='%Y-%m-%d %H:%M:%S'
    )
    created_by_name = serializers.CharField(
        source='created_by.display_name',
        read_only=True,
        default=None
    )

    class Meta:
        abstract = True


class BulkCreateSerializer(serializers.ListSerializer):
    """Serializer for bulk create operations."""
    def create(self, validated_data):
        model = self.child.Meta.model
        instances = [model(**item) for item in validated_data]
        return model.objects.bulk_create(instances)


class BulkUpdateSerializer(serializers.ListSerializer):
    """Serializer for bulk update operations."""
    def update(self, instance, validated_data):
        instance_mapping = {item.id: item for item in instance}
        data_mapping = {item['id']: item for item in validated_data}

        result = []
        for instance_id, data in data_mapping.items():
            instance = instance_mapping.get(instance_id, None)
            if instance is not None:
                result.append(self.child.update(instance, data))

        return result
