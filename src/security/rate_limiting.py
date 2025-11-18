#!/usr/bin/env python3
"""
Rate limiting and caching system for API protection.
Provides request rate limiting, caching, and DDoS protection.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_limit: int = 20
    window_size_seconds: int = 60
    cache_ttl_seconds: int = 300  # 5 minutes


@dataclass
class CacheEntry:
    """Cache entry data structure."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))


class RateLimiter:
    """Rate limiting implementation using sliding window."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000))
        self.blocked_ips: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str, endpoint: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed based on rate limits."""
        with self._lock:
            # Check if IP is blocked
            if self._is_ip_blocked(client_id):
                return False, {
                    'allowed': False,
                    'reason': 'ip_blocked',
                    'retry_after': self._get_block_remaining_time(client_id)
                }

            # Create rate limit key
            rate_key = f"{client_id}:{endpoint or 'global'}"

            # Get current time
            now = datetime.now(timezone.utc)

            # Clean old requests
            self._clean_old_requests(rate_key, now)

            # Get request count in current window
            request_count = len(self.request_history[rate_key])

            # Check rate limits
            if request_count >= self.config.requests_per_minute:
                # Block IP for excessive requests
                self._block_ip(client_id)
                return False, {
                    'allowed': False,
                    'reason': 'rate_limit_exceeded',
                    'retry_after': self.config.window_size_seconds,
                    'limit': self.config.requests_per_minute
                }

            # Check burst limit
            if request_count >= self.config.burst_limit:
                return False, {
                    'allowed': False,
                    'reason': 'burst_limit_exceeded',
                    'retry_after': 10,  # 10 seconds for burst
                    'limit': self.config.burst_limit
                }

            # Add request to history
            self.request_history[rate_key].append(now)

            return True, {
                'allowed': True,
                'remaining': self.config.requests_per_minute - request_count - 1,
                'reset_time': (now + timedelta(seconds=self.config.window_size_seconds)).isoformat()
            }

    def _clean_old_requests(self, rate_key: str, now: datetime):
        """Clean old requests from history."""
        if rate_key not in self.request_history:
            return

        cutoff_time = now - timedelta(seconds=self.config.window_size_seconds)

        # Remove old requests
        while (self.request_history[rate_key] and
               self.request_history[rate_key][0] < cutoff_time):
            self.request_history[rate_key].popleft()

    def _is_ip_blocked(self, client_id: str) -> bool:
        """Check if IP is blocked."""
        if client_id not in self.blocked_ips:
            return False

        block_until = self.blocked_ips[client_id]
        if datetime.now(timezone.utc) > block_until:
            # Unblock expired IP
            del self.blocked_ips[client_id]
            return False

        return True

    def _block_ip(self, client_id: str, duration_minutes: int = 30):
        """Block IP for specified duration."""
        block_until = datetime.now(timezone.utc) + \
            timedelta(minutes=duration_minutes)
        self.blocked_ips[client_id] = block_until
        logger.warning(
            "IP %s blocked for %d minutes due to rate limit violation", client_id, duration_minutes)

    def _get_block_remaining_time(self, client_id: str) -> int:
        """Get remaining block time in seconds."""
        if client_id not in self.blocked_ips:
            return 0

        remaining = self.blocked_ips[client_id] - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))

    def get_stats(self, client_id: str = None) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self._lock:
            stats = {
                'total_requests': 0,
                'blocked_ips': len(self.blocked_ips),
                'active_rate_limits': len(self.request_history)
            }

            if client_id:
                rate_key = f"{client_id}:global"
                stats['client_requests'] = len(
                    self.request_history.get(rate_key, []))
                stats['is_blocked'] = self._is_ip_blocked(client_id)

            return stats


class CacheManager:
    """Simple in-memory cache with TTL."""

    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # Check if expired
            if datetime.now(timezone.utc) > entry.expires_at:
                del self.cache[key]
                return None

            # Update access stats
            entry.access_count += 1
            entry.last_accessed = datetime.now(timezone.utc)

            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """Set value in cache with TTL."""
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=expires_at
        )

        with self._lock:
            self.cache[key] = entry

        return True

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = datetime.now(timezone.utc)
            active_entries = [
                entry for entry in self.cache.values() if entry.expires_at > now]

            return {
                'total_entries': len(self.cache),
                'active_entries': len(active_entries),
                'expired_entries': len(self.cache) - len(active_entries),
                'memory_usage_estimate': len(str(self.cache))  # Rough estimate
            }

    def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                self._cleanup_expired()
                time.sleep(60)  # Cleanup every minute
            except (ValueError, RuntimeError, AttributeError, TypeError) as e:
                logger.error("Cache cleanup error: %s", e)
                time.sleep(300)  # Wait 5 minutes on error

    def _cleanup_expired(self):
        """Remove expired cache entries."""
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.expires_at <= now
            ]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.debug("Cleaned up %d expired cache entries",
                             len(expired_keys))


class SecurityMiddleware:
    """Security middleware for request processing."""

    def __init__(self, limiter: RateLimiter, cache_mgr: CacheManager):
        self.rate_limiter = limiter
        self.cache_manager = cache_mgr
        self.request_log: deque = deque(maxlen=10000)

    def process_request(self, client_id: str, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Process incoming request with security checks."""
        start_time = time.time()

        # Log request
        self._log_request(client_id, endpoint, method)

        # Check rate limits
        allowed, rate_limit_info = self.rate_limiter.is_allowed(
            client_id, endpoint)

        if not allowed:
            return {
                'success': False,
                'error': 'rate_limit_exceeded',
                'details': rate_limit_info,
                'processing_time': time.time() - start_time
            }

        # Check cache for GET requests
        cache_key = None
        cached_response = None

        if method.upper() == "GET":
            cache_key = self._generate_cache_key(client_id, endpoint)
            cached_response = self.cache_manager.get(cache_key)

        processing_time = time.time() - start_time

        return {
            'success': True,
            'allowed': True,
            'cached': cached_response is not None,
            'cache_key': cache_key,
            'cached_response': cached_response,
            'rate_limit_info': rate_limit_info,
            'processing_time': processing_time
        }

    def cache_response(self, cache_key: str, response: Any, ttl_seconds: int = 300):
        """Cache response for future requests."""
        if cache_key:
            self.cache_manager.set(cache_key, response, ttl_seconds)

    def _log_request(self, client_id: str, endpoint: str, method: str):
        """Log request for monitoring."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'client_id': client_id,
            'endpoint': endpoint,
            'method': method
        }

        self.request_log.append(log_entry)

    def _generate_cache_key(self, client_id: str, endpoint: str) -> str:
        """Generate cache key for request."""
        key_data = f"{client_id}:{endpoint}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return {
            'rate_limiter_stats': self.rate_limiter.get_stats(),
            'cache_stats': self.cache_manager.get_stats(),
            'recent_requests': len(self.request_log),
            'blocked_ips': len(self.rate_limiter.blocked_ips)
        }


class DDoSProtection:
    """DDoS protection system."""

    def __init__(self, threshold_requests: int = 100, window_seconds: int = 60):
        self.threshold_requests = threshold_requests
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000))
        self.suspicious_ips: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def check_ddos(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check for DDoS attack patterns."""
        with self._lock:
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(seconds=self.window_seconds)

            # Clean old requests
            while (self.request_counts[client_id] and
                   self.request_counts[client_id][0] < cutoff_time):
                self.request_counts[client_id].popleft()

            # Add current request
            self.request_counts[client_id].append(now)

            # Check threshold
            request_count = len(self.request_counts[client_id])

            if request_count > self.threshold_requests:
                # Mark as suspicious
                self.suspicious_ips[client_id] = {
                    'first_detected': now,
                    'request_count': request_count,
                    'threshold': self.threshold_requests
                }

                return True, {
                    'ddos_detected': True,
                    'request_count': request_count,
                    'threshold': self.threshold_requests,
                    'client_id': client_id
                }

            return False, {
                'ddos_detected': False,
                'request_count': request_count,
                'threshold': self.threshold_requests
            }

    def get_suspicious_ips(self) -> Dict[str, Dict[str, Any]]:
        """Get list of suspicious IPs."""
        with self._lock:
            return self.suspicious_ips.copy()


# Global instances
rate_limit_config = RateLimitConfig()
rate_limiter = RateLimiter(rate_limit_config)
cache_manager = CacheManager()
security_middleware = SecurityMiddleware(rate_limiter, cache_manager)
ddos_protection = DDoSProtection()
