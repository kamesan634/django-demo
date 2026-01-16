#!/bin/bash
set -e

echo "=== Django Demo 啟動腳本 ==="

# 等待資料庫就緒
echo "等待資料庫連線..."
while ! python manage.py check --database default > /dev/null 2>&1; do
    echo "資料庫尚未就緒，等待中..."
    sleep 2
done
echo "資料庫連線成功！"

# 執行資料庫遷移
echo "執行資料庫遷移..."
python manage.py migrate --noinput

# 檢查是否需要載入假資料
echo "檢查是否需要載入 Demo 資料..."
export DJANGO_SETTINGS_MODULE=config.settings.development
PRODUCT_COUNT=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()
from apps.products.models import Product
print(Product.objects.count())
" 2>/dev/null || echo "0")

if [ "$PRODUCT_COUNT" = "0" ]; then
    echo "資料庫為空，產生假資料..."
    python manage.py seed_data
    echo "假資料產生完成！"
    echo ""
    echo "=== 測試帳號資訊 ==="
    echo "管理員: admin / admin123"
    echo "台北店長: manager_tpe / demo123"
    echo "收銀員: cashier01 / demo123"
    echo "===================="
else
    echo "資料庫已有資料 (商品數: $PRODUCT_COUNT)，跳過載入。"
fi

# 啟動 Django 服務
echo "啟動 Django 開發伺服器..."
exec python manage.py runserver 0.0.0.0:8000
