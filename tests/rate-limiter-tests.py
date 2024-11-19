# tests/performance/rate_limiter_tests.py

import asyncio
import time
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
import statistics

from utils.logger import CustomLogger
from tests.test_db import TestDatabase
from tests.test_config import TestData

logger = CustomLogger("rate_limiter_tests", "rate_limiter.log")

@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int
    window_seconds: int
    burst_size: Optional[int] = None

class RateLimiterTests:
    """Tests for rate limiting functionality"""
    
    def __init__(self):
        self.db = TestDatabase()
        
        # Rate limit configurations
        self.rate_limits = {
            "global": RateLimit(1000, 3600),  # 1000 requests per hour
            "user": RateLimit(100, 60),       # 100 requests per minute
            "ip": RateLimit(50, 60),          # 50 requests per minute
            "endpoint": {
                "create_agent": RateLimit(10, 60),    # 10 agent creations per minute
                "token_transfer": RateLimit(20, 60),  # 20 transfers per minute
                "ai_request": RateLimit(30, 60, 5)    # 30 AI requests per minute, burst of 5
            }
        }
        
        # Request tracking
        self.request_history: Dict[str, List[datetime]] = {}
        self.violations: List[Dict[str, Any]] = []

    async def setup(self):
        """Setup test environment"""
        self.db.setup()
        
        # Create rate limiting tables
        self.db.cursor.executescript("""
            -- Rate limit tracking
            CREATE TABLE IF NOT EXISTS rate_limit_tracking (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,  -- 'user', 'ip', 'endpoint'
                entity_id TEXT NOT NULL,    -- user_id, ip_address, endpoint_name
                request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_count INTEGER DEFAULT 1,
                window_start TIMESTAMP
            );
            
            -- Rate limit violations
            CREATE TABLE IF NOT EXISTS rate_limit_violations (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                violation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                limit_type TEXT NOT NULL,
                request_count INTEGER,
                details TEXT
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_rate_tracking_entity 
            ON rate_limit_tracking(entity_type, entity_id, window_start);
            
            CREATE INDEX IF NOT EXISTS idx_rate_violations_entity
            ON rate_limit_violations(entity_type, entity_id, violation_time);
        """)
        
        self.db.conn.commit()
        logger.info("Rate limiter test environment setup complete")

    async def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        logger.info("Testing basic rate limiting...")
        
        # Test user rate limiting
        user_id = str(uuid.uuid4())
        limit = self.rate_limits["user"]
        
        # Make requests up to limit
        for _ in range(limit.requests):
            assert await self._check_rate_limit(
                "user", user_id, limit
            ), "Valid request blocked"
        
        # Verify limit enforcement
        assert not await self._check_rate_limit(
            "user", user_id, limit
        ), "Rate limit not enforced"
        
        # Test rate limit reset
        await asyncio.sleep(limit.window_seconds)
        assert await self._check_rate_limit(
            "user", user_id, limit
        ), "Rate limit not reset"

    async def test_burst_handling(self):
        """Test burst request handling"""
        logger.info("Testing burst request handling...")
        
        endpoint = "ai_request"
        limit = self.rate_limits["endpoint"][endpoint]
        
        # Test burst allowance
        burst_results = await asyncio.gather(*[
            self._check_rate_limit("endpoint", endpoint, limit)
            for _ in range(limit.burst_size or 1)
        ])
        
        assert all(burst_results), "Burst requests blocked"
        
        # Verify burst limit
        assert not await self._check_rate_limit(
            "endpoint", endpoint, limit
        ), "Burst limit not enforced"

    async def test_distributed_rate_limiting(self):
        """Test rate limiting across multiple instances"""
        logger.info("Testing distributed rate limiting...")
        
        # Simulate multiple instances
        instance_count = 3
        user_id = str(uuid.uuid4())
        limit = self.rate_limits["user"]
        
        # Distribute requests across instances
        requests_per_instance = limit.requests // instance_count
        
        async def instance_requests(instance_id: int):
            for _ in range(requests_per_instance):
                success = await self._check_rate_limit(
                    "user", user_id, limit,
                    instance_id=f"instance_{instance_id}"
                )
                if not success:
                    return False
            return True
        
        results = await asyncio.gather(*[
            instance_requests(i) for i in range(instance_count)
        ])
        
        # Verify global limit enforcement
        assert not all(results), "Distributed rate limit not enforced"

    async def test_sliding_window(self):
        """Test sliding window rate limiting"""
        logger.info("Testing sliding window rate limiting...")
        
        endpoint = "token_transfer"
        limit = self.rate_limits["endpoint"][endpoint]
        
        # Fill half the window
        half_requests = limit.requests // 2
        for _ in range(half_requests):
            await self._check_rate_limit("endpoint", endpoint, limit)
        
        # Wait for half the window
        await asyncio.sleep(limit.window_seconds / 2)
        
        # Should allow more requests
        assert await self._check_rate_limit(
            "endpoint", endpoint, limit
        ), "Sliding window not working"

    async def test_cleanup(self):
        """Test cleanup of old rate limit data"""
        logger.info("Testing rate limit cleanup...")
        
        # Add old tracking data
        old_time = datetime.utcnow() - timedelta(days=1)
        self.db.cursor.execute("""
            INSERT INTO rate_limit_tracking 
            (id, entity_type, entity_id, request_time, window_start)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            "user",
            "test_user",
            old_time.timestamp(),
            old_time.timestamp()
        ))
        
        # Run cleanup
        await self._cleanup_old_data()
        
        # Verify cleanup
        self.db.cursor.execute(
            "SELECT COUNT(*) FROM rate_limit_tracking WHERE request_time < ?",
            (datetime.utcnow() - timedelta(hours=1)).timestamp()
        )
        old_records = self.db.cursor.fetchone()[0]
        assert old_records == 0, "Old data not cleaned up"

    async def _check_rate_limit(
        self,
        entity_type: str,
        entity_id: str,
        limit: RateLimit,
        instance_id: Optional[str] = None
    ) -> bool:
        """Check if request is within rate limit"""
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=limit.window_seconds)
        
        # Get request count in window
        self.db.cursor.execute("""
            SELECT COUNT(*) FROM rate_limit_tracking
            WHERE entity_type = ? 
            AND entity_id = ?
            AND request_time > ?
        """, (entity_type, entity_id, window_start.timestamp()))
        
        count = self.db.cursor.fetchone()[0]
        
        if count >= limit.requests:
            # Log violation
            violation_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO rate_limit_violations
                (id, entity_type, entity_id, limit_type, request_count, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                violation_id,
                entity_type,
                entity_id,
                "basic",
                count,
                f"Limit: {limit.requests}, Instance: {instance_id}"
            ))
            self.db.conn.commit()
            return False
        
        # Record request
        self.db.cursor.execute("""
            INSERT INTO rate_limit_tracking
            (id, entity_type, entity_id, request_time, window_start)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            entity_type,
            entity_id,
            current_time.timestamp(),
            window_start.timestamp()
        ))
        self.db.conn.commit()
        return True

    async def _cleanup_old_data(self):
        """Clean up old rate limit tracking data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        self.db.cursor.execute("""
            DELETE FROM rate_limit_tracking
            WHERE request_time < ?
        """, (cutoff_time.timestamp(),))
        
        self.db.conn.commit()

    async def run_all_tests(self):
        """Run all rate limiter tests"""
        test_methods = [
            self.test_basic_rate_limiting,
            self.test_burst_handling,
            self.test_distributed_rate_limiting,
            self.test_sliding_window,
            self.test_cleanup
        ]
        
        results = []
        for test_method in test_methods:
            try:
                await test_method()
                results.append((test_method.__name__, "PASSED", None))
                logger.info(f"{test_method.__name__} passed")
            except Exception as e:
                results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"{test_method.__name__} failed: {str(e)}")
        
        return results

    async def cleanup(self):
        """Cleanup test environment"""
        self.db.cleanup()
        logger.info("Rate limiter test cleanup complete")

async def run_rate_limiter_tests():
    """Run all rate limiter tests"""
    test_suite = RateLimiterTests()
    try:
        await test_suite.setup()
        results = await test_suite.run_all_tests()
        
        # Print results
        print("\nRate Limiter Test Results:")
        print("=========================")
        for test_name, status, error in results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name}")
            if error:
                print(f"  Error: {error}")
        
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        total = len(results)
        print(f"\nPassed {passed}/{total} tests")
        
        return passed == total
        
    finally:
        await test_suite.cleanup()

if __name__ == "__main__":
    success = asyncio.run(run_rate_limiter_tests())
    import sys
    sys.exit(0 if success else 1)
