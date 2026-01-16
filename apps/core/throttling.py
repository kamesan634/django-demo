"""
Custom throttling classes for API rate limiting.
Based on SA_06_Redis快取模組.md specifications.
"""
import time
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle


class RedisRateThrottle(SimpleRateThrottle):
    """
    Base Redis-backed rate throttle with custom headers.
    """
    cache_format = 'ratelimit:%(scope)s:%(ident)s'

    def allow_request(self, request, view):
        """
        Check if request should be allowed and set rate limit headers.
        """
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = cache.get(self.key, [])
        self.now = time.time()

        # Drop any requests from the history which have now passed the throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.num_requests:
            self.throttle_failure()
            return False

        return self.throttle_success()

    def throttle_success(self):
        """
        Inserts the current request's timestamp along with the key
        into the cache.
        """
        self.history.insert(0, self.now)
        cache.set(self.key, self.history, self.duration)
        return True

    def get_rate_limit_headers(self):
        """
        Return rate limit headers for the response.
        """
        return {
            'X-RateLimit-Limit': str(self.num_requests),
            'X-RateLimit-Remaining': str(max(0, self.num_requests - len(self.history))),
            'X-RateLimit-Reset': str(int(self.now + self.duration)),
        }


class DefaultAPIThrottle(RedisRateThrottle):
    """
    Default API throttle: 60 requests per minute.
    BR06-003-01: 預設限制：每分鐘 60 次請求
    """
    scope = 'default_api'
    rate = '60/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class LoginThrottle(RedisRateThrottle):
    """
    Login API throttle: 5 requests per minute (prevent brute force).
    BR06-003-02: 登入 API 限制：每分鐘 5 次（防暴力破解）
    """
    scope = 'login'
    rate = '5/min'

    def get_cache_key(self, request, view):
        # Use IP address for login throttling
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class ExportThrottle(RedisRateThrottle):
    """
    Export API throttle: 10 requests per hour (prevent resource abuse).
    BR06-003-03: 匯出 API 限制：每小時 10 次（防資源濫用）
    """
    scope = 'export'
    rate = '10/hour'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class ReportThrottle(RedisRateThrottle):
    """
    Report API throttle: 10 requests per minute (computation intensive).
    報表 API: 每分鐘 10 次（運算密集）
    """
    scope = 'report'
    rate = '10/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class BurstThrottle(RedisRateThrottle):
    """
    Burst throttle for short-term spikes: 10 requests per second.
    """
    scope = 'burst'
    rate = '10/sec'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class AnonRateThrottle(RedisRateThrottle):
    """
    Anonymous user throttle: 30 requests per minute.
    """
    scope = 'anon'
    rate = '30/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None  # Only throttle anonymous users

        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class UserRateThrottle(RedisRateThrottle):
    """
    Authenticated user throttle: 60 requests per minute.
    """
    scope = 'user'
    rate = '60/min'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {
                'scope': self.scope,
                'ident': request.user.pk
            }
        return None  # Only throttle authenticated users
