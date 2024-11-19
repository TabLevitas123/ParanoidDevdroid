# tests/performance/memory_leak_detector.py

import asyncio
import time
from datetime import datetime, timedelta
import psutil
import gc
import tracemalloc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import json
from pathlib import Path
from collections import defaultdict

from utils.logger import CustomLogger

logger = CustomLogger("memory_leak_detector", "memory.log")

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: float
    total_memory: int
    used_memory: int
    peak_memory: int
    num_objects: int
    num_traceback_entries: int
    top_allocations: List[Tuple[str, int]]  # (traceback, size)

@dataclass
class LeakReport:
    """Memory leak analysis report"""
    leak_detected: bool
    confidence: float  # 0.0 to 1.0
    growth_rate: float  # bytes per second
    problematic_traces: List[Dict[str, Any]]
    duration: float
    peak_memory: int
    baseline_memory: int

class MemoryLeakDetector:
    """Detects potential memory leaks during endurance testing"""
    
    def __init__(
        self,
        sampling_interval: float = 60.0,  # 1 minute
        history_size: int = 60,  # 1 hour of minute samples
        leak_threshold: float = 0.05  # 5% growth per hour
    ):
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        self.leak_threshold = leak_threshold
        
        # Memory tracking
        self.snapshots: List[MemorySnapshot] = []
        self.baseline_memory: Optional[int] = None
        self.peak_memory: int = 0
        
        # Trace tracking
        self.trace_history: Dict[str, List[int]] = defaultdict(list)
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistical analysis
        self.growth_samples: List[float] = []
        self.analysis_window = 10  # number of samples for trend analysis

    async def start_monitoring(self):
        """Start memory leak detection"""
        if self.is_monitoring:
            return
            
        # Initialize tracemalloc
        tracemalloc.start(25)  # Keep 25 frames in tracebacks
        
        # Force garbage collection
        gc.collect()
        
        # Take baseline snapshot
        self.baseline_memory = psutil.Process().memory_info().rss
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitor_memory())
        logger.info("Memory leak detection started")

    async def stop_monitoring(self) -> LeakReport:
        """Stop monitoring and generate report"""
        if not self.is_monitoring:
            return self._generate_empty_report()
            
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Generate final report
        report = await self._analyze_memory_usage()
        
        # Stop tracemalloc
        tracemalloc.stop()
        
        logger.info("Memory leak detection stopped")
        return report

    async def _monitor_memory(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Take snapshot
                snapshot = await self._take_snapshot()
                self.snapshots.append(snapshot)
                
                # Update peak memory
                self.peak_memory = max(self.peak_memory, snapshot.used_memory)
                
                # Trim history if needed
                if len(self.snapshots) > self.history_size:
                    self.snapshots = self.snapshots[-self.history_size:]
                
                # Calculate memory growth
                if len(self.snapshots) >= 2:
                    growth = (self.snapshots[-1].used_memory - 
                            self.snapshots[-2].used_memory) / self.sampling_interval
                    self.growth_samples.append(growth)
                    
                    # Trim growth samples
                    if len(self.growth_samples) > self.history_size:
                        self.growth_samples = self.growth_samples[-self.history_size:]
                    
                    # Check for potential leaks
                    await self._check_for_leaks()
                
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring memory: {str(e)}")
                await asyncio.sleep(self.sampling_interval)

    async def _take_snapshot(self) -> MemorySnapshot:
        """Take memory usage snapshot"""
        # Get process memory info
        memory_info = psutil.Process().memory_info()
        
        # Get tracemalloc snapshot
        snapshot = tracemalloc.take_snapshot()
        
        # Get top memory allocations
        top_stats = snapshot.statistics('traceback')
        top_allocations = [
            (str(stat.traceback), stat.size)
            for stat in top_stats[:10]  # Keep top 10 allocations
        ]
        
        # Update trace history
        for trace, size in top_allocations:
            self.trace_history[trace].append(size)
            # Keep only recent history
            if len(self.trace_history[trace]) > self.history_size:
                self.trace_history[trace] = self.trace_history[trace][-self.history_size:]
        
        return MemorySnapshot(
            timestamp=time.time(),
            total_memory=memory_info.rss,
            used_memory=memory_info.rss - (self.baseline_memory or 0),
            peak_memory=self.peak_memory,
            num_objects=len(gc.get_objects()),
            num_traceback_entries=len(top_stats),
            top_allocations=top_allocations
        )

    async def _check_for_leaks(self):
        """Check recent memory usage for potential leaks"""
        if len(self.growth_samples) < self.analysis_window:
            return
            
        # Calculate recent growth trend
        recent_growth = self.growth_samples[-self.analysis_window:]
        growth_rate = np.mean(recent_growth)
        
        # Calculate hourly growth rate as percentage
        hourly_growth_percent = (growth_rate * 3600) / self.baseline_memory * 100
        
        if hourly_growth_percent > self.leak_threshold:
            # Analyze which traces are growing
            growing_traces = []
            for trace, sizes in self.trace_history.items():
                if len(sizes) >= self.analysis_window:
                    recent_sizes = sizes[-self.analysis_window:]
                    size_growth = (recent_sizes[-1] - recent_sizes[0]) / 
                                (self.sampling_interval * self.analysis_window)
                    if size_growth > 0:
                        growing_traces.append({
                            'trace': trace,
                            'growth_rate': size_growth,
                            'current_size': recent_sizes[-1]
                        })
            
            if growing_traces:
                logger.warning(
                    f"Potential memory leak detected! "
                    f"Hourly growth rate: {hourly_growth_percent:.2f}%"
                )
                for trace in sorted(
                    growing_traces,
                    key=lambda x: x['growth_rate'],
                    reverse=True
                )[:3]:
                    logger.warning(
                        f"Growing allocation:\n"
                        f"Rate: {trace['growth_rate']:.2f} bytes/sec\n"
                        f"Size: {trace['current_size']} bytes\n"
                        f"Trace:\n{trace['trace']}"
                    )

    async def _analyze_memory_usage(self) -> LeakReport:
        """Analyze memory usage patterns for leaks"""
        if not self.snapshots:
            return self._generate_empty_report()
        
        duration = self.snapshots[-1].timestamp - self.snapshots[0].timestamp
        
        # Calculate memory growth trend
        growth_rate = 0
        leak_detected = False
        confidence = 0.0
        problematic_traces = []
        
        if len(self.snapshots) >= 2:
            # Calculate overall growth rate
            memory_changes = [
                (s2.used_memory - s1.used_memory) / (s2.timestamp - s1.timestamp)
                for s1, s2 in zip(self.snapshots[:-1], self.snapshots[1:])
            ]
            growth_rate = np.mean(memory_changes)
            
            # Calculate growth stability
            growth_std = np.std(memory_changes)
            stability = 1 - min(1, growth_std / (abs(growth_rate) + 1e-6))
            
            # Determine if there's a leak
            hourly_growth_percent = (growth_rate * 3600) / self.baseline_memory * 100
            leak_detected = hourly_growth_percent > self.leak_threshold
            
            # Calculate confidence based on:
            # 1. Number of samples
            # 2. Growth stability
            # 3. Growth rate relative to threshold
            samples_confidence = min(1, len(self.snapshots) / self.history_size)
            threshold_confidence = min(1, hourly_growth_percent / self.leak_threshold)
            confidence = (samples_confidence * 0.3 + 
                        stability * 0.4 +
                        threshold_confidence * 0.3)
            
            # Find problematic memory allocations
            if leak_detected:
                for trace, sizes in self.trace_history.items():
                    if len(sizes) >= 2:
                        size_growth = (sizes[-1] - sizes[0]) / (
                            self.snapshots[-1].timestamp - self.snapshots[0].timestamp
                        )
                        if size_growth > 0:
                            problematic_traces.append({
                                'trace': trace,
                                'growth_rate': size_growth,
                                'total_growth': sizes[-1] - sizes[0],
                                'current_size': sizes[-1],
                                'contribution': size_growth / growth_rate
                            })
                
                # Sort by contribution to overall growth
                problematic_traces.sort(
                    key=lambda x: x['contribution'],
                    reverse=True
                )
        
        return LeakReport(
            leak_detected=leak_detected,
            confidence=confidence,
            growth_rate=growth_rate,
            problematic_traces=problematic_traces[:10],  # Top 10 traces
            duration=duration,
            peak_memory=self.peak_memory,
            baseline_memory=self.baseline_memory or 0
        )

    def _generate_empty_report(self) -> LeakReport:
        """Generate empty report when no data available"""
        return LeakReport(
            leak_detected=False,
            confidence=0.0,
            growth_rate=0.0,
            problematic_traces=[],
            duration=0.0,
            peak_memory=0,
            baseline_memory=0
        )

    def save_report(self, report: LeakReport, filepath: str):
        """Save leak analysis report to file"""
        report_data = {
            'summary': {
                'leak_detected': report.leak_detected,
                'confidence': report.confidence,
                'growth_rate': report.growth_rate,
                'duration_hours': report.duration / 3600,
                'peak_memory_mb': report.peak_memory / (1024 * 1024),
                'baseline_memory_mb': report.baseline_memory / (1024 * 1024)
            },
            'memory_usage': {
                'samples': [
                    {
                        'timestamp': snapshot.timestamp,
                        'used_memory_mb': snapshot.used_memory / (1024 * 1024),
                        'num_objects': snapshot.num_objects
                    }
                    for snapshot in self.snapshots
                ]
            },
            'problematic_traces': [
                {
                    'trace': trace['trace'],
                    'growth_rate_mb': trace['growth_rate'] / (1024 * 1024),
                    'total_growth_mb': trace['total_growth'] / (1024 * 1024),
                    'current_size_mb': trace['current_size'] / (1024 * 1024),
                    'contribution': trace['contribution']
                }
                for trace in report.problematic_traces
            ]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Memory leak report saved to {filepath}")

async def run_leak_detection(duration: int = 3600):
    """Run memory leak detection"""
    detector = MemoryLeakDetector()
    
    try:
        await detector.start_monitoring()
        
        # Monitor for specified duration
        await asyncio.sleep(duration)
        
        # Generate report
        report = await detector.stop_monitoring()
        
        # Save report
        detector.save_report(
            report,
            f"test/reports/memory_leak_report_{int(time.time())}.json"
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Memory leak detection failed: {str(e)}")
        return detector._generate_empty_report()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run memory leak detection")
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Monitoring duration in seconds"
    )
    
    args = parser.parse_args()
    
    report = asyncio.run(run_leak_detection(args.duration))
    
    if report.leak_detected:
        print(f"\nPotential memory leak detected!")
        print(f"Confidence: {report.confidence:.1%}")
        print(f"Growth rate: {report.growth_rate / 1024:.2f} KB/sec")
    else:
        print("\nNo memory leaks detected")
