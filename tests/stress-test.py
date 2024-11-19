# tests/performance/stress_tests.py

import asyncio
import time
from datetime import datetime, timedelta
import statistics
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import aiohttp
import numpy as np
import json
from pathlib import Path

from utils.logger import CustomLogger
from tests.test_config import TestData

logger = CustomLogger("stress_tests", "stress.log")

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_usage: float
    memory_usage: float
    disk_io: Tuple[float, float]  # read_bytes, write_bytes
    network_io: Tuple[float, float]  # sent_bytes, recv_bytes
    open_files: int
    thread_count: int
    timestamp: float

@dataclass
class StressTestResults:
    """Results from stress testing"""
    max_concurrent_users: int
    breaking_point: Optional[int]
    response_times: List[float]
    error_rates: List[float]
    system_metrics: List[SystemMetrics]
    recovery_time: Optional[float]

class StressTest:
    """Stress testing implementation"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_data = TestData()
        
        # Test configuration
        self.start_users = 10
        self.step_users = 10
        self.step_duration = 60  # seconds
        self.max_users = 1000
        self.breaking_point_threshold = 0.9  # 90% success rate threshold
        
        # Metrics tracking
        self.metrics_interval = 1  # second
        self.system_metrics: List[SystemMetrics] = []
        self.initial_metrics: Optional[SystemMetrics] = None
        
        # Resource monitoring
        self.disk_io_old = psutil.disk_io_counters()
        self.network_io_old = psutil.net_io_counters()

    async def setup(self):
        """Setup stress testing environment"""
        self.session = aiohttp.ClientSession()
        self.initial_metrics = await self._collect_system_metrics()
        logger.info("Stress test environment setup complete")

    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # Get current resource usage
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            
            # Calculate IO rates
            disk_io_new = psutil.disk_io_counters()
            network_io_new = psutil.net_io_counters()
            
            disk_read = disk_io_new.read_bytes - self.disk_io_old.read_bytes
            disk_write = disk_io_new.write_bytes - self.disk_io_old.write_bytes
            net_sent = network_io_new.bytes_sent - self.network_io_old.bytes_sent
            net_recv = network_io_new.bytes_recv - self.network_io_old.bytes_recv
            
            self.disk_io_old = disk_io_new
            self.network_io_old = network_io_new
            
            # Get process metrics
            process = psutil.Process()
            open_files = len(process.open_files())
            thread_count = process.num_threads()
            
            return SystemMetrics(
                cpu_usage=cpu,
                memory_usage=memory,
                disk_io=(disk_read, disk_write),
                network_io=(net_sent, net_recv),
                open_files=open_files,
                thread_count=thread_count,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {str(e)}")
            return SystemMetrics(0, 0, (0, 0), (0, 0), 0, 0, time.time())

    async def _monitor_system_resources(self, duration: int):
        """Monitor system resources for a period"""
        end_time = time.time() + duration
        while time.time() < end_time:
            metrics = await self._collect_system_metrics()
            self.system_metrics.append(metrics)
            await asyncio.sleep(self.metrics_interval)

    async def generate_user_load(
        self,
        user_count: int,
        duration: int
    ) -> Tuple[List[float], float]:
        """Generate load with specified number of concurrent users"""
        tasks = []
        start_time = time.time()
        response_times = []
        errors = 0
        
        # Start resource monitoring
        monitor_task = asyncio.create_task(
            self._monitor_system_resources(duration)
        )
        
        # Create user tasks
        for i in range(user_count):
            task = asyncio.create_task(
                self._simulate_user_behavior(i, duration)
            )
            tasks.append(task)
        
        # Wait for all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        await monitor_task
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                errors += 1
            else:
                response_times.extend(result)
        
        error_rate = errors / user_count
        return response_times, error_rate

    async def _simulate_user_behavior(
        self,
        user_id: int,
        duration: int
    ) -> List[float]:
        """Simulate realistic user behavior"""
        response_times = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Simulate user actions
            actions = [
                self._view_marketplace,
                self._create_agent,
                self._make_transaction
            ]
            
            for action in actions:
                try:
                    start_time = time.time()
                    await action(user_id)
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                except Exception as e:
                    logger.error(f"Action failed for user {user_id}: {str(e)}")
                
                # Random delay between actions
                await asyncio.sleep(np.random.uniform(0.1, 1.0))
        
        return response_times

    async def _view_marketplace(self, user_id: int):
        """Simulate marketplace browsing"""
        async with self.session.get(
            f"{self.base_url}/api/marketplace/listings"
        ) as response:
            await response.json()
            if response.status != 200:
                raise Exception(f"Marketplace view failed: {response.status}")

    async def _create_agent(self, user_id: int):
        """Simulate agent creation"""
        async with self.session.post(
            f"{self.base_url}/api/agents",
            json={
                "name": f"Agent_{user_id}_{int(time.time())}",
                "description": "Stress test agent",
                "capabilities": ["text_generation"]
            }
        ) as response:
            await response.json()
            if response.status != 200:
                raise Exception(f"Agent creation failed: {response.status}")

    async def _make_transaction(self, user_id: int):
        """Simulate transaction"""
        async with self.session.post(
            f"{self.base_url}/api/transactions",
            json={
                "amount": 10,
                "recipient": f"user_{user_id + 1}"
            }
        ) as response:
            await response.json()
            if response.status != 200:
                raise Exception(f"Transaction failed: {response.status}")

    async def find_breaking_point(self) -> StressTestResults:
        """Find system breaking point by incrementally increasing load"""
        logger.info("Starting breaking point analysis...")
        
        current_users = self.start_users
        breaking_point = None
        max_users = current_users
        all_response_times = []
        error_rates = []
        
        while current_users <= self.max_users:
            logger.info(f"Testing with {current_users} concurrent users...")
            
            # Generate load
            response_times, error_rate = await self.generate_user_load(
                current_users,
                self.step_duration
            )
            
            all_response_times.extend(response_times)
            error_rates.append(error_rate)
            
            # Check if breaking point reached
            if error_rate > (1 - self.breaking_point_threshold):
                logger.info(f"Breaking point found at {current_users} users")
                breaking_point = current_users
                break
            
            max_users = current_users
            current_users += self.step_users
        
        # Test system recovery
        recovery_time = await self._test_recovery()
        
        return StressTestResults(
            max_concurrent_users=max_users,
            breaking_point=breaking_point,
            response_times=all_response_times,
            error_rates=error_rates,
            system_metrics=self.system_metrics,
            recovery_time=recovery_time
        )

    async def _test_recovery(self) -> Optional[float]:
        """Test system recovery after stress"""
        logger.info("Testing system recovery...")
        
        start_time = time.time()
        max_recovery_time = 300  # 5 minutes
        
        while time.time() - start_time < max_recovery_time:
            try:
                # Make health check request
                async with self.session.get(
                    f"{self.base_url}/health"
                ) as response:
                    if response.status == 200:
                        recovery_time = time.time() - start_time
                        logger.info(f"System recovered after {recovery_time:.2f} seconds")
                        return recovery_time
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        logger.error("System did not recover within timeout")
        return None

    async def cleanup(self):
        """Cleanup after stress testing"""
        if self.session:
            await self.session.close()

    def _generate_report(self, results: StressTestResults) -> str:
        """Generate detailed test report"""
        report = []
        report.append("Stress Test Report")
        report.append("=================")
        report.append(f"Time: {datetime.now().isoformat()}")
        report.append("")
        
        report.append("Load Characteristics:")
        report.append(f"- Maximum Concurrent Users: {results.max_concurrent_users}")
        if results.breaking_point:
            report.append(f"- Breaking Point: {results.breaking_point} users")
        report.append(f"- Average Response Time: {statistics.mean(results.response_times):.2f}s")
        report.append(f"- 95th Percentile Response Time: {np.percentile(results.response_times, 95):.2f}s")
        report.append("")
        
        report.append("Error Rates:")
        for i, rate in enumerate(results.error_rates):
            users = self.start_users + (i * self.step_users)
            report.append(f"- {users} users: {rate*100:.1f}% errors")
        report.append("")
        
        report.append("System Metrics (Peak Values):")
        cpu_peak = max(m.cpu_usage for m in results.system_metrics)
        memory_peak = max(m.memory_usage for m in results.system_metrics)
        report.append(f"- Peak CPU Usage: {cpu_peak:.1f}%")
        report.append(f"- Peak Memory Usage: {memory_peak:.1f}%")
        report.append("")
        
        if results.recovery_time:
            report.append(f"Recovery Time: {results.recovery_time:.2f} seconds")
        else:
            report.append("System did not recover within timeout period")
        
        return "\n".join(report)

async def run_stress_tests():
    """Run complete stress test suite"""
    stress_test = StressTest()
    
    try:
        # Setup
        await stress_test.setup()
        
        # Run tests
        results = await stress_test.find_breaking_point()
        
        # Generate report
        report = stress_test._generate_report(results)
        
        # Save report
        report_dir = Path("test/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"stress_test_report_{int(time.time())}.txt"
        report_file.write_text(report)
        
        # Save raw results
        results_file = report_dir / f"stress_test_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'max_concurrent_users': results.max_concurrent_users,
                'breaking_point': results.breaking_point,
                'response_times': results.response_times,
                'error_rates': results.error_rates,
                'system_metrics': [
                    {
                        'cpu_usage': m.cpu_usage,
                        'memory_usage': m.memory_usage,
                        'disk_io': m.disk_io,
                        'network_io': m.network_io,
                        'open_files': m.open_files,
                        'thread_count': m.thread_count,
                        'timestamp': m.timestamp
                    }
                    for m in results.system_metrics
                ],
                'recovery_time': results.recovery_time
            }, f, indent=2)
        
        print(report)
        print(f"\nDetailed report saved to: {report_file}")
        print(f"Raw results saved to: {results_file}")
        
        return results
        
    finally:
        await stress_test.cleanup()

if __name__ == "__main__":
    asyncio.run(run_stress_tests())
