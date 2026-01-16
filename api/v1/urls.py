"""
API v1 URL Configuration.
"""
from django.urls import path, include

urlpatterns = [
    # Auth & Users
    path('', include('apps.accounts.urls')),

    # Stores & Warehouses
    path('', include('apps.stores.urls')),

    # Products & Categories
    path('', include('apps.products.urls')),

    # Customers
    path('', include('apps.customers.urls')),

    # Inventory
    path('', include('apps.inventory.urls')),

    # Sales & POS
    path('', include('apps.sales.urls')),

    # Purchasing
    path('', include('apps.purchasing.urls')),

    # Promotions
    path('', include('apps.promotions.urls')),

    # Reports & Dashboard
    path('', include('apps.reports.urls')),

    # System Management (Redis/Cache/Audit)
    path('', include('apps.core.urls')),
]
