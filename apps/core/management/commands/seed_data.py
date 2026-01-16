"""
Demo data seeding command.
建立假資料供展示與測試使用。

Usage:
    python manage.py seed_data          # 建立所有假資料
    python manage.py seed_data --reset  # 清除並重建所有假資料
"""
import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction


class Command(BaseCommand):
    help = '建立 Demo 假資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='清除現有資料後重新建立',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('清除現有資料...')
            self.clear_data()

        with transaction.atomic():
            self.stdout.write('開始建立假資料...')

            # 依序建立資料（有相依性）
            self.create_roles()
            self.create_stores_and_warehouses()
            self.create_users()
            self.create_customer_levels()
            self.create_customers()
            self.create_tax_types_and_units()
            self.create_categories()
            self.create_suppliers()
            self.create_products()
            self.create_inventory()
            self.create_promotions_and_coupons()
            self.create_orders()
            self.create_purchase_orders()
            self.create_goods_receipts()
            self.create_inventory_movements()
            self.create_stock_counts()
            self.create_stock_transfers()
            self.create_refunds()

            self.stdout.write(self.style.SUCCESS('假資料建立完成！'))

    def clear_data(self):
        """清除所有資料（保留 admin 帳號）"""
        from apps.sales.models import Payment, RefundItem, Refund, OrderItem, Order
        from apps.purchasing.models import GoodsReceiptItem, GoodsReceipt, PurchaseOrderItem, PurchaseOrder, Supplier, PurchaseReturnItem, PurchaseReturn, SupplierPrice
        from apps.inventory.models import InventoryMovement, Inventory, StockTransferItem, StockTransfer, StockCountItem, StockCount
        from apps.promotions.models import CouponUsage, Coupon, Promotion
        from apps.customers.models import PointsLog, Customer, CustomerLevel
        from apps.products.models import ProductBarcode, ProductVariant, Product, Category, TaxType, Unit
        from apps.stores.models import Warehouse, Store
        from apps.accounts.models import UserStore, User, Role

        # 依相依性順序刪除
        Payment.objects.all().delete()
        RefundItem.objects.all().delete()
        Refund.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()

        PurchaseReturnItem.objects.all().delete()
        PurchaseReturn.objects.all().delete()
        GoodsReceiptItem.objects.all().delete()
        GoodsReceipt.objects.all().delete()
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        SupplierPrice.objects.all().delete()

        InventoryMovement.objects.all().delete()
        Inventory.objects.all().delete()
        StockTransferItem.objects.all().delete()
        StockTransfer.objects.all().delete()
        StockCountItem.objects.all().delete()
        StockCount.objects.all().delete()

        CouponUsage.objects.all().delete()
        Coupon.objects.all().delete()
        Promotion.objects.all().delete()

        PointsLog.objects.all().delete()
        Customer.objects.all().delete()
        CustomerLevel.objects.all().delete()

        ProductBarcode.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        TaxType.objects.all().delete()
        Unit.objects.all().delete()

        Supplier.objects.all().delete()

        UserStore.objects.all().delete()
        User.objects.exclude(username='admin').delete()
        Role.objects.all().delete()

        Warehouse.objects.all().delete()
        Store.objects.all().delete()

        self.stdout.write('資料清除完成')

    def create_roles(self):
        """建立角色"""
        from apps.accounts.models import Role

        roles_data = [
            {'name': '系統管理員', 'code': 'ADMIN', 'permissions': {'all': True}},
            {'name': '店長', 'code': 'STORE_MANAGER', 'permissions': {
                'stores': ['read', 'update'],
                'products': ['read'],
                'inventory': ['read', 'update'],
                'sales': ['read', 'create', 'update'],
                'customers': ['read', 'create', 'update'],
                'reports': ['read'],
            }},
            {'name': '收銀員', 'code': 'CASHIER', 'permissions': {
                'products': ['read'],
                'inventory': ['read'],
                'sales': ['read', 'create'],
                'customers': ['read', 'create'],
            }},
            {'name': '倉管人員', 'code': 'WAREHOUSE_STAFF', 'permissions': {
                'products': ['read'],
                'inventory': ['read', 'create', 'update'],
                'purchasing': ['read', 'update'],
            }},
            {'name': '採購人員', 'code': 'PURCHASER', 'permissions': {
                'products': ['read'],
                'inventory': ['read'],
                'purchasing': ['read', 'create', 'update'],
                'suppliers': ['read', 'create', 'update'],
            }},
        ]

        for data in roles_data:
            Role.objects.get_or_create(
                code=data['code'],
                defaults={'name': data['name'], 'permissions': data['permissions']}
            )

        self.stdout.write(f'  建立 {len(roles_data)} 個角色')

    def create_stores_and_warehouses(self):
        """建立門店與倉庫"""
        from apps.stores.models import Store, Warehouse

        stores_data = [
            {'code': 'TPE001', 'name': '台北信義店', 'address': '台北市信義區信義路五段7號', 'phone': '02-27201234'},
            {'code': 'TPE002', 'name': '台北西門店', 'address': '台北市萬華區西門町1號', 'phone': '02-23111234'},
            {'code': 'NTC001', 'name': '新北板橋店', 'address': '新北市板橋區中山路一段1號', 'phone': '02-29601234'},
            {'code': 'TYC001', 'name': '桃園中壢店', 'address': '桃園市中壢區中央路100號', 'phone': '03-4251234'},
            {'code': 'TCH001', 'name': '台中逢甲店', 'address': '台中市西屯區福星路500號', 'phone': '04-24521234'},
        ]

        stores = []
        for data in stores_data:
            store, _ = Store.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'address': data['address'],
                    'phone': data['phone'],
                    'status': 'ACTIVE',
                }
            )
            stores.append(store)

        # 建立倉庫（每間店一個倉庫）
        for store in stores:
            Warehouse.objects.get_or_create(
                code=f'WH-{store.code}',
                defaults={
                    'name': f'{store.name}倉庫',
                    'store': store,
                    'warehouse_type': 'STORE',
                    'is_default': True,
                }
            )

        # 建立總倉（關聯到第一間店）
        main_store = stores[0] if stores else None
        if main_store:
            Warehouse.objects.get_or_create(
                code='WH-MAIN',
                defaults={
                    'name': '總倉',
                    'store': main_store,
                    'address': '新北市五股區五權路100號',
                    'warehouse_type': 'WAREHOUSE',
                    'is_default': False,
                }
            )

        self.stdout.write(f'  建立 {len(stores_data)} 間門店及對應倉庫')

    def create_users(self):
        """建立使用者"""
        from apps.accounts.models import User, Role, UserStore
        from apps.stores.models import Store

        roles = {r.code: r for r in Role.objects.all()}
        stores = list(Store.objects.all())

        # 建立管理員帳號
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'display_name': '系統管理員',
                'email': 'admin@example.com',
                'role': roles.get('ADMIN'),
                'status': 'active',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write('  建立管理員帳號: admin / admin123')

        users_data = [
            {'username': 'manager_tpe', 'display_name': '王大明', 'email': 'manager_tpe@example.com', 'role': 'STORE_MANAGER', 'store_idx': 0},
            {'username': 'manager_tch', 'display_name': '李小華', 'email': 'manager_tch@example.com', 'role': 'STORE_MANAGER', 'store_idx': 4},
            {'username': 'cashier01', 'display_name': '張美玲', 'email': 'cashier01@example.com', 'role': 'CASHIER', 'store_idx': 0},
            {'username': 'cashier02', 'display_name': '陳志明', 'email': 'cashier02@example.com', 'role': 'CASHIER', 'store_idx': 1},
            {'username': 'cashier03', 'display_name': '林佳蓉', 'email': 'cashier03@example.com', 'role': 'CASHIER', 'store_idx': 2},
            {'username': 'warehouse01', 'display_name': '黃建國', 'email': 'warehouse01@example.com', 'role': 'WAREHOUSE_STAFF', 'store_idx': None},
            {'username': 'purchaser01', 'display_name': '吳淑芬', 'email': 'purchaser01@example.com', 'role': 'PURCHASER', 'store_idx': None},
        ]

        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'display_name': data['display_name'],
                    'email': data['email'],
                    'role': roles.get(data['role']),
                    'status': 'active',
                }
            )
            if created:
                user.set_password('demo123')
                user.save()

                # 關聯門店
                if data['store_idx'] is not None and stores:
                    UserStore.objects.create(user=user, store=stores[data['store_idx']], is_primary=True)

        self.stdout.write(f'  建立 {len(users_data)} 個使用者')

    def create_customer_levels(self):
        """建立會員等級"""
        from apps.customers.models import CustomerLevel

        levels_data = [
            {'name': '一般會員', 'min_points': 0, 'discount_rate': Decimal('0'), 'points_multiplier': Decimal('1.0'), 'sort_order': 1, 'is_default': True},
            {'name': '銀卡會員', 'min_points': 1000, 'discount_rate': Decimal('5'), 'points_multiplier': Decimal('1.2'), 'sort_order': 2, 'is_default': False},
            {'name': '金卡會員', 'min_points': 5000, 'discount_rate': Decimal('10'), 'points_multiplier': Decimal('1.5'), 'sort_order': 3, 'is_default': False},
            {'name': 'VIP會員', 'min_points': 20000, 'discount_rate': Decimal('15'), 'points_multiplier': Decimal('2.0'), 'sort_order': 4, 'is_default': False},
        ]

        for data in levels_data:
            CustomerLevel.objects.get_or_create(
                name=data['name'],
                defaults=data
            )

        self.stdout.write(f'  建立 {len(levels_data)} 個會員等級')

    def create_customers(self):
        """建立客戶"""
        from apps.customers.models import Customer, CustomerLevel

        levels = {l.name: l for l in CustomerLevel.objects.all()}

        customers_data = [
            {'member_no': 'M000001', 'name': '張三豐', 'phone': '0912345678', 'email': 'zhang3f@example.com', 'level': 'VIP會員', 'points': 25000},
            {'member_no': 'M000002', 'name': '李莫愁', 'phone': '0923456789', 'email': 'limc@example.com', 'level': '金卡會員', 'points': 8500},
            {'member_no': 'M000003', 'name': '王重陽', 'phone': '0934567890', 'email': 'wangcy@example.com', 'level': '金卡會員', 'points': 6200},
            {'member_no': 'M000004', 'name': '黃蓉', 'phone': '0945678901', 'email': 'huangr@example.com', 'level': '銀卡會員', 'points': 2300},
            {'member_no': 'M000005', 'name': '郭靖', 'phone': '0956789012', 'email': 'guoj@example.com', 'level': '銀卡會員', 'points': 1800},
            {'member_no': 'M000006', 'name': '楊過', 'phone': '0967890123', 'email': 'yangg@example.com', 'level': '一般會員', 'points': 500},
            {'member_no': 'M000007', 'name': '小龍女', 'phone': '0978901234', 'email': 'xlnv@example.com', 'level': '一般會員', 'points': 300},
            {'member_no': 'M000008', 'name': '周伯通', 'phone': '0989012345', 'email': 'zhoubt@example.com', 'level': '一般會員', 'points': 150},
            {'member_no': 'M000009', 'name': '洪七公', 'phone': '0990123456', 'email': 'hong7g@example.com', 'level': '銀卡會員', 'points': 3200},
            {'member_no': 'M000010', 'name': '歐陽鋒', 'phone': '0911234567', 'email': 'ouyf@example.com', 'level': '一般會員', 'points': 80},
        ]

        for data in customers_data:
            Customer.objects.get_or_create(
                member_no=data['member_no'],
                defaults={
                    'name': data['name'],
                    'phone': data['phone'],
                    'email': data['email'],
                    'level': levels.get(data['level']),
                    'points': data['points'],
                }
            )

        self.stdout.write(f'  建立 {len(customers_data)} 個客戶')

    def create_tax_types_and_units(self):
        """建立稅別與單位"""
        from apps.products.models import TaxType, Unit

        tax_types = [
            {'name': '應稅', 'rate': Decimal('5'), 'is_default': True},
            {'name': '零稅率', 'rate': Decimal('0'), 'is_default': False},
            {'name': '免稅', 'rate': Decimal('0'), 'is_default': False},
        ]

        for data in tax_types:
            TaxType.objects.get_or_create(name=data['name'], defaults=data)

        units = [
            {'name': '個', 'symbol': 'pcs'},
            {'name': '件', 'symbol': 'pc'},
            {'name': '盒', 'symbol': 'box'},
            {'name': '包', 'symbol': 'pack'},
            {'name': '瓶', 'symbol': 'btl'},
            {'name': '罐', 'symbol': 'can'},
            {'name': '公斤', 'symbol': 'kg'},
            {'name': '公升', 'symbol': 'L'},
        ]

        for data in units:
            Unit.objects.get_or_create(name=data['name'], defaults=data)

        self.stdout.write(f'  建立 {len(tax_types)} 個稅別, {len(units)} 個單位')

    def create_categories(self):
        """建立商品分類"""
        from apps.products.models import Category

        # 一級分類
        categories_l1 = [
            {'name': '食品', 'sort_order': 1},
            {'name': '飲料', 'sort_order': 2},
            {'name': '日用品', 'sort_order': 3},
            {'name': '3C電子', 'sort_order': 4},
            {'name': '服飾配件', 'sort_order': 5},
        ]

        # 二級分類
        categories_l2 = {
            '食品': ['零食餅乾', '泡麵速食', '罐頭食品', '調味料'],
            '飲料': ['茶類飲料', '咖啡', '果汁', '碳酸飲料', '乳製品'],
            '日用品': ['清潔用品', '衛生紙品', '個人護理'],
            '3C電子': ['手機配件', '電腦周邊', '充電設備'],
            '服飾配件': ['上衣', '褲子', '配件'],
        }

        created_categories = {}
        for data in categories_l1:
            parent, _ = Category.objects.get_or_create(
                name=data['name'],
                parent=None,
                defaults={'sort_order': data['sort_order']}
            )
            created_categories[data['name']] = parent

            for idx, child_name in enumerate(categories_l2.get(data['name'], [])):
                Category.objects.get_or_create(
                    name=child_name,
                    parent=parent,
                    defaults={'sort_order': idx + 1}
                )

        total = len(categories_l1) + sum(len(v) for v in categories_l2.values())
        self.stdout.write(f'  建立 {total} 個商品分類')

    def create_suppliers(self):
        """建立供應商"""
        from apps.purchasing.models import Supplier

        suppliers_data = [
            {'code': 'SUP001', 'name': '統一企業', 'contact_name': '林經理', 'phone': '06-2535678', 'email': 'contact@uni.com.tw', 'address': '台南市永康區中正路301號'},
            {'code': 'SUP002', 'name': '味全食品', 'contact_name': '張經理', 'phone': '02-27191234', 'email': 'contact@weichuan.com.tw', 'address': '台北市中山區松江路100號'},
            {'code': 'SUP003', 'name': '義美食品', 'contact_name': '陳經理', 'phone': '02-26511234', 'email': 'contact@imei.com.tw', 'address': '新北市蘆洲區中正路200號'},
            {'code': 'SUP004', 'name': '可口可樂', 'contact_name': '王經理', 'phone': '02-87891234', 'email': 'contact@coca-cola.com.tw', 'address': '台北市內湖區瑞光路500號'},
            {'code': 'SUP005', 'name': '寶僑家品', 'contact_name': '李經理', 'phone': '02-27001234', 'email': 'contact@pg.com.tw', 'address': '台北市信義區松仁路100號'},
            {'code': 'SUP006', 'name': '花王企業', 'contact_name': '黃經理', 'phone': '02-87971234', 'email': 'contact@kao.com.tw', 'address': '台北市內湖區堤頂大道300號'},
        ]

        for data in suppliers_data:
            Supplier.objects.get_or_create(
                code=data['code'],
                defaults=data
            )

        self.stdout.write(f'  建立 {len(suppliers_data)} 個供應商')

    def create_products(self):
        """建立商品"""
        from apps.products.models import Product, ProductBarcode, Category, TaxType, Unit

        # 透過名稱找分類
        categories = {c.name: c for c in Category.objects.filter(parent__isnull=False)}
        tax_taxable = TaxType.objects.filter(name='應稅').first()
        unit_pcs = Unit.objects.filter(name='個').first()
        unit_bottle = Unit.objects.filter(name='瓶').first()
        unit_box = Unit.objects.filter(name='盒').first()
        unit_pack = Unit.objects.filter(name='包').first()

        products_data = [
            # 零食餅乾
            {'sku': 'SNK001', 'name': '樂事經典原味洋芋片', 'category': '零食餅乾', 'cost': 25, 'price': 35, 'unit': unit_pack},
            {'sku': 'SNK002', 'name': '品客洋芋片蜂蜜芥末', 'category': '零食餅乾', 'cost': 45, 'price': 65, 'unit': unit_pcs},
            {'sku': 'SNK003', 'name': '義美小泡芙巧克力', 'category': '零食餅乾', 'cost': 30, 'price': 45, 'unit': unit_box},
            {'sku': 'SNK004', 'name': '可樂果豌豆酥', 'category': '零食餅乾', 'cost': 20, 'price': 29, 'unit': unit_pack},
            {'sku': 'SNK005', 'name': '蝦味先原味', 'category': '零食餅乾', 'cost': 22, 'price': 32, 'unit': unit_pack},

            # 泡麵速食
            {'sku': 'INS001', 'name': '統一肉燥麵', 'category': '泡麵速食', 'cost': 18, 'price': 28, 'unit': unit_pack},
            {'sku': 'INS002', 'name': '維力炸醬麵', 'category': '泡麵速食', 'cost': 20, 'price': 30, 'unit': unit_pack},
            {'sku': 'INS003', 'name': '滿漢大餐蔥燒牛肉', 'category': '泡麵速食', 'cost': 35, 'price': 55, 'unit': unit_pack},
            {'sku': 'INS004', 'name': '來一客鮮蝦魚板', 'category': '泡麵速食', 'cost': 25, 'price': 39, 'unit': unit_pcs},

            # 茶類飲料
            {'sku': 'TEA001', 'name': '御茶園特上紅茶', 'category': '茶類飲料', 'cost': 15, 'price': 25, 'unit': unit_bottle},
            {'sku': 'TEA002', 'name': '茶裏王日式無糖綠茶', 'category': '茶類飲料', 'cost': 18, 'price': 29, 'unit': unit_bottle},
            {'sku': 'TEA003', 'name': '統一麥香紅茶', 'category': '茶類飲料', 'cost': 12, 'price': 20, 'unit': unit_bottle},
            {'sku': 'TEA004', 'name': '立頓檸檬紅茶', 'category': '茶類飲料', 'cost': 16, 'price': 25, 'unit': unit_bottle},

            # 咖啡
            {'sku': 'COF001', 'name': '伯朗咖啡藍山風味', 'category': '咖啡', 'cost': 18, 'price': 30, 'unit': unit_pcs},
            {'sku': 'COF002', 'name': '貝納頌經典拿鐵', 'category': '咖啡', 'cost': 25, 'price': 42, 'unit': unit_pcs},
            {'sku': 'COF003', 'name': '雀巢即溶咖啡', 'category': '咖啡', 'cost': 150, 'price': 229, 'unit': unit_pcs},

            # 碳酸飲料
            {'sku': 'SOD001', 'name': '可口可樂 600ml', 'category': '碳酸飲料', 'cost': 18, 'price': 29, 'unit': unit_bottle},
            {'sku': 'SOD002', 'name': '雪碧 600ml', 'category': '碳酸飲料', 'cost': 18, 'price': 29, 'unit': unit_bottle},
            {'sku': 'SOD003', 'name': '芬達橘子 600ml', 'category': '碳酸飲料', 'cost': 18, 'price': 29, 'unit': unit_bottle},
            {'sku': 'SOD004', 'name': '百事可樂 600ml', 'category': '碳酸飲料', 'cost': 17, 'price': 28, 'unit': unit_bottle},

            # 乳製品
            {'sku': 'DRY001', 'name': '統一瑞穗鮮乳', 'category': '乳製品', 'cost': 55, 'price': 79, 'unit': unit_bottle},
            {'sku': 'DRY002', 'name': '光泉全脂鮮乳', 'category': '乳製品', 'cost': 52, 'price': 75, 'unit': unit_bottle},
            {'sku': 'DRY003', 'name': '養樂多', 'category': '乳製品', 'cost': 25, 'price': 40, 'unit': unit_pack},

            # 清潔用品
            {'sku': 'CLN001', 'name': '白蘭洗衣精', 'category': '清潔用品', 'cost': 120, 'price': 189, 'unit': unit_bottle},
            {'sku': 'CLN002', 'name': '花王洗碗精', 'category': '清潔用品', 'cost': 60, 'price': 99, 'unit': unit_bottle},
            {'sku': 'CLN003', 'name': '妙管家地板清潔劑', 'category': '清潔用品', 'cost': 80, 'price': 129, 'unit': unit_bottle},

            # 衛生紙品
            {'sku': 'TIS001', 'name': '舒潔衛生紙', 'category': '衛生紙品', 'cost': 180, 'price': 269, 'unit': unit_pack},
            {'sku': 'TIS002', 'name': '五月花面紙', 'category': '衛生紙品', 'cost': 55, 'price': 85, 'unit': unit_pack},
            {'sku': 'TIS003', 'name': '春風抽取式衛生紙', 'category': '衛生紙品', 'cost': 200, 'price': 299, 'unit': unit_pack},

            # 手機配件
            {'sku': 'PHN001', 'name': 'iPhone 充電線', 'category': '手機配件', 'cost': 150, 'price': 299, 'unit': unit_pcs},
            {'sku': 'PHN002', 'name': 'Type-C 快充線', 'category': '手機配件', 'cost': 120, 'price': 249, 'unit': unit_pcs},
            {'sku': 'PHN003', 'name': '手機保護殼', 'category': '手機配件', 'cost': 80, 'price': 199, 'unit': unit_pcs},

            # 充電設備
            {'sku': 'CHG001', 'name': '行動電源 10000mAh', 'category': '充電設備', 'cost': 350, 'price': 699, 'unit': unit_pcs},
            {'sku': 'CHG002', 'name': 'USB 充電器 20W', 'category': '充電設備', 'cost': 200, 'price': 399, 'unit': unit_pcs},
        ]

        for idx, data in enumerate(products_data):
            product, created = Product.objects.get_or_create(
                sku=data['sku'],
                defaults={
                    'name': data['name'],
                    'category': categories.get(data['category']),
                    'cost_price': Decimal(str(data['cost'])),
                    'sale_price': Decimal(str(data['price'])),
                    'tax_type': tax_taxable,
                    'unit': data['unit'],
                    'status': 'ACTIVE',
                    'safety_stock': 10,
                }
            )

            if created:
                # 建立條碼
                barcode = f'47100{str(idx+1).zfill(8)}'
                ProductBarcode.objects.create(
                    product=product,
                    barcode=barcode,
                    is_primary=True
                )

        self.stdout.write(f'  建立 {len(products_data)} 個商品')

    def create_inventory(self):
        """建立庫存"""
        from apps.products.models import Product
        from apps.stores.models import Warehouse
        from apps.inventory.models import Inventory

        products = list(Product.objects.all())
        warehouses = list(Warehouse.objects.all())

        count = 0
        for warehouse in warehouses:
            for product in products:
                qty = random.randint(20, 200)
                Inventory.objects.get_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={
                        'quantity': qty,
                        'available_quantity': qty,
                        'reserved_quantity': 0,
                    }
                )
                count += 1

        self.stdout.write(f'  建立 {count} 筆庫存記錄')

    def create_promotions_and_coupons(self):
        """建立促銷活動與優惠券"""
        from apps.promotions.models import Promotion, Coupon
        from apps.stores.models import Store

        now = timezone.now()
        stores = list(Store.objects.all())

        promotions_data = [
            {
                'name': '週年慶全館85折',
                'promotion_type': 'PERCENTAGE',
                'discount_value': Decimal('15'),
                'start_date': now - timedelta(days=5),
                'end_date': now + timedelta(days=25),
                'is_active': True,
            },
            {
                'name': '飲料第二件6折',
                'promotion_type': 'BUY_X_GET_Y',
                'discount_value': Decimal('40'),
                'buy_quantity': 2,
                'get_quantity': 1,
                'start_date': now,
                'end_date': now + timedelta(days=14),
                'is_active': True,
            },
            {
                'name': '滿千送百',
                'promotion_type': 'FIXED',
                'discount_value': Decimal('100'),
                'min_purchase': Decimal('1000'),
                'start_date': now,
                'end_date': now + timedelta(days=30),
                'is_active': True,
            },
        ]

        for data in promotions_data:
            promo, created = Promotion.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                promo.stores.set(stores)

        coupons_data = [
            {'code': 'WELCOME100', 'name': '新會員折100元', 'discount_type': 'FIXED', 'discount_value': Decimal('100'), 'min_purchase': Decimal('500'), 'usage_limit': 1000, 'used_count': 156},
            {'code': 'SUMMER50', 'name': '夏季優惠50元', 'discount_type': 'FIXED', 'discount_value': Decimal('50'), 'min_purchase': Decimal('300'), 'usage_limit': 500, 'used_count': 89},
            {'code': 'VIP20OFF', 'name': 'VIP專屬8折券', 'discount_type': 'PERCENTAGE', 'discount_value': Decimal('20'), 'min_purchase': Decimal('0'), 'usage_limit': 200, 'used_count': 45},
            {'code': 'FREESHIP', 'name': '免運費優惠', 'discount_type': 'FIXED', 'discount_value': Decimal('60'), 'min_purchase': Decimal('499'), 'usage_limit': 300, 'used_count': 120},
        ]

        for data in coupons_data:
            Coupon.objects.get_or_create(
                code=data['code'],
                defaults={
                    **data,
                    'start_date': now - timedelta(days=10),
                    'end_date': now + timedelta(days=50),
                    'status': 'ACTIVE',
                }
            )

        self.stdout.write(f'  建立 {len(promotions_data)} 個促銷活動, {len(coupons_data)} 張優惠券')

    def create_orders(self):
        """建立訂單"""
        from apps.sales.models import Order, OrderItem, Payment
        from apps.products.models import Product
        from apps.stores.models import Store, Warehouse
        from apps.customers.models import Customer

        products = list(Product.objects.all())
        stores = list(Store.objects.all())
        customers = list(Customer.objects.all())

        now = timezone.now()
        order_count = 0

        # 建立過去30天的訂單
        for day_offset in range(30, 0, -1):
            order_date = now - timedelta(days=day_offset)
            # 每天 5-15 筆訂單
            daily_orders = random.randint(5, 15)

            for _ in range(daily_orders):
                store = random.choice(stores)
                # 取得該店的預設倉庫
                warehouse = Warehouse.objects.filter(store=store, is_default=True).first()
                if not warehouse:
                    warehouse = Warehouse.objects.filter(store=store).first()
                if not warehouse:
                    continue

                customer = random.choice(customers) if random.random() > 0.3 else None

                # 訂單編號
                order_number = f"ORD{order_date.strftime('%Y%m%d')}{str(order_count+1).zfill(4)}"

                # 建立訂單
                order = Order.objects.create(
                    order_number=order_number,
                    store=store,
                    warehouse=warehouse,
                    customer=customer,
                    order_type='POS',
                    status='COMPLETED',
                    subtotal=Decimal('0'),
                    discount_amount=Decimal('0'),
                    tax_amount=Decimal('0'),
                    total_amount=Decimal('0'),
                )
                # 更新 created_at 為過去的日期
                Order.objects.filter(pk=order.pk).update(created_at=order_date)

                # 建立訂單項目 (1-5 個商品)
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))

                subtotal = Decimal('0')
                for product in selected_products:
                    qty = random.randint(1, 3)
                    unit_price = product.sale_price
                    item_total = unit_price * qty

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=qty,
                        unit_price=unit_price,
                        discount_amount=Decimal('0'),
                        subtotal=item_total,
                    )
                    subtotal += item_total

                # 計算稅額 (5%)
                tax = (subtotal * Decimal('0.05')).quantize(Decimal('1'))
                total = subtotal + tax

                # 隨機折扣
                discount = Decimal('0')
                if random.random() > 0.7:
                    discount = (subtotal * Decimal(str(random.randint(5, 15))) / 100).quantize(Decimal('1'))
                    total = total - discount

                order.subtotal = subtotal
                order.discount_amount = discount
                order.tax_amount = tax
                order.total_amount = total
                order.save()

                # 建立付款記錄
                payment_methods = ['CASH', 'CREDIT_CARD', 'LINE_PAY', 'APPLE_PAY']
                Payment.objects.create(
                    order=order,
                    method=random.choice(payment_methods),
                    amount=total,
                    status='COMPLETED',
                )

                order_count += 1

        self.stdout.write(f'  建立 {order_count} 筆訂單')

    def create_purchase_orders(self):
        """建立採購單"""
        from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem, Supplier, SupplierPrice
        from apps.products.models import Product
        from apps.stores.models import Warehouse
        from apps.accounts.models import User

        suppliers = list(Supplier.objects.all())
        products = list(Product.objects.all())
        warehouses = list(Warehouse.objects.filter(warehouse_type='WAREHOUSE'))
        if not warehouses:
            warehouses = list(Warehouse.objects.all()[:1])
        admin = User.objects.filter(username='admin').first()

        now = timezone.now()
        po_count = 0

        # 建立供應商報價
        for supplier in suppliers:
            assigned_products = random.sample(products, min(8, len(products)))
            for product in assigned_products:
                SupplierPrice.objects.get_or_create(
                    supplier=supplier,
                    product=product,
                    effective_from=now.date() - timedelta(days=90),
                    defaults={
                        'unit_price': product.cost_price * Decimal('0.9'),
                        'min_quantity': random.choice([1, 5, 10]),
                        'lead_time_days': random.randint(3, 14),
                        'is_preferred': random.random() > 0.7,
                    }
                )

        # 建立採購單
        statuses = ['DRAFT', 'SUBMITTED', 'APPROVED', 'COMPLETED', 'COMPLETED', 'COMPLETED']
        for i in range(15):
            supplier = random.choice(suppliers)
            warehouse = random.choice(warehouses)
            status = random.choice(statuses)
            days_ago = random.randint(1, 45)
            order_date = now - timedelta(days=days_ago)

            po = PurchaseOrder.objects.create(
                po_number=f"PO{order_date.strftime('%Y%m%d')}{str(i+1).zfill(3)}",
                supplier=supplier,
                warehouse=warehouse,
                status=status,
                expected_date=order_date.date() + timedelta(days=7),
                submitted_at=order_date if status != 'DRAFT' else None,
                approved_by=admin if status in ('APPROVED', 'COMPLETED') else None,
                approved_at=order_date if status in ('APPROVED', 'COMPLETED') else None,
                note=f'採購單備註 {i+1}' if random.random() > 0.7 else '',
            )
            PurchaseOrder.objects.filter(pk=po.pk).update(created_at=order_date)

            # 建立採購單項目
            num_items = random.randint(2, 6)
            selected_products = random.sample(products, min(num_items, len(products)))
            total = Decimal('0')

            for product in selected_products:
                qty = random.randint(10, 50)
                unit_price = product.cost_price
                subtotal = qty * unit_price

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity=qty,
                    received_quantity=qty if status == 'COMPLETED' else 0,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
                total += subtotal

            po.total_amount = total
            po.save(update_fields=['total_amount'])
            po_count += 1

        self.stdout.write(f'  建立 {po_count} 筆採購單')

    def create_goods_receipts(self):
        """建立進貨單"""
        from apps.purchasing.models import PurchaseOrder, GoodsReceipt, GoodsReceiptItem

        now = timezone.now()
        completed_pos = PurchaseOrder.objects.filter(status='COMPLETED')
        receipt_count = 0

        for po in completed_pos:
            receipt_date = po.created_at + timedelta(days=random.randint(3, 10))

            receipt = GoodsReceipt.objects.create(
                receipt_number=f"GR{receipt_date.strftime('%Y%m%d')}{str(receipt_count+1).zfill(3)}",
                purchase_order=po,
                status='COMPLETED',
                receipt_date=receipt_date.date(),
                note='驗收完成' if random.random() > 0.5 else '',
            )
            GoodsReceipt.objects.filter(pk=receipt.pk).update(created_at=receipt_date)

            # 建立收貨明細
            for po_item in po.items.all():
                GoodsReceiptItem.objects.create(
                    receipt=receipt,
                    po_item=po_item,
                    received_quantity=po_item.quantity,
                )

            receipt_count += 1

        self.stdout.write(f'  建立 {receipt_count} 筆進貨單')

    def create_inventory_movements(self):
        """建立庫存異動記錄"""
        from apps.inventory.models import Inventory, InventoryMovement
        from apps.purchasing.models import GoodsReceipt
        from apps.sales.models import Order

        now = timezone.now()
        movement_count = 0

        # 從進貨單建立入庫記錄
        for receipt in GoodsReceipt.objects.all():
            for item in receipt.items.all():
                inventory = Inventory.objects.filter(
                    warehouse=receipt.purchase_order.warehouse,
                    product=item.po_item.product
                ).first()

                if inventory:
                    InventoryMovement.objects.create(
                        warehouse=receipt.purchase_order.warehouse,
                        product=item.po_item.product,
                        movement_type='PURCHASE_IN',
                        quantity=item.received_quantity,
                        balance=inventory.quantity,
                        reference_type='GoodsReceipt',
                        reference_id=receipt.id,
                        note=f'採購入庫 - {receipt.receipt_number}',
                    )
                    movement_count += 1

        # 從訂單建立出庫記錄 (只取部分訂單)
        orders = Order.objects.filter(status='COMPLETED')[:50]
        for order in orders:
            for item in order.items.all():
                inventory = Inventory.objects.filter(
                    warehouse=order.warehouse,
                    product=item.product
                ).first()

                if inventory:
                    InventoryMovement.objects.create(
                        warehouse=order.warehouse,
                        product=item.product,
                        movement_type='SALE_OUT',
                        quantity=-item.quantity,
                        balance=inventory.quantity,
                        reference_type='Order',
                        reference_id=order.id,
                        note=f'銷售出庫 - {order.order_number}',
                    )
                    movement_count += 1

        self.stdout.write(f'  建立 {movement_count} 筆庫存異動')

    def create_stock_counts(self):
        """建立盤點單"""
        from apps.inventory.models import StockCount, StockCountItem, Inventory
        from apps.stores.models import Warehouse
        from apps.products.models import Product

        now = timezone.now()
        warehouses = list(Warehouse.objects.all())
        products = list(Product.objects.all())
        count_num = 0

        statuses = ['COMPLETED', 'COMPLETED', 'IN_PROGRESS', 'DRAFT']

        for i in range(8):
            warehouse = random.choice(warehouses)
            status = random.choice(statuses)
            days_ago = random.randint(5, 60)
            count_date = now - timedelta(days=days_ago)

            stock_count = StockCount.objects.create(
                warehouse=warehouse,
                count_number=f"SC{count_date.strftime('%Y%m%d')}{str(i+1).zfill(3)}",
                status=status,
                count_date=count_date.date(),
                completed_at=count_date if status == 'COMPLETED' else None,
                note=f'定期盤點 - {warehouse.name}' if random.random() > 0.5 else '',
            )
            StockCount.objects.filter(pk=stock_count.pk).update(created_at=count_date)

            # 建立盤點項目 (隨機選擇部分商品)
            selected_products = random.sample(products, min(random.randint(5, 15), len(products)))
            for product in selected_products:
                inventory = Inventory.objects.filter(warehouse=warehouse, product=product).first()
                system_qty = inventory.quantity if inventory else 0

                # 實際數量有時會有差異
                if status in ('COMPLETED', 'IN_PROGRESS'):
                    diff = random.choice([0, 0, 0, -1, -2, 1, -3]) if random.random() > 0.6 else 0
                    actual_qty = max(0, system_qty + diff)
                else:
                    actual_qty = None

                StockCountItem.objects.create(
                    stock_count=stock_count,
                    product=product,
                    system_quantity=system_qty,
                    actual_quantity=actual_qty,
                )

            count_num += 1

        self.stdout.write(f'  建立 {count_num} 筆盤點單')

    def create_stock_transfers(self):
        """建立調撥單"""
        from apps.inventory.models import StockTransfer, StockTransferItem
        from apps.stores.models import Warehouse
        from apps.products.models import Product

        now = timezone.now()
        warehouses = list(Warehouse.objects.all())
        products = list(Product.objects.all())
        transfer_count = 0

        if len(warehouses) < 2:
            self.stdout.write('  倉庫不足，跳過建立調撥單')
            return

        statuses = ['COMPLETED', 'COMPLETED', 'IN_TRANSIT', 'PENDING']

        for i in range(10):
            from_wh, to_wh = random.sample(warehouses, 2)
            status = random.choice(statuses)
            days_ago = random.randint(3, 40)
            transfer_date = now - timedelta(days=days_ago)

            transfer = StockTransfer.objects.create(
                transfer_number=f"ST{transfer_date.strftime('%Y%m%d')}{str(i+1).zfill(3)}",
                from_warehouse=from_wh,
                to_warehouse=to_wh,
                status=status,
                transfer_date=transfer_date.date(),
                completed_at=transfer_date if status == 'COMPLETED' else None,
                note=f'{from_wh.name} -> {to_wh.name}' if random.random() > 0.5 else '',
            )
            StockTransfer.objects.filter(pk=transfer.pk).update(created_at=transfer_date)

            # 建立調撥項目
            num_items = random.randint(2, 5)
            selected_products = random.sample(products, min(num_items, len(products)))
            for product in selected_products:
                StockTransferItem.objects.create(
                    transfer=transfer,
                    product=product,
                    quantity=random.randint(5, 20),
                )

            transfer_count += 1

        self.stdout.write(f'  建立 {transfer_count} 筆調撥單')

    def create_refunds(self):
        """建立退貨單"""
        from apps.sales.models import Order, Refund, RefundItem

        now = timezone.now()
        completed_orders = list(Order.objects.filter(status='COMPLETED')[:30])
        refund_count = 0

        # 隨機選擇部分訂單進行退貨
        orders_to_refund = random.sample(completed_orders, min(8, len(completed_orders)))

        reasons = ['商品瑕疵', '尺寸不合', '顏色不符', '重複購買', '不想要了', '品質問題']

        for i, order in enumerate(orders_to_refund):
            days_after = random.randint(1, 7)
            refund_date = order.created_at + timedelta(days=days_after)
            status = random.choice(['COMPLETED', 'COMPLETED', 'PENDING'])

            # 選擇部分商品退貨
            order_items = list(order.items.all())
            items_to_refund = random.sample(order_items, min(random.randint(1, 2), len(order_items)))

            refund_amount = Decimal('0')
            for item in items_to_refund:
                refund_qty = random.randint(1, item.quantity)
                refund_amount += item.unit_price * refund_qty

            refund = Refund.objects.create(
                refund_number=f"RF{refund_date.strftime('%Y%m%d')}{str(i+1).zfill(3)}",
                order=order,
                refund_amount=refund_amount,
                reason=random.choice(reasons),
                status=status,
                completed_at=refund_date if status == 'COMPLETED' else None,
            )
            Refund.objects.filter(pk=refund.pk).update(created_at=refund_date)

            # 建立退貨明細
            for item in items_to_refund:
                refund_qty = random.randint(1, item.quantity)
                RefundItem.objects.create(
                    refund=refund,
                    order_item=item,
                    quantity=refund_qty,
                )

            refund_count += 1

        self.stdout.write(f'  建立 {refund_count} 筆退貨單')
