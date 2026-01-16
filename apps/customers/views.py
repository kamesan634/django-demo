"""
Customer views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import BaseViewSet
from apps.core.mixins import MultiSerializerMixin, StandardResponseMixin
from .models import Customer, CustomerLevel, PointsLog
from .serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerCreateSerializer,
    CustomerLevelSerializer,
    PointsLogSerializer,
    AddPointsSerializer,
)


class CustomerLevelViewSet(BaseViewSet):
    """CustomerLevel management ViewSet."""
    queryset = CustomerLevel.objects.all()
    serializer_class = CustomerLevelSerializer
    search_fields = ['name']
    ordering_fields = ['sort_order', 'name']


class CustomerViewSet(MultiSerializerMixin, StandardResponseMixin, BaseViewSet):
    """Customer management ViewSet."""
    queryset = Customer.objects.select_related('level').all()
    serializer_class = CustomerListSerializer
    serializer_classes = {
        'list': CustomerListSerializer,
        'retrieve': CustomerDetailSerializer,
        'create': CustomerCreateSerializer,
        'update': CustomerDetailSerializer,
        'partial_update': CustomerDetailSerializer,
    }
    search_fields = ['name', 'phone', 'member_no', 'email']
    filterset_fields = ['level', 'is_active']
    ordering_fields = ['name', 'member_no', 'created_at', 'total_spending']

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search customer by phone or member number."""
        phone = request.query_params.get('phone')
        member_no = request.query_params.get('member_no')

        if not phone and not member_no:
            return self.error_response(message='請提供手機號碼或會員編號')

        queryset = self.get_queryset()
        if phone:
            queryset = queryset.filter(phone=phone)
        elif member_no:
            queryset = queryset.filter(member_no=member_no)

        if not queryset.exists():
            return self.error_response(
                message='找不到此客戶',
                status_code=status.HTTP_404_NOT_FOUND
            )

        customer = queryset.first()
        serializer = CustomerDetailSerializer(customer)
        return self.success_response(data=serializer.data)

    @action(detail=True, methods=['get'])
    def points(self, request, pk=None):
        """Get customer points history."""
        customer = self.get_object()
        points_logs = customer.points_logs.all()[:50]
        serializer = PointsLogSerializer(points_logs, many=True)
        return self.success_response(data={
            'current_points': customer.points,
            'logs': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_points(self, request, pk=None):
        """Manually add points to customer."""
        customer = self.get_object()
        serializer = AddPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer.add_points(
            points=serializer.validated_data['points'],
            description=serializer.validated_data.get('description', '手動加點'),
            user=request.user
        )

        return self.success_response(
            message=f'成功加入 {serializer.validated_data["points"]} 點',
            data={'current_points': customer.points}
        )
