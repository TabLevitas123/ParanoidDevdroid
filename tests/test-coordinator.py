# tests/performance/test_coordinator.py

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

from utils.logger import CustomLogger
from tests.performance.resource_monitor import ResourceMonitor
from tests.performance.workload_generator import WorkloadGenerator, WorkloadPattern
from tests.performance.memory_leak_detector import MemoryLeakDetector

logger = CustomLogger("test_coordinator", "endurance.log")

@dataclass
class TestPhase:
    """Configuration for a test phase"""
    name: str
    duration: int  # seconds
    workload_pattern: WorkloadPattern
    success_criteria: Dict[str, Any]

@dataclass
class PhaseResults:
    """Results from a test phase"""
    phase_name: str
    start_time: float
    end_time: float
    workload_metrics: Dict[str, Any]
    resource_metrics: Dict[str, Any]
    memory_metrics: Dict[str, Any]
    success: bool
    failure_reasons: List[str]

class TestCoordinator:
    """Coordinates different components of endurance testing"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
        # Test components
        self.resource_monitor = ResourceMonitor()
        self.workload_generator = WorkloadGenerator(base_url)
        self.memory_leak_detector = MemoryLeakDetector()
        
        # Results storage
        self.phase_results: List[PhaseResults] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        # Test configuration
        self.default_phases = [
            TestPhase(
                name="warmup",
                duration=300,  # 5 minutes
                workload_pattern=WorkloadPattern(
                    name="warmup",
                    users=5,
                    requests_per_user=0.1,
                    duration=300,
                    think_time=(1, 3),
                    distribution="constant"
                ),
                success_criteria={
                    "error_rate_threshold": 0.01,  # 1%
                    "max_response_time": 2.0,      # 2 seconds
                    "min_throughput": 1.0          # 1 request/second
                }
            ),
            TestPhase(
                name="main_test",
                duration=3600,  # 1 hour
                workload_pattern=WorkloadPattern(
                    name="main",
                    users=20,
                    requests_per_user=0.5,
                    duration=3600,
                    think_time=(0.5, 2),
                    distribution="sine"
                ),
                success_criteria={
                    "error_rate_threshold": 0.02,   # 2%
                    "max_response_time": 3.0,       # 3 seconds
                    "min_throughput": 5.0,          # 5 requests/second
                    "max_memory_growth": 10.0,      # 10% per hour
                    "max_cpu_sustained": 80.0       # 80% CPU
                }
            ),
            TestPhase(
                name="cooldown",
                duration=300,  # 5 minutes
                workload_pattern=WorkloadPattern(
                    name="cooldown",
                    users=5,
                    requests_per_user=0.1,
                    duration=300,
                    think_time=(1, 3),
                    distribution="constant"
                ),
                success_criteria={
                    "error_rate_threshold": 0.01,
                    "resource_recovery_time": 60.0  # 1 minute
                }
            )
        ]

    async def setup(self):
        """Setup test environment"""
        try:
            # Start monitors
            await self.resource_monitor.start_monitoring()
            await self.memory_leak_detector.start_monitoring()
            
            # Setup workload generator
            await self.workload_generator.setup()
            
            self.start_time = time.time()
            logger.info("Test coordinator setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup test coordinator: {str(e)}")
            raise

    async def run_phase(self, phase: TestPhase) -> PhaseResults:
        """Run a single test phase"""
        logger.info(f"Starting test phase: {phase.name}")
        
        phase_start = time.time()
        failure_reasons = []
        
        try:
            # Generate workload
            workload_metrics = await self.workload_generator.generate_workload(
                phase.workload_pattern
            )
            
            # Get resource metrics
            resource_metrics = self.resource_monitor.get_metrics_summary()
            
            # Get memory metrics
            memory_report = await self.memory_leak_detector._analyze_memory_usage()
            
            # Check success criteria
            success = True
            
            # Check error rate
            error_rate = (workload_metrics.requests_failed / 
                         workload_metrics.requests_sent)
            if error_rate > phase.success_criteria["error_rate_threshold"]:
                success = False
                failure_reasons.append(
                    f"Error rate {error_rate:.2%} exceeds threshold "
                    f"{phase.success_criteria['error_rate_threshold']:.2%}"
                )
            
            # Check response time
            if workload_metrics.p95_response_time > phase.success_criteria["max_response_time"]:
                success = False
                failure_reasons.append(
                    f"Response time {workload_metrics.p95_response_time:.2f}s exceeds "
                    f"threshold {phase.success_criteria['max_response_time']}s"
                )
            
            # Check throughput
            throughput = (workload_metrics.requests_succeeded / 
                        (time.time() - phase_start))
            if throughput < phase.success_criteria["min_throughput"]:
                success = False
                failure_reasons.append(
                    f"Throughput {throughput:.2f} req/s below threshold "
                    f"{phase.success_criteria['min_throughput']} req/s"
                )
            
            # Check memory growth (if specified)
            if "max_memory_growth" in phase.success_criteria:
                if memory_report.growth_rate > phase.success_criteria["max_memory_growth"]:
                    success = False
                    failure_reasons.append(
                        f"Memory growth {memory_report.growth_rate:.2f}% per hour exceeds "
                        f"threshold {phase.success_criteria['max_memory_growth']}%"
                    )
            
            # Check CPU usage (if specified)
            if "max_cpu_sustained" in phase.success_criteria:
                if resource_metrics["cpu"]["mean"] > phase.success_criteria["max_cpu_sustained"]:
                    success = False
                    failure_reasons.append(
                        f"Sustained CPU usage {resource_metrics['cpu']['mean']:.2f}% exceeds "
                        f"threshold {phase.success_criteria['max_cpu_sustained']}%"
                    )
            
            return PhaseResults(
                phase_name=phase.name,
                start_time=phase_start,
                end_time=time.time(),
                workload_metrics=workload_metrics.__dict__,
                resource_metrics=resource_metrics,
                memory_metrics=memory_report.__dict__,
                success=success,
                failure_reasons=failure_reasons
            )
            
        except Exception as e:
            logger.error(f"Phase {phase.name} failed: {str(e)}")
            return PhaseResults(
                phase_name=phase.name,
                start_time=phase_start,
                end_time=time.time(),
                workload_metrics={},
                resource_metrics={},
                memory_metrics={},
                success=False,
                failure_reasons=[str(e)]
            )

    async def run_test(
        self,
        phases: Optional[List[TestPhase]] = None
    ) -> bool:
        """Run complete endurance test"""
        phases = phases or self.default_phases
        
        try:
            await self.setup()
            
            # Run each phase
            for phase in phases:
                results = await self.run_phase(phase)
                self.phase_results.append(results)
                
                if not results.success:
                    logger.error(f"Phase {phase.name} failed")
                    logger.error("Failure reasons:")
                    for reason in results.failure_reasons:
                        logger.error(f"  - {reason}")
                    return False
                
                logger.info(f"Phase {phase.name} completed successfully")
            
            self.end_time = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            return False
            
        finally:
            await self.cleanup()

    def save_results(self, filepath: str):
        """Save test results to file"""
        if not self.start_time or not self.end_time:
            logger.error("No test results to save")
            return
            
        results = {
            'summary': {
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'end_time': datetime.fromtimestamp(self.end_time).isoformat(),
                'duration': self.end_time - self.start_time,
                'success': all(phase.success for phase in self.phase_results)
            },
            'phases': [
                {
                    'name': phase.phase_name,
                    'duration': phase.end_time - phase.start_time,
                    'success': phase.success,
                    'failure_reasons': phase.failure_reasons,
                    'metrics': {
                        'workload': phase.workload_metrics,
                        'resources': phase.resource_metrics,
                        'memory': phase.memory_metrics
                    }
                }
                for phase in self.phase_results
            ]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Test results saved to {filepath}")

    async def cleanup(self):
        """Cleanup test environment"""
        try:
            await self.resource_monitor.stop_monitoring()
            memory_report = await self.memory_leak_detector.stop_monitoring()
            await self.workload_generator.cleanup()
            
            logger.info("Test coordinator cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

async def run_endurance_test(base_url: str, duration: Optional[int] = None):
    """Run endurance test with default configuration"""
    coordinator = TestCoordinator(base_url)
    
    if duration:
        # Adjust phase durations
        for phase in coordinator.default_phases:
            if phase.name == "main_test":
                phase.duration = duration
                phase.workload_pattern.duration = duration
    
    success = await coordinator.run_test()
    
    # Save results
    coordinator.save_results(
        f"test/reports/endurance_test_{int(time.time())}.json"
    )
    
    return success

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run endurance test")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for testing"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Override main test phase duration (seconds)"
    )
    
    args = parser.parse_args()
    
    success = asyncio.run(run_endurance_test(args.url, args.duration))
    sys.exit(0 if success else 1)
