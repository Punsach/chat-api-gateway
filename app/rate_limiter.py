# app/rate_limiter.py
import redis
import time
import os
from typing import Tuple

# Use environment variable in production
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class RateLimiter:
    """Token bucket rate limiter with Redis"""
    
    # Tier limits (requests per minute)
    LIMITS = {
        "free": 10,
        "pro": 100,
        "enterprise": 1000,
        "global": 10000  # Global limit across all users
    }
    
    def __init__(self, tier: str, user_id: int):
        self.tier = tier
        self.user_id = user_id
        self.user_key = f"rate_limit:user:{user_id}"
        self.global_key = "rate_limit:global"
    
    def _check_bucket(self, key: str, limit: int) -> Tuple[bool, dict]:
        """
        Token bucket algorithm:
        - Tokens refill at constant rate (limit per minute)
        - Each request consumes 1 token
        - Bucket capacity = limit
        """
        now = time.time()
        
        # Get current state
        pipe = redis_client.pipeline()
        pipe.hgetall(key)
        result = pipe.execute()[0]
        
        if not result:
            # First request - initialize bucket
            tokens = limit - 1
            redis_client.hset(key, mapping={
                "tokens": tokens,
                "last_refill": now
            })
            redis_client.expire(key, 60)  # Auto-cleanup
            return True, {"remaining": tokens, "limit": limit}
        
        # Calculate token refill
        tokens = float(result["tokens"])
        last_refill = float(result["last_refill"])
        time_passed = now - last_refill
        refill_rate = limit / 60.0  # tokens per second
        tokens_to_add = time_passed * refill_rate
        tokens = min(limit, tokens + tokens_to_add)
        
        # Check if request allowed
        if tokens >= 1:
            tokens -= 1
            redis_client.hset(key, mapping={
                "tokens": tokens,
                "last_refill": now
            })
            return True, {"remaining": int(tokens), "limit": limit}
        else:
            return False, {"remaining": 0, "limit": limit}
    
    def check(self) -> Tuple[bool, dict]:
        """Check both user and global rate limits"""
        # Check user limit
        user_limit = self.LIMITS.get(self.tier, self.LIMITS["free"])
        user_allowed, user_info = self._check_bucket(self.user_key, user_limit)
        
        if not user_allowed:
            return False, {
                "error": "User rate limit exceeded",
                "retry_after": 60,
                **user_info
            }
        
        # Check global limit
        global_allowed, global_info = self._check_bucket(
            self.global_key,
            self.LIMITS["global"]
        )
        
        if not global_allowed:
            return False, {
                "error": "Global rate limit exceeded",
                "retry_after": 60,
                **global_info
            }
        
        return True, user_info