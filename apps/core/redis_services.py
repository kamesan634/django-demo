"""
Redis services for the ERP system.
Based on SA_06_Redis快取模組.md specifications.
"""
import json
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


class RedisKeyPrefix:
    """Redis key prefixes according to SA_06 specifications."""
    TOKEN = 'token'
    SESSION = 'session'
    ONLINE = 'online'
    CACHE = 'cache'
    LOCK = 'lock'
    RATELIMIT = 'ratelimit'
    NOTIFY = 'notify'
    AUDIT = 'audit'
    STATS = 'stats'


class TokenBlacklistService:
    """
    JWT Token blacklist service.
    F06-001: JWT Token 黑名單
    """
    KEY_PREFIX = f'{RedisKeyPrefix.TOKEN}:blacklist'

    @classmethod
    def _get_token_hash(cls, token: str) -> str:
        """Generate hash for token to use as key."""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    @classmethod
    def add_to_blacklist(cls, token: str, user_id: int, ttl_seconds: int = None) -> bool:
        """
        Add token to blacklist.
        BR06-001-01: Token 加入黑名單時，TTL 設定為該 Token 的剩餘有效時間
        """
        try:
            token_hash = cls._get_token_hash(token)
            key = f'{cls.KEY_PREFIX}:{token_hash}'

            # Default TTL to 2 hours if not provided (typical JWT lifetime)
            if ttl_seconds is None:
                ttl_seconds = 7200

            cache.set(key, str(user_id), ttl_seconds)
            logger.info(f"Token added to blacklist for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
            return False

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """
        Check if token is in blacklist.
        BR06-001-02: 每次 API 請求需檢查 Token 是否在黑名單中
        """
        try:
            token_hash = cls._get_token_hash(token)
            key = f'{cls.KEY_PREFIX}:{token_hash}'
            return cache.get(key) is not None
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    @classmethod
    def blacklist_user_tokens(cls, user_id: int) -> bool:
        """
        Blacklist all tokens for a specific user.
        BR06-001-04: 管理員可強制將特定使用者的所有 Token 加入黑名單
        """
        try:
            # Store user-level blacklist flag
            key = f'{cls.KEY_PREFIX}:user:{user_id}'
            cache.set(key, timezone.now().isoformat(), 86400)  # 24 hours
            logger.info(f"All tokens blacklisted for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist user tokens: {e}")
            return False

    @classmethod
    def is_user_blacklisted(cls, user_id: int) -> bool:
        """Check if user has all tokens blacklisted."""
        try:
            key = f'{cls.KEY_PREFIX}:user:{user_id}'
            return cache.get(key) is not None
        except Exception:
            return False


class OnlineStatusService:
    """
    User online status tracking service.
    F06-002: 使用者在線狀態
    """
    ONLINE_USERS_KEY = f'{RedisKeyPrefix.ONLINE}:users'
    SESSION_KEY_PREFIX = f'{RedisKeyPrefix.SESSION}:user'
    SESSION_TTL = 1800  # 30 minutes

    @classmethod
    def user_login(cls, user_id: int, ip: str = None, user_agent: str = None) -> bool:
        """
        Mark user as online on login.
        BR06-002-01: 使用者登入成功後加入在線列表
        """
        try:
            redis_conn = get_redis_connection('default')
            now = timezone.now().isoformat()

            # Add to online users set
            redis_conn.sadd(cls.ONLINE_USERS_KEY, str(user_id))

            # Store session info
            session_key = f'{cls.SESSION_KEY_PREFIX}:{user_id}'
            session_data = {
                'loginTime': now,
                'lastActiveTime': now,
                'ip': ip or '',
                'userAgent': user_agent or ''
            }
            redis_conn.hset(session_key, mapping=session_data)
            redis_conn.expire(session_key, cls.SESSION_TTL)

            logger.info(f"User {user_id} marked as online")
            return True
        except Exception as e:
            logger.error(f"Failed to mark user online: {e}")
            return False

    @classmethod
    def user_logout(cls, user_id: int) -> bool:
        """
        Remove user from online list on logout.
        BR06-002-02: 使用者登出後從在線列表移除
        """
        try:
            redis_conn = get_redis_connection('default')

            # Remove from online users set
            redis_conn.srem(cls.ONLINE_USERS_KEY, str(user_id))

            # Remove session info
            session_key = f'{cls.SESSION_KEY_PREFIX}:{user_id}'
            redis_conn.delete(session_key)

            logger.info(f"User {user_id} marked as offline")
            return True
        except Exception as e:
            logger.error(f"Failed to mark user offline: {e}")
            return False

    @classmethod
    def update_activity(cls, user_id: int) -> bool:
        """
        Update user's last activity time.
        BR06-002-03: 使用者每次 API 請求更新最後活動時間
        """
        try:
            redis_conn = get_redis_connection('default')
            session_key = f'{cls.SESSION_KEY_PREFIX}:{user_id}'

            if redis_conn.exists(session_key):
                now = timezone.now().isoformat()
                redis_conn.hset(session_key, 'lastActiveTime', now)
                redis_conn.expire(session_key, cls.SESSION_TTL)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update user activity: {e}")
            return False

    @classmethod
    def get_online_users(cls) -> List[Dict]:
        """Get list of online users with session info."""
        try:
            redis_conn = get_redis_connection('default')
            user_ids = redis_conn.smembers(cls.ONLINE_USERS_KEY)

            users = []
            for user_id in user_ids:
                user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id
                session_key = f'{cls.SESSION_KEY_PREFIX}:{user_id_str}'
                session_data = redis_conn.hgetall(session_key)

                if session_data:
                    users.append({
                        'userId': int(user_id_str),
                        'loginTime': session_data.get(b'loginTime', b'').decode(),
                        'lastActiveTime': session_data.get(b'lastActiveTime', b'').decode(),
                        'ip': session_data.get(b'ip', b'').decode(),
                    })

            return users
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []

    @classmethod
    def get_online_count(cls) -> int:
        """Get count of online users."""
        try:
            redis_conn = get_redis_connection('default')
            return redis_conn.scard(cls.ONLINE_USERS_KEY)
        except Exception:
            return 0

    @classmethod
    def is_user_online(cls, user_id: int) -> bool:
        """Check if specific user is online."""
        try:
            redis_conn = get_redis_connection('default')
            return redis_conn.sismember(cls.ONLINE_USERS_KEY, str(user_id))
        except Exception:
            return False

    @classmethod
    def cleanup_inactive_users(cls) -> int:
        """
        Remove users who have been inactive for too long.
        BR06-002-04: 超過 30 分鐘無活動視為離線，自動移除
        """
        try:
            redis_conn = get_redis_connection('default')
            user_ids = redis_conn.smembers(cls.ONLINE_USERS_KEY)
            removed_count = 0

            for user_id in user_ids:
                user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id
                session_key = f'{cls.SESSION_KEY_PREFIX}:{user_id_str}'

                if not redis_conn.exists(session_key):
                    redis_conn.srem(cls.ONLINE_USERS_KEY, user_id)
                    removed_count += 1

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} inactive users")

            return removed_count
        except Exception as e:
            logger.error(f"Failed to cleanup inactive users: {e}")
            return 0


class DistributedLockService:
    """
    Distributed lock service using Redis.
    F06-005: 分散式鎖
    """
    KEY_PREFIX = RedisKeyPrefix.LOCK

    @classmethod
    def acquire_lock(
        cls,
        resource: str,
        lock_id: str = None,
        ttl_seconds: int = 10,
        retry_times: int = 3,
        retry_delay: float = 0.1
    ) -> Optional[str]:
        """
        Acquire a distributed lock.
        BR06-005-01: 使用 Redis SETNX 實現互斥鎖
        BR06-005-02: 鎖必須設定 TTL，防止死鎖
        BR06-005-05: 獲取鎖失敗時支援重試機制
        """
        import time

        if lock_id is None:
            lock_id = f'{uuid.uuid4()}'

        key = f'{cls.KEY_PREFIX}:{resource}'

        for attempt in range(retry_times):
            try:
                redis_conn = get_redis_connection('default')
                # Use SET NX EX for atomic operation
                acquired = redis_conn.set(key, lock_id, nx=True, ex=ttl_seconds)

                if acquired:
                    logger.debug(f"Lock acquired for {resource} with id {lock_id}")
                    return lock_id

                if attempt < retry_times - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Failed to acquire lock for {resource}: {e}")
                return None

        logger.warning(f"Failed to acquire lock for {resource} after {retry_times} attempts")
        return None

    @classmethod
    def release_lock(cls, resource: str, lock_id: str) -> bool:
        """
        Release a distributed lock.
        BR06-005-03: 只有持有鎖的執行緒可以釋放鎖
        """
        key = f'{cls.KEY_PREFIX}:{resource}'

        try:
            redis_conn = get_redis_connection('default')
            # Check if we own the lock before releasing
            current_lock_id = redis_conn.get(key)

            if current_lock_id is None:
                return True  # Lock already released

            current_lock_id = current_lock_id.decode() if isinstance(current_lock_id, bytes) else current_lock_id

            if current_lock_id == lock_id:
                redis_conn.delete(key)
                logger.debug(f"Lock released for {resource}")
                return True
            else:
                logger.warning(f"Cannot release lock for {resource}: lock_id mismatch")
                return False
        except Exception as e:
            logger.error(f"Failed to release lock for {resource}: {e}")
            return False

    @classmethod
    def extend_lock(cls, resource: str, lock_id: str, ttl_seconds: int) -> bool:
        """Extend the TTL of an existing lock."""
        key = f'{cls.KEY_PREFIX}:{resource}'

        try:
            redis_conn = get_redis_connection('default')
            current_lock_id = redis_conn.get(key)

            if current_lock_id is None:
                return False

            current_lock_id = current_lock_id.decode() if isinstance(current_lock_id, bytes) else current_lock_id

            if current_lock_id == lock_id:
                redis_conn.expire(key, ttl_seconds)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to extend lock for {resource}: {e}")
            return False


