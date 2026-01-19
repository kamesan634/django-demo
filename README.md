# 龜三的ERP Demo - Django REST API 專案

![CI](https://github.com/kamesan634/django-demo/actions/workflows/ci.yml/badge.svg)

基於 Python 3.12 + Django 5.2 LTS + Django REST Framework 的零售業 ERP 系統 RESTful API。

## 技能樹 請點以下技能

| 技能 | 版本 | 說明 |
|------|------|------|
| Python | 3.12 | 程式語言 |
| Django | 5.2 LTS | 核心框架 |
| Django REST Framework | 3.15 | API 框架 |
| Simple JWT | 5.3 | JWT 認證 |
| MySQL | 8.4 | 資料庫 |
| Redis | 7 | 快取 / Session |
| Celery | 5.4 | 非同步任務 |
| Docker | - | 容器化佈署 |
| pytest | 8.0 | 測試框架 |

## 功能模組

- **accounts** - 帳號管理（使用者、角色、權限）
- **stores** - 門店管理（門市、倉庫）
- **products** - 商品管理（商品、分類、單位、稅別、條碼）
- **customers** - 客戶管理（會員、會員等級、點數）
- **inventory** - 庫存管理（庫存查詢、異動記錄、調撥）
- **sales** - 銷售管理（POS結帳、訂單、退貨、發票）
- **purchasing** - 採購管理（採購單、進貨、退貨）
- **promotions** - 促銷管理（促銷活動、優惠券）
- **reports** - 報表管理（Dashboard、統計報表、自訂報表）

## 快速開始

### 環境需求

- Docker & Docker Compose
- 或 Python 3.12 + MySQL 8.4 + Redis

### 使用 Docker 佈署（推薦）

```bash
# 啟動所有服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f web

# 執行資料庫遷移
docker-compose exec web python manage.py migrate

# 載入種子資料
docker-compose exec web python manage.py loaddata seeds

# 停止服務
docker-compose down
```

### 本地開發

```bash
# 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安裝依賴
pip install -r requirements.txt

# 執行遷移
python manage.py migrate

# 啟動開發伺服器
python manage.py runserver 8001
```

## Port

| 服務 | Port | 說明 |
|------|------|------|
| Django API | 8001 | RESTful API |
| MySQL | 3301 | 資料庫 |
| Redis | 6381 | 快取 / Session |

## API 文件

啟動服務後，訪問：http://localhost:8001

### 文件入口

| 文件 | 路徑 | 說明 |
|------|------|------|
| Swagger UI | /api/docs/ | 互動式 API 文件 |
| ReDoc | /api/redoc/ | API 文件（閱讀優化） |
| OpenAPI Schema | /api/schema/ | OpenAPI 3.0 規格 |

### 主要 API 端點

| 端點 | 路徑 | 說明 |
|------|------|------|
| 認證 | /api/v1/auth/ | 登入、登出、Token 更新 |
| 使用者 | /api/v1/users/ | 使用者 CRUD |
| 門店 | /api/v1/stores/ | 門店 CRUD |
| 倉庫 | /api/v1/warehouses/ | 倉庫 CRUD |
| 商品 | /api/v1/products/ | 商品 CRUD、匯入匯出 |
| 分類 | /api/v1/categories/ | 分類 CRUD、樹狀結構 |
| 客戶 | /api/v1/customers/ | 客戶 CRUD、點數管理 |
| 庫存 | /api/v1/inventory/ | 庫存查詢、調整、調撥 |
| POS | /api/v1/pos/ | POS 結帳、作廢 |
| 訂單 | /api/v1/orders/ | 訂單查詢 |
| 退貨 | /api/v1/refunds/ | 退貨處理 |
| 發票 | /api/v1/invoices/ | 發票開立、作廢 |
| 採購 | /api/v1/purchase-orders/ | 採購單 CRUD |
| 促銷 | /api/v1/promotions/ | 促銷活動 CRUD |
| 優惠券 | /api/v1/coupons/ | 優惠券 CRUD、驗證 |
| Dashboard | /api/v1/dashboard/ | 儀表板數據 |
| 報表 | /api/v1/reports/ | 各類報表 |

## 測試資訊

### 測試帳號

所有帳號的密碼都是：`password123`

| 帳號 | 角色 | 說明 |
|------|------|------|
| admin | 系統管理員 | 擁有所有權限 |
| manager01 | 門市店長 | 門市管理權限 |
| cashier01 | 收銀員 | 收銀台操作權限 |
| cashier02 | 收銀員 | 收銀台操作權限 |
| warehouse01 | 倉管人員 | 倉庫管理權限 |

### 測試資料

系統已預載以下種子資料：

| 資料類型 | 數量 | 說明 |
|----------|------|------|
| 角色 | 5 | ADMIN, MANAGER, CASHIER, WAREHOUSE, VIEWER |
| 門市/倉庫 | 6 | 1 總公司 + 3 門市 + 2 物流中心 |
| 使用者 | 5 | 含各角色使用者 |
| 商品分類 | 8 | 含階層分類 |
| 計量單位 | 7 | 個、盒、包、瓶、罐、組、公斤 |
| 稅別 | 3 | 應稅5%、零稅率、免稅 |
| 商品 | 10 | 3C 產品、零食、飲料 |
| 會員等級 | 4 | 一般、銀卡、金卡、VIP |
| 會員 | 5 | 不同等級的會員 |
| 供應商 | 4 | 各類供應商 |
| 庫存 | 10 | 不同門市/倉庫的庫存 |
| 促銷活動 | 3 | 各類促銷活動 |
| 優惠券 | 3 | 各類優惠券 |
| 訂單 | 5 | 含不同狀態的訂單 |

## 專案結構

```
django-demo/
├── docker-compose.yml          # Docker Compose 配置
├── Dockerfile                  # Docker 映像配置
├── requirements.txt            # Python 依賴
├── manage.py                   # Django 管理指令
├── pytest.ini                  # pytest 配置
├── config/                     # Django 設定
│   ├── settings/
│   │   ├── base.py            # 基礎設定
│   │   ├── development.py     # 開發環境
│   │   ├── production.py      # 生產環境
│   │   └── testing.py         # 測試環境
│   ├── urls.py                # URL 路由
│   └── wsgi.py
├── apps/                       # Django 應用程式
│   ├── core/                  # 共用元件
│   ├── accounts/              # 帳號模組
│   ├── stores/                # 門店模組
│   ├── products/              # 商品模組
│   ├── customers/             # 客戶模組
│   ├── inventory/             # 庫存模組
│   ├── sales/                 # 銷售模組
│   ├── purchasing/            # 採購模組
│   ├── promotions/            # 促銷模組
│   └── reports/               # 報表模組
├── api/                        # API 版本管理
│   └── v1/
├── tests/                      # 測試程式碼
└── docker/                     # Docker 相關配置
```

## 資料庫連線

### Docker 環境

- Host: `localhost`
- Port: `3301`
- Database: `django_demo_db`
- Username: `root`
- Password: `dev123`

```bash
# 使用 MySQL 客戶端連線
mysql -h localhost -P 3301 -uroot -pdev123 django_demo_db

# 或進入 Docker 容器
docker exec -it django-demo-mysql mysql -uroot -pdev123 django_demo_db
```

## 測試

```bash
# 執行所有測試
pytest

# 執行測試並產生覆蓋率報告
pytest --cov=apps --cov-report=html

# 執行特定模組測試
pytest tests/products/
pytest tests/sales/

# 執行特定測試檔案
pytest tests/reports/test_views.py -v
```

## 健康檢查

```bash
# 檢查 API 狀態
curl http://localhost:8001/api/v1/health/

# 檢查認證
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'
```

## License

MIT License
我一開始以為是Made In Taiwan 咧！(羞
