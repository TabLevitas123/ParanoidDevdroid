# tests/performance/load_tests.py

import asyncio
import time
from datetime import datetime, timedelta
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import aiohttp
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import json

from utils.logger import CustomLogger
from tests.test_config import TestData

logger = CustomLogger("load_tests", "performance.log")

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    response_times: List[float]
    error_count: int
    success_count: int
    throughput: float
    cpu_usage: float
    memory_usage: float
    
    @property
    def avg_response_time(self) -> float:
        return statistics.mean(self.response_times) if self.response_times else 0
    
    @property
    def p95_response_time(self) -> float:
        return np.percentile(self.response_times, 95) if self.response_times else 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return (self.success_count / total) * 100 if total > 0 else 0

class LoadGenerator:
    """Generates load for performance testing"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.test_data = TestData()
        
        # Test user credentials
        self.test_users: List[Dict[str, Any]] = []
        self.auth_tokens: Dict[str, str] = {}
        
        # Performance tracking
        self.metrics = PerformanceMetrics(
            response_times=[],
            error_count=0,
            success_count=0,
            throughput=0,
            cpu_usage=0,
            memory_usage=0
        )
    
    async def setup(self):
        """Setup load testing environment"""
        self.session = aiohttp.ClientSession()
        
        # Create test users
        for i in range(10):  # Create 10 test users
            user = await self._create_test_user(f"loadtest_{i}")
            if user:
                self.test_users.append(user)
                # Login user
                token = await self._login_test_user(user)
                if token:
                    self.auth_tokens[user['id']] = token
    
    async def _create_test_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Create a test user"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/users/register",
                json={
                    "username": username,
                    "email": f"{username}@test.com",
                    "password": "Test123!@#"
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to create test user: {str(e)}")
            return None
    
    async def _login_test_user(self, user: Dict[str, Any]) -> Optional[str]:
        """Login test user and get auth token"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/users/login",
                json={
                    "email": user['email'],
                    "password": "Test123!@#"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('token')
                return None
        except Exception as e:
            logger.error(f"Failed to login test user: {str(e)}")
            return None

    async def generate_load(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        requests_per_second: int = 10,
        duration_seconds: int = 60,
        need_auth: bool = True
    ) -> PerformanceMetrics:
        """Generate load for a specific endpoint"""
        start_time = time.time()
        request_count = 0
        tasks = []
        
        # Calculate delay between requests
        delay = 1.0 / requests_per_second
        
        while time.time() - start_time < duration_seconds:
            if need_auth and not self.auth_tokens:
                logger.error("No auth tokens available")
                break
                
            # Create request task
            task = asyncio.create_task(
                self._make_request(
                    endpoint,
                    method,
                    data,
                    self.auth_tokens[self.test_users[request_count % len(self.test_users)]['id']]
                    if need_auth else None
                )
            )
            tasks.append(task)
            request_count += 1
            
            # Wait for delay
            await asyncio.sleep(delay)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate metrics
        end_time = time.time()
        duration = end_time - start_time
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        error_count = len(results) - success_count
        response_times = [r['response_time'] for r in results if isinstance(r, dict)]
        
        return PerformanceMetrics(
            response_times=response_times,
            error_count=error_count,
            success_count=success_count,
            throughput=request_count / duration,
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        )

    async def _make_request(
        self,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        auth_token: Optional[str]
    ) -> Dict[str, Any]:
        """Make a single request and measure performance"""
        start_time = time.time()
        
        try:
            headers = {
                'Authorization': f'Bearer {auth_token}'
            } if auth_token else {}
            
            async with self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                json=data,
                headers=headers
            ) as response:
                await response.json()
                success = 200 <= response.status < 300
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            success = False
        
        return {
            'success': success,
            'response_time': time.time() - start_time
        }

    async def cleanup(self):
        """Cleanup after load testing"""
        if self.session:
            await self.session.close()

class LoadTest:
    """Main load testing class"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.load_generator = LoadGenerator(base_url)
        
        # Test scenarios
        self.scenarios = {
            "user_registration": {
                "endpoint": "/api/users/register",
                "method": "POST",
                "data": lambda i: {
                    "username": f"user_{i}",
                    "email": f"user_{i}@test.com",
                    "password": "Test123!@#"
                },
                "need_auth": False
            },
            "agent_creation": {
                "endpoint": "/api/agents",
                "method": "POST",
                "data": lambda i: {
                    "name": f"Agent_{i}",
                    "description": "Test agent",
                    "capabilities": ["text_generation"]
                },
                "need_auth": True
            },
            "marketplace_listing": {
                "endpoint": "/api/marketplace/listings",
                "method": "GET",
                "data": None,
                "need_auth": False
            }
        }
    
    async def run_load_test(
        self,
        scenario: str,
        requests_per_second: int = 10,
        duration_seconds: int = 60
    ) -> Dict[str, Any]:
        """Run load test for a specific scenario"""
        logger.info(f"Running load test for scenario: {scenario}")
        
        if scenario not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        scenario_config = self.scenarios[scenario]
        
        # Setup
        await self.load_generator.setup()
        
        try:
            # Run test
            metrics = await self.load_generator.generate_load(
                scenario_config["endpoint"],
                scenario_config["method"],
                scenario_config["data"](0) if callable(scenario_config["data"]) else scenario_config["data"],
                requests_per_second,
                duration_seconds,
                scenario_config["need_auth"]
            )
            
            # Format results
            return {
                "scenario": scenario,
                "duration": duration_seconds,
                "requests_per_second": requests_per_second,
                "metrics": {
                    "avg_response_time": metrics.avg_response_time,
                    "p95_response_time": metrics.p95_response_time,
                    "success_rate": metrics.success_rate,
                    "throughput": metrics.throughput,
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "total_requests": metrics.success_count + metrics.error_count,
                    "successful_requests": metrics.success_count,
                    "failed_requests": metrics.error_count
                }
            }
            
        finally:
            # Cleanup
            await self.load_generator.cleanup()

async def run_load_tests():
    """Run all load tests"""
    load_test = LoadTest()
    results = []
    
    scenarios = [
        ("user_registration", 5, 30),  # 5 RPS for 30 seconds
        ("agent_creation", 2, 30),     # 2 RPS for 30 seconds
        ("marketplace_listing", 10, 30) # 10 RPS for 30 seconds
    ]
    
    for scenario, rps, duration in scenarios:
        try:
            result = await load_test.run_load_test(scenario, rps, duration)
            results.append(result)
            
            # Print results
            print(f"\nLoad Test Results - {scenario}")
            print("=" * 50)
            print(f"Duration: {duration} seconds")
            print(f"Target RPS: {rps}")
            print("\nMetrics:")
            for metric, value in result["metrics"].items():
                print(f"{metric}: {value:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to run load test for {scenario}: {str(e)}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(run_load_tests())
    
    # Save results to file
    with open("test/reports/load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nLoad test results saved to test/reports/load_test_results.json")