class distributed_lock:
    """
    Context manager / decorator for distributed lock.

    Usage:
        # As context manager
        with distributed_lock('order:number', ttl=5) as lock_id:
            if lock_id:
                # do work
                pass

        # As decorator
        @distributed_lock('order:number', ttl=5)
        def generate_order_number():
            pass
    """

    def __init__(self, resource: str, ttl: int = 10, retry_times: int = 3):
        self.resource = resource
        self.ttl = ttl
        self.retry_times = retry_times
        self.lock_id = None

    def __enter__(self):
        self.lock_id = DistributedLockService.acquire_lock(
            self.resource,
            ttl_seconds=self.ttl,
            retry_times=self.retry_times
        )
        return self.lock_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_id:
            DistributedLockService.release_lock(self.resource, self.lock_id)
        return False

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self as lock_id:
                if lock_id is None:
                    raise Exception(f"Could not acquire lock for {self.resource}")
                return func(*args, **kwargs)
        return wrapper


class CacheService:
    """
    Hot data cache service.
    F06-004: 熱門資料快取
    """
    KEY_PREFIX = RedisKeyPrefix.CACHE
    STATS_KEY_PREFIX = RedisKeyPrefix.STATS

    # Cache TTL configurations (in seconds)
    TTL_CONFIG = {
        'product': 1800,       # 30 minutes
        'products': 300,       # 5 minutes (list)
        'categories': 3600,    # 1 hour
        'suppliers': 3600,     # 1 hour
        'units': 86400,        # 1 day
        'tax_types': 86400,    # 1 day
        'customer_levels': 86400,  # 1 day
        'system_params': 86400,    # 1 day
        'inventory': 300,      # 5 minutes (frequently changing)
        'dropdown': 86400,     # 1 day
    }

    @classmethod
    def _get_cache_key(cls, cache_type: str, identifier: str = None) -> str:
        if identifier:
            return f'{cls.KEY_PREFIX}:{cache_type}:{identifier}'
        return f'{cls.KEY_PREFIX}:{cache_type}'

    @classmethod
    def _get_stats_key(cls, cache_type: str) -> str:
        return f'{cls.STATS_KEY_PREFIX}:cache:{cache_type}'

    @classmethod
    def _record_hit(cls, cache_type: str):
        """Record cache hit for statistics."""
        try:
            redis_conn = get_redis_connection('default')
            stats_key = cls._get_stats_key(cache_type)
            redis_conn.hincrby(stats_key, 'hits', 1)
        except Exception:
            pass

    @classmethod
    def _record_miss(cls, cache_type: str):
        """Record cache miss for statistics."""
        try:
            redis_conn = get_redis_connection('default')
            stats_key = cls._get_stats_key(cache_type)
            redis_conn.hincrby(stats_key, 'misses', 1)
        except Exception:
            pass

    @classmethod
    def get(cls, cache_type: str, identifier: str = None) -> Optional[Any]:
        """
        Get cached data.
        BR06-004-02: 快取未命中時從資料庫載入並寫入快取
        """
        try:
            key = cls._get_cache_key(cache_type, identifier)
            data = cache.get(key)

            if data is not None:
                cls._record_hit(cache_type)
                return json.loads(data) if isinstance(data, str) else data
            else:
                cls._record_miss(cache_type)
                return None
        except Exception as e:
            logger.error(f"Failed to get cache {cache_type}: {e}")
            return None

    @classmethod
    def set(cls, cache_type: str, data: Any, identifier: str = None, ttl: int = None) -> bool:
        """
        Set cached data.
        BR06-004-03: 不同資料類型設定不同 TTL
        """
        try:
            key = cls._get_cache_key(cache_type, identifier)
            if ttl is None:
                ttl = cls.TTL_CONFIG.get(cache_type, 300)

            serialized = json.dumps(data) if not isinstance(data, str) else data
            cache.set(key, serialized, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache {cache_type}: {e}")
            return False

    @classmethod
    def delete(cls, cache_type: str, identifier: str = None) -> bool:
        """
        Delete cached data.
        BR06-004-01: 資料更新時自動清除對應快取
        """
        try:
            key = cls._get_cache_key(cache_type, identifier)
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache {cache_type}: {e}")
            return False

    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            redis_conn = get_redis_connection('default')
            keys = redis_conn.keys(f'*{cls.KEY_PREFIX}:{pattern}*')
            if keys:
                return redis_conn.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete cache pattern {pattern}: {e}")
            return 0

    @classmethod
    def get_stats(cls, cache_type: str = None) -> Dict:
        """
        Get cache statistics.
        BR06-004-04: 記錄 Cache Hit/Miss 比率供監控
        """
        try:
            redis_conn = get_redis_connection('default')

            if cache_type:
                stats_key = cls._get_stats_key(cache_type)
                stats_data = redis_conn.hgetall(stats_key)
                hits = int(stats_data.get(b'hits', 0))
                misses = int(stats_data.get(b'misses', 0))
                total = hits + misses
                hit_rate = f"{(hits / total * 100):.1f}%" if total > 0 else "0%"

                return {
                    cache_type: {
                        'hits': hits,
                        'misses': misses,
                        'hitRate': hit_rate,
                    }
                }
            else:
                # Get stats for all cache types
                all_stats = {}
                for ct in cls.TTL_CONFIG.keys():
                    stats_key = cls._get_stats_key(ct)
                    stats_data = redis_conn.hgetall(stats_key)
                    hits = int(stats_data.get(b'hits', 0))
                    misses = int(stats_data.get(b'misses', 0))
                    total = hits + misses
                    hit_rate = f"{(hits / total * 100):.1f}%" if total > 0 else "0%"

                    all_stats[ct] = {
                        'hits': hits,
                        'misses': misses,
                        'hitRate': hit_rate,
                    }

                return all_stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    @classmethod
    def clear_all(cls) -> bool:
        """Clear all cache data."""
        try:
            redis_conn = get_redis_connection('default')
            keys = redis_conn.keys(f'*{cls.KEY_PREFIX}:*')
            if keys:
                redis_conn.delete(*keys)
            logger.info("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
            return False


def cached(cache_type: str, key_func=None, ttl: int = None):
    """
    Decorator for caching function results.

    Usage:
        @cached('product', key_func=lambda pk: str(pk))
        def get_product(pk):
            return Product.objects.get(pk=pk)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                identifier = key_func(*args, **kwargs)
            else:
                identifier = str(args) if args else None

            # Try to get from cache
            cached_data = CacheService.get(cache_type, identifier)
            if cached_data is not None:
                return cached_data

            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheService.set(cache_type, result, identifier, ttl)
            return result
        return wrapper
    return decorator


class NotificationService:
    """
    Real-time notification service using Redis Pub/Sub.
    F06-006: 即時通知推播
    """
    CHANNEL_PREFIX = RedisKeyPrefix.NOTIFY

    # Channel types
    CHANNEL_ORDER_NEW = 'order:new'
    CHANNEL_INVENTORY_LOW = 'inventory:low'
    CHANNEL_SYSTEM_BROADCAST = 'system:broadcast'
    CHANNEL_USER = 'user'

    @classmethod
    def _get_channel(cls, channel_type: str, user_id: int = None) -> str:
        if user_id:
            return f'{cls.CHANNEL_PREFIX}:{channel_type}:{user_id}'
        return f'{cls.CHANNEL_PREFIX}:{channel_type}'

    @classmethod
    def publish(
        cls,
        channel_type: str,
        title: str,
        content: str,
        data: Dict = None,
        target_users: List[int] = None,
        notification_type: str = None
    ) -> bool:
        """
        Publish a notification message.
        BR06-006-01: 通知訊息透過 Redis Channel 發布
        BR06-006-04: 支援廣播（所有使用者）與定向（特定使用者）通知
        """
        try:
            redis_conn = get_redis_connection('default')

            message = {
                'id': f'msg-{uuid.uuid4()}',
                'type': notification_type or channel_type.upper().replace(':', '_'),
                'title': title,
                'content': content,
                'data': data or {},
                'targetUsers': target_users or [],
                'createdAt': timezone.now().isoformat()
            }

            message_json = json.dumps(message)

            if target_users:
                # Send to specific users
                for user_id in target_users:
                    channel = cls._get_channel(cls.CHANNEL_USER, user_id)
                    redis_conn.publish(channel, message_json)
            else:
                # Broadcast to channel
                channel = cls._get_channel(channel_type)
                redis_conn.publish(channel, message_json)

            logger.info(f"Notification published to {channel_type}: {title}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish notification: {e}")
            return False

    @classmethod
    def notify_new_order(cls, order_id: int, order_no: str, amount: float) -> bool:
        """Send new order notification."""
        return cls.publish(
            cls.CHANNEL_ORDER_NEW,
            title='新訂單通知',
            content=f'訂單 {order_no} 已建立',
            data={
                'orderId': order_id,
                'orderNo': order_no,
                'amount': amount
            },
            notification_type='NEW_ORDER'
        )

    @classmethod
    def notify_low_stock(cls, product_id: int, product_name: str, current_qty: int, min_qty: int) -> bool:
        """Send low stock alert notification."""
        return cls.publish(
            cls.CHANNEL_INVENTORY_LOW,
            title='庫存警示',
            content=f'商品 {product_name} 庫存不足 (目前: {current_qty}, 安全: {min_qty})',
            data={
                'productId': product_id,
                'productName': product_name,
                'currentQty': current_qty,
                'minQty': min_qty
            },
            notification_type='LOW_STOCK'
        )

    @classmethod
    def notify_user(cls, user_id: int, title: str, content: str, data: Dict = None) -> bool:
        """Send notification to specific user."""
        return cls.publish(
            cls.CHANNEL_USER,
            title=title,
            content=content,
            data=data,
            target_users=[user_id],
            notification_type='PERSONAL'
        )

    @classmethod
    def broadcast(cls, title: str, content: str, data: Dict = None) -> bool:
        """Broadcast system-wide notification."""
        return cls.publish(
            cls.CHANNEL_SYSTEM_BROADCAST,
            title=title,
            content=content,
            data=data,
            notification_type='SYSTEM_BROADCAST'
        )


class AuditQueueService:
    """
    Audit log queue service for async processing.
    F06-007: 操作紀錄佇列
    """
    QUEUE_KEY = f'{RedisKeyPrefix.AUDIT}:log:queue'
    DEAD_LETTER_KEY = f'{RedisKeyPrefix.AUDIT}:log:dead'
    STATS_KEY = f'{RedisKeyPrefix.AUDIT}:log:stats'

    MAX_QUEUE_SIZE = 10000  # BR06-007-04: 佇列長度超過 10000 筆觸發告警
    BATCH_SIZE = 100  # BR06-007-03: 每次最多處理 100 筆記錄

    @classmethod
    def push(
        cls,
        user_id: int,
        username: str,
        action: str,
        module: str,
        target_id: str = None,
        target_type: str = None,
        old_value: Dict = None,
        new_value: Dict = None,
        ip: str = None,
        user_agent: str = None
    ) -> bool:
        """
        Push audit log to queue.
        BR06-007-01: 操作日誌先 LPUSH 至 Redis List
        """
        try:
            redis_conn = get_redis_connection('default')

            log_entry = {
                'id': f'audit-{uuid.uuid4()}',
                'userId': user_id,
                'username': username,
                'action': action,
                'module': module,
                'targetId': target_id,
                'targetType': target_type,
                'oldValue': json.dumps(old_value) if old_value else None,
                'newValue': json.dumps(new_value) if new_value else None,
                'ip': ip,
                'userAgent': user_agent,
                'createdAt': timezone.now().isoformat()
            }

            redis_conn.lpush(cls.QUEUE_KEY, json.dumps(log_entry))
            redis_conn.hincrby(cls.STATS_KEY, 'totalPushed', 1)

            # Check queue size for alerting
            queue_size = redis_conn.llen(cls.QUEUE_KEY)
            if queue_size > cls.MAX_QUEUE_SIZE:
                logger.warning(f"Audit queue size ({queue_size}) exceeds threshold ({cls.MAX_QUEUE_SIZE})")

            return True
        except Exception as e:
            logger.error(f"Failed to push audit log: {e}")
            return False

    @classmethod
    def pop_batch(cls, count: int = None) -> List[Dict]:
        """
        Pop a batch of audit logs from queue.
        BR06-007-02: 背景排程每 5 秒批次處理佇列
        BR06-007-03: 每次最多處理 100 筆記錄
        """
        if count is None:
            count = cls.BATCH_SIZE

        try:
            redis_conn = get_redis_connection('default')
            logs = []

            for _ in range(count):
                # Use RPOP to get oldest entries first
                entry = redis_conn.rpop(cls.QUEUE_KEY)
                if entry is None:
                    break
                logs.append(json.loads(entry))

            return logs
        except Exception as e:
            logger.error(f"Failed to pop audit logs: {e}")
            return []

    @classmethod
    def move_to_dead_letter(cls, log_entry: Dict, error: str) -> bool:
        """
        Move failed log entry to dead letter queue.
        BR06-007-05: 處理失敗的記錄移至 Dead Letter Queue
        """
        try:
            redis_conn = get_redis_connection('default')
            log_entry['error'] = error
            log_entry['failedAt'] = timezone.now().isoformat()
            redis_conn.lpush(cls.DEAD_LETTER_KEY, json.dumps(log_entry))
            redis_conn.hincrby(cls.STATS_KEY, 'totalFailed', 1)
            return True
        except Exception as e:
            logger.error(f"Failed to move to dead letter queue: {e}")
            return False

    @classmethod
    def record_processed(cls, count: int) -> bool:
        """Record successfully processed count."""
        try:
            redis_conn = get_redis_connection('default')
            redis_conn.hincrby(cls.STATS_KEY, 'totalProcessed', count)
            redis_conn.hset(cls.STATS_KEY, 'lastProcessTime', timezone.now().isoformat())
            return True
        except Exception:
            return False

    @classmethod
    def get_queue_size(cls) -> int:
        """Get current queue size."""
        try:
            redis_conn = get_redis_connection('default')
            return redis_conn.llen(cls.QUEUE_KEY)
        except Exception:
            return 0

    @classmethod
    def get_dead_letter_size(cls) -> int:
        """Get dead letter queue size."""
        try:
            redis_conn = get_redis_connection('default')
            return redis_conn.llen(cls.DEAD_LETTER_KEY)
        except Exception:
            return 0

    @classmethod
    def get_stats(cls) -> Dict:
        """Get queue statistics."""
        try:
            redis_conn = get_redis_connection('default')
            stats_data = redis_conn.hgetall(cls.STATS_KEY)

            total_pushed = int(stats_data.get(b'totalPushed', 0))
            total_processed = int(stats_data.get(b'totalProcessed', 0))
            total_failed = int(stats_data.get(b'totalFailed', 0))
            last_process_time = stats_data.get(b'lastProcessTime', b'').decode()

            queue_size = cls.get_queue_size()
            dead_letter_size = cls.get_dead_letter_size()

            # Determine health status
            if queue_size > cls.MAX_QUEUE_SIZE:
                health = 'CRITICAL'
            elif queue_size > cls.MAX_QUEUE_SIZE * 0.8:
                health = 'WARNING'
            else:
                health = 'HEALTHY'

            return {
                'queueSize': queue_size,
                'deadLetterSize': dead_letter_size,
                'stats': {
                    'totalPushed': total_pushed,
                    'totalProcessed': total_processed,
                    'totalFailed': total_failed,
                    'lastProcessTime': last_process_time,
                },
                'health': health
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                'queueSize': 0,
                'deadLetterSize': 0,
                'stats': {},
                'health': 'UNKNOWN'
            }

    @classmethod
    def reprocess_dead_letters(cls, count: int = None) -> int:
        """Reprocess entries from dead letter queue."""
        if count is None:
            count = cls.BATCH_SIZE

        try:
            redis_conn = get_redis_connection('default')
            reprocessed = 0

            for _ in range(count):
                entry = redis_conn.rpop(cls.DEAD_LETTER_KEY)
                if entry is None:
                    break

                log_entry = json.loads(entry)
                # Remove error fields before reprocessing
                log_entry.pop('error', None)
                log_entry.pop('failedAt', None)

                redis_conn.lpush(cls.QUEUE_KEY, json.dumps(log_entry))
                reprocessed += 1

            return reprocessed
        except Exception as e:
            logger.error(f"Failed to reprocess dead letters: {e}")
            return 0


class RateLimitService:
    """
    Rate limit monitoring and management service.
    """
    KEY_PREFIX = RedisKeyPrefix.RATELIMIT
    BLOCKED_STATS_KEY = f'{RedisKeyPrefix.STATS}:ratelimit:blocked'

    @classmethod
    def get_user_status(cls, user_id: int) -> Dict:
        """Get rate limit status for a user."""
        try:
            redis_conn = get_redis_connection('default')
            status = {}

            # Check different throttle scopes
            for scope in ['default_api', 'export', 'report']:
                key_pattern = f'*{cls.KEY_PREFIX}:{scope}:{user_id}*'
                keys = redis_conn.keys(key_pattern)

                if keys:
                    for key in keys:
                        history = cache.get(key.decode() if isinstance(key, bytes) else key)
                        if history:
                            status[scope] = {
                                'requestCount': len(history),
                                'oldestRequest': history[-1] if history else None
                            }

            return status
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {}

    @classmethod
    def record_blocked(cls, identifier: str, scope: str):
        """Record a blocked request for statistics."""
        try:
            redis_conn = get_redis_connection('default')
            redis_conn.hincrby(cls.BLOCKED_STATS_KEY, f'{scope}:{identifier}', 1)
            redis_conn.hincrby(cls.BLOCKED_STATS_KEY, 'total', 1)
        except Exception:
            pass

    @classmethod
    def get_blocked_stats(cls) -> Dict:
        """Get blocked request statistics."""
        try:
            redis_conn = get_redis_connection('default')
            stats = redis_conn.hgetall(cls.BLOCKED_STATS_KEY)
            return {
                k.decode(): int(v)
                for k, v in stats.items()
            }
        except Exception:
            return {}
