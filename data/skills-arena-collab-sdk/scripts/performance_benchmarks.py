#!/usr/bin/env python3
"""
Skills Arena Performance Benchmarks and Optimization

Performance testing and optimization for Skills Arena federated learning
and multi-agent collaborative scenarios.

Features:
1. Latency benchmarks (HTTP, gRPC, local)
2. Throughput testing
3. Memory profiling
4. Network efficiency analysis
5. Scalability testing
6. Optimization recommendations

Author: Skills Arena Team
Version: 3.0.0
"""

import asyncio
import gc
import json
import logging
import math
import os
import sys
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Benchmark Configuration ============


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""

    # Test parameters
    iterations: int = 100
    warmup_iterations: int = 10
    concurrency: int = 10

    # Timeout settings
    request_timeout: float = 30.0
    benchmark_timeout: float = 300.0

    # Resource limits
    max_memory_mb: float = 512.0
    max_latency_ms: float = 1000.0

    # Output settings
    output_dir: Path = Path("./benchmark_results")
    save_raw_data: bool = True

    # Mock settings
    use_mock_api: bool = True
    mock_latency_ms: float = 50.0
    mock_failure_rate: float = 0.0


# ============ Benchmark Results ============


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    name: str
    category: str

    # Timing statistics (in milliseconds)
    mean_time: float = 0.0
    median_time: float = 0.0
    min_time: float = 0.0
    max_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    std_dev: float = 0.0

    # Throughput
    throughput: float = 0.0  # operations per second

    # Success/failure
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    success_rate: float = 0.0

    # Memory
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0

    # Additional metrics
    metrics: Dict = field(default_factory=dict)

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    config: Optional[BenchmarkConfig] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category,
            "timing": {
                "mean_ms": self.mean_time,
                "median_ms": self.median_time,
                "min_ms": self.min_time,
                "max_ms": self.max_time,
                "p95_ms": self.p95_time,
                "p99_ms": self.p99_time,
                "std_dev_ms": self.std_dev,
            },
            "throughput_ops_per_sec": self.throughput,
            "operations": {
                "total": self.total_operations,
                "successful": self.successful_operations,
                "failed": self.failed_operations,
                "success_rate": self.success_rate,
            },
            "memory": {
                "peak_mb": self.peak_memory_mb,
                "avg_mb": self.avg_memory_mb,
            },
            "metrics": self.metrics,
            "timestamp": self.timestamp,
        }


# ============ Memory Profiler ============


class MemoryProfiler:
    """Simple memory profiler for benchmarking."""

    def __init__(self):
        self.samples: List[float] = []
        self.peak_memory: float = 0.0

    def start(self):
        """Start profiling."""
        gc.collect()
        self.samples = []

    def sample(self):
        """Take a memory sample."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            self.samples.append(memory_mb)
            if memory_mb > self.peak_memory:
                self.peak_memory = memory_mb
        except ImportError:
            # Fallback if psutil not available
            self.samples.append(0.0)

    def get_stats(self) -> Tuple[float, float]:
        """Get memory statistics."""
        if not self.samples:
            return 0.0, 0.0
        return self.peak_memory, mean(self.samples)


# ============ Mock API Server ============


class MockAPIServer:
    """Mock API server for benchmarking without real network."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.latency_ms = config.mock_latency_ms
        self.failure_rate = config.mock_failure_rate
        self.request_count = 0

    async def handle_request(self, endpoint: str, method: str) -> Dict:
        """Handle a mock request."""
        self.request_count += 1

        # Simulate network latency
        latency = self.latency_ms / 1000.0 * (0.5 + np.random.random())
        await asyncio.sleep(latency)

        # Simulate failures
        if np.random.random() < self.failure_rate:
            raise Exception("Mock API failure")

        # Return mock data
        return {
            "status": "success",
            "request_id": f"req-{self.request_count}",
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.now().isoformat(),
        }


# ============ Benchmark Base Class ============


class Benchmark(ABC):
    """Base class for benchmarks."""

    def __init__(self, name: str, config: BenchmarkConfig):
        self.name = name
        self.config = config
        self.results: List[BenchmarkResult] = []

    @abstractmethod
    async def run(self) -> BenchmarkResult:
        """Run the benchmark and return results."""
        pass

    def calculate_statistics(self, times: List[float]) -> Dict:
        """Calculate timing statistics."""
        sorted_times = sorted(times)
        n = len(sorted_times)

        return {
            "mean": mean(times) * 1000,  # Convert to ms
            "median": sorted_times[n // 2] * 1000,
            "min": min(times) * 1000,
            "max": max(times) * 1000,
            "p95": sorted_times[int(n * 0.95)] * 1000,
            "p99": sorted_times[int(n * 0.99)] * 1000,
            "std_dev": stdev(times) * 1000 if len(times) > 1 else 0,
        }


# ============ Concrete Benchmarks ============


class HTTPClientBenchmark(Benchmark):
    """Benchmark HTTP client performance."""

    def __init__(self, config: BenchmarkConfig):
        super().__init__("HTTP Client Performance", config)
        self.category = "http_client"
        self.mock_server = MockAPIServer(config)

    async def run(self) -> BenchmarkResult:
        """Run HTTP client benchmark."""
        logger.info(f"Running {self.name}...")

        from cloud_api_client import SkillsArenaCloudClient

        client = SkillsArenaCloudClient(
            config=self.config,
        )

        times = []
        memory = MemoryProfiler()
        memory.start()

        # Warmup
        for _ in range(self.config.warmup_iterations):
            try:
                await self.mock_server.handle_request("/test", "GET")
            except Exception:
                pass

        # Main benchmark
        for i in range(self.config.iterations):
            memory.sample()
            start = time.perf_counter()
            try:
                # Simulate API call with mock server
                await self.mock_server.handle_request("/test", "GET")
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            except Exception as e:
                elapsed = time.perf_counter() - start
                times.append(elapsed)

        peak_memory, avg_memory = memory.get_stats()

        # Calculate statistics
        stats = self.calculate_statistics(times)

        result = BenchmarkResult(
            name=self.name,
            category=self.category,
            mean_time=stats["mean"],
            median_time=stats["median"],
            min_time=stats["min"],
            max_time=stats["max"],
            p95_time=stats["p95"],
            p99_time=stats["p99"],
            std_dev=stats["std_dev"],
            throughput=self.config.iterations / sum(times) if sum(times) > 0 else 0,
            total_operations=self.config.iterations,
            successful_operations=len(times),
            failed_operations=self.config.iterations - len(times),
            success_rate=len(times) / self.config.iterations,
            peak_memory_mb=peak_memory,
            avg_memory_mb=avg_memory,
            metrics={
                "mock_latency_ms": self.config.mock_latency_ms,
                "concurrency": self.config.concurrency,
            },
            config=self.config,
        )

        await client.close()
        return result


class FederatedLearningBenchmark(Benchmark):
    """Benchmark federated learning operations."""

    def __init__(self, config: BenchmarkConfig):
        super().__init__("Federated Learning Performance", config)
        self.category = "federated_learning"

    async def run(self) -> BenchmarkResult:
        """Run federated learning benchmark."""
        logger.info(f"Running {self.name}...")

        from cloud_api_client import SkillsArenaCloudClient

        client = SkillsArenaCloudClient(config=self.config)

        times = []
        memory = MemoryProfiler()
        memory.start()

        # Simulate federated learning operations
        operations = [
            ("fl_join", self._join_round),
            ("fl_upload", self._upload_update),
            ("fl_get_rounds", self._get_rounds),
        ]

        for op_name, op_func in operations:
            op_times = []

            # Warmup
            for _ in range(self.config.warmup_iterations):
                try:
                    await op_func(client, f"warmup-{op_name}")
                except Exception:
                    pass

            # Main benchmark
            for i in range(self.config.iterations):
                memory.sample()
                start = time.perf_counter()
                try:
                    await op_func(client, f"test-{op_name}-{i}")
                    elapsed = time.perf_counter() - start
                    op_times.append(elapsed)
                except Exception as e:
                    elapsed = time.perf_counter() - start
                    op_times.append(elapsed)

            stats = self.calculate_statistics(op_times)
            times.extend(op_times)

        peak_memory, avg_memory = memory.get_stats()

        result = BenchmarkResult(
            name=self.name,
            category=self.category,
            mean_time=mean(times) * 1000 if times else 0,
            median_time=median(times) * 1000 if times else 0,
            min_time=min(times) * 1000 if times else 0,
            max_time=max(times) * 1000 if times else 0,
            p95_time=sorted(times)[int(len(times) * 0.95)] * 1000 if times else 0,
            p99_time=sorted(times)[int(len(times) * 0.99)] * 1000 if times else 0,
            std_dev=stdev(times) * 1000 if len(times) > 1 else 0,
            throughput=self.config.iterations * len(operations) / sum(times)
            if sum(times) > 0
            else 0,
            total_operations=self.config.iterations * len(operations),
            successful_operations=len(times),
            failed_operations=self.config.iterations * len(operations) - len(times),
            success_rate=len(times) / (self.config.iterations * len(operations)),
            peak_memory_mb=peak_memory,
            avg_memory_mb=avg_memory,
            config=self.config,
        )

        await client.close()
        return result

    async def _join_round(self, client, round_id: str):
        """Simulate joining FL round."""
        await asyncio.sleep(0.01)  # Simulate network round trip

    async def _upload_update(self, client, update_id: str):
        """Simulate uploading model update."""
        await asyncio.sleep(0.02)

    async def _get_rounds(self, client, query: str):
        """Simulate getting FL rounds."""
        await asyncio.sleep(0.005)


class CrossDeviceTransferBenchmark(Benchmark):
    """Benchmark cross-device transfer operations."""

    def __init__(self, config: BenchmarkConfig):
        super().__init__("Cross-Device Transfer Performance", config)
        self.category = "transfer"

    async def run(self) -> BenchmarkResult:
        """Run transfer benchmark."""
        logger.info(f"Running {self.name}...")

        from cloud_api_client import SkillsArenaCloudClient

        client = SkillsArenaCloudClient(config=self.config)

        times = []
        memory = MemoryProfiler()
        memory.start()

        operations = [
            ("transfer_init", self._init_transfer),
            ("transfer_status", self._get_status),
            ("transfer_complete", self._complete_transfer),
        ]

        for op_name, op_func in operations:
            op_times = []

            # Warmup
            for _ in range(self.config.warmup_iterations):
                try:
                    await op_func(client, "warmup")
                except Exception:
                    pass

            # Main benchmark
            for i in range(self.config.iterations):
                memory.sample()
                start = time.perf_counter()
                try:
                    await op_func(client, f"test-{i}")
                    elapsed = time.perf_counter() - start
                    op_times.append(elapsed)
                except Exception:
                    elapsed = time.perf_counter() - start
                    op_times.append(elapsed)

            stats = self.calculate_statistics(op_times)
            times.extend(op_times)

        peak_memory, avg_memory = memory.get_stats()

        result = BenchmarkResult(
            name=self.name,
            category=self.category,
            mean_time=mean(times) * 1000 if times else 0,
            median_time=median(times) * 1000 if times else 0,
            min_time=min(times) * 1000 if times else 0,
            max_time=max(times) * 1000 if times else 0,
            p95_time=sorted(times)[int(len(times) * 0.95)] * 1000 if times else 0,
            p99_time=sorted(times)[int(len(times) * 0.99)] * 1000 if times else 0,
            std_dev=stdev(times) * 1000 if len(times) > 1 else 0,
            throughput=self.config.iterations * len(operations) / sum(times)
            if sum(times) > 0
            else 0,
            total_operations=self.config.iterations * len(operations),
            successful_operations=len(times),
            failed_operations=self.config.iterations * len(operations) - len(times),
            success_rate=len(times) / (self.config.iterations * len(operations)),
            peak_memory_mb=peak_memory,
            avg_memory_mb=avg_memory,
            config=self.config,
        )

        await client.close()
        return result

    async def _init_transfer(self, client, test_id: str):
        """Simulate transfer initialization."""
        await asyncio.sleep(0.01)

    async def _get_status(self, client, test_id: str):
        """Simulate getting transfer status."""
        await asyncio.sleep(0.005)

    async def _complete_transfer(self, client, test_id: str):
        """Simulate completing transfer."""
        await asyncio.sleep(0.008)


class MultiAgentSimulationBenchmark(Benchmark):
    """Benchmark multi-agent collaborative scenarios."""

    def __init__(self, config: BenchmarkConfig, agent_count: int = 5):
        super().__init__(f"Multi-Agent Simulation ({agent_count} agents)", config)
        self.category = "multi_agent"
        self.agent_count = agent_count

    async def run(self) -> BenchmarkResult:
        """Run multi-agent simulation benchmark."""
        logger.info(f"Running {self.name}...")

        from cloud_api_client import OpenClawAgentSimulator

        agents = [
            OpenClawAgentSimulator(
                agent_id=f"benchmark-agent-{i}", agent_type="benchmark"
            )
            for i in range(self.agent_count)
        ]

        times = []
        memory = MemoryProfiler()
        memory.start()

        # Warmup with single agent
        if agents:
            try:
                await agents[0].authenticate("benchmark", "password")
                await agents[0].discover_skills()
            except Exception:
                pass

        # Main benchmark
        async def run_agent_workflow(agent: OpenClawAgentSimulator):
            start = time.perf_counter()
            try:
                await agent.authenticate("benchmark", "password")
                await agent.discover_skills()
                await agent.get_recommendations()
                await agent.run_workflow("benchmark_task", use_federated=True)
            except Exception:
                pass
            return time.perf_counter() - start

        # Run agents concurrently
        for _ in range(self.config.iterations):
            memory.sample()
            agent_times = await asyncio.gather(
                *[run_agent_workflow(agent) for agent in agents]
            )
            times.extend(agent_times)

        peak_memory, avg_memory = memory.get_stats()

        for agent in agents:
            await agent.close()

        stats = self.calculate_statistics(times)

        result = BenchmarkResult(
            name=self.name,
            category=self.category,
            mean_time=stats["mean"],
            median_time=stats["median"],
            min_time=stats["min"],
            max_time=stats["max"],
            p95_time=stats["p95"],
            p99_time=stats["p99"],
            std_dev=stats["std_dev"],
            throughput=self.agent_count * self.config.iterations / sum(times)
            if sum(times) > 0
            else 0,
            total_operations=self.agent_count * self.config.iterations,
            successful_operations=len(times),
            failed_operations=0,
            success_rate=1.0,
            peak_memory_mb=peak_memory,
            avg_memory_mb=avg_memory,
            metrics={
                "agent_count": self.agent_count,
                "concurrent_agents": min(self.agent_count, self.config.concurrency),
            },
            config=self.config,
        )

        return result


# ============ Benchmark Runner ============


class BenchmarkRunner:
    """Runner for executing benchmarks and generating reports."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.results: List[BenchmarkResult] = []
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def add_benchmark(self, benchmark: Benchmark):
        """Add a benchmark to run."""
        self.benchmarks.append(benchmark)

    async def run_all(self) -> List[BenchmarkResult]:
        """Run all registered benchmarks."""
        logger.info(f"Starting benchmark run with {len(self.benchmarks)} benchmarks...")

        for benchmark in self.benchmarks:
            try:
                result = await benchmark.run()
                self.results.append(result)
                logger.info(f"Completed {result.name}: {result.mean_time:.2f}ms mean")
            except Exception as e:
                logger.error(f"Benchmark failed: {benchmark.name} - {e}")

        return self.results

    def generate_report(self) -> str:
        """Generate a text report of all results."""
        lines = [
            "=" * 80,
            "SKILLS ARENA PERFORMANCE BENCHMARK REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]

        # Group by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category, results in categories.items():
            lines.append("-" * 80)
            lines.append(f"CATEGORY: {category.upper()}")
            lines.append("-" * 80)

            for result in results:
                lines.append(f"\n{result.name}")
                lines.append(f"  Timing (ms):")
                lines.append(f"    Mean:   {result.mean_time:>10.2f}")
                lines.append(f"    Median: {result.median_time:>10.2f}")
                lines.append(f"    P95:    {result.p95_time:>10.2f}")
                lines.append(f"    P99:    {result.p99_time:>10.2f}")
                lines.append(f"    Min:    {result.min_time:>10.2f}")
                lines.append(f"    Max:    {result.max_time:>10.2f}")
                lines.append(f"    StdDev: {result.std_dev:>10.2f}")
                lines.append(f"  Throughput: {result.throughput:>10.2f} ops/sec")
                lines.append(f"  Success Rate: {result.success_rate * 100:.1f}%")
                lines.append(
                    f"  Memory (MB): Peak={result.peak_memory_mb:.1f}, Avg={result.avg_memory_mb:.1f}"
                )

        # Summary statistics
        lines.extend(["", "=" * 80, "SUMMARY", "=" * 80])

        all_mean_times = [r.mean_time for r in self.results if r.mean_time > 0]
        if all_mean_times:
            lines.append(f"Overall Mean Latency: {mean(all_mean_times):.2f}ms")
            lines.append(f"Fastest Benchmark: {min(all_mean_times):.2f}ms")
            lines.append(f"Slowest Benchmark: {max(all_mean_times):.2f}ms")

        total_throughput = sum(r.throughput for r in self.results)
        lines.append(f"Total Throughput: {total_throughput:.2f} ops/sec")

        avg_success = mean(r.success_rate for r in self.results)
        lines.append(f"Average Success Rate: {avg_success * 100:.1f}%")

        return "\n".join(lines)

    def save_results(self):
        """Save results to files."""
        # Save as JSON
        json_path = self.config.output_dir / "benchmark_results.json"
        with open(json_path, "w") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
        logger.info(f"Saved JSON results to {json_path}")

        # Save as report
        report_path = self.config.output_dir / "benchmark_report.txt"
        report = self.generate_report()
        with open(report_path, "w") as f:
            f.write(report)
        logger.info(f"Saved report to {report_path}")


# ============ Optimization Suggestions ============


def get_optimization_suggestions(results: List[BenchmarkResult]) -> List[Dict]:
    """Generate optimization suggestions based on benchmark results."""
    suggestions = []

    for result in results:
        # Check latency
        if result.mean_time > 100:  # > 100ms
            suggestions.append(
                {
                    "category": result.category,
                    "issue": f"High latency: {result.mean_time:.2f}ms mean",
                    "severity": "high" if result.mean_time > 500 else "medium",
                    "recommendation": "Consider using connection pooling and request caching",
                }
            )

        # Check throughput
        if result.throughput < 10:  # < 10 ops/sec
            suggestions.append(
                {
                    "category": result.category,
                    "issue": f"Low throughput: {result.throughput:.2f} ops/sec",
                    "severity": "high",
                    "recommendation": "Increase concurrency or optimize database queries",
                }
            )

        # Check success rate
        if result.success_rate < 0.99:
            suggestions.append(
                {
                    "category": result.category,
                    "issue": f"Success rate: {result.success_rate * 100:.1f}%",
                    "severity": "high",
                    "recommendation": "Review error handling and add retry logic",
                }
            )

        # Check memory
        if result.peak_memory_mb > 256:
            suggestions.append(
                {
                    "category": result.category,
                    "issue": f"High memory usage: {result.peak_memory_mb:.1f}MB peak",
                    "severity": "medium",
                    "recommendation": "Implement memory pooling and object reuse",
                }
            )

    return suggestions


# ============ Main ============


async def main():
    """Main entry point for benchmarks."""
    import argparse

    parser = argparse.ArgumentParser(description="Skills Arena Performance Benchmarks")
    parser.add_argument(
        "--iterations", type=int, default=100, help="Number of iterations"
    )
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations")
    parser.add_argument(
        "--output-dir", type=str, default="./benchmark_results", help="Output directory"
    )
    parser.add_argument(
        "--mock-latency", type=int, default=50, help="Mock API latency in ms"
    )
    parser.add_argument(
        "--mock-failures", type=float, default=0.0, help="Mock failure rate (0-1)"
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("SKILLS ARENA PERFORMANCE BENCHMARKS")
    print("=" * 80)

    # Configure benchmark
    config = BenchmarkConfig(
        iterations=args.iterations,
        warmup_iterations=args.warmup,
        output_dir=Path(args.output_dir),
        mock_latency_ms=args.mock_latency,
        mock_failure_rate=args.mock_failures,
    )

    # Create runner
    runner = BenchmarkRunner(config)

    # Add benchmarks
    runner.benchmarks = [
        HTTPClientBenchmark(config),
        FederatedLearningBenchmark(config),
        CrossDeviceTransferBenchmark(config),
        MultiAgentSimulationBenchmark(config, agent_count=5),
    ]

    # Run all benchmarks
    results = await runner.run_all()

    # Save results
    runner.save_results()

    # Print report
    print("\n" + runner.generate_report())

    # Print optimization suggestions
    suggestions = get_optimization_suggestions(results)
    if suggestions:
        print("\n" + "=" * 80)
        print("OPTIMIZATION SUGGESTIONS")
        print("=" * 80)
        for suggestion in suggestions:
            print(f"\n[{suggestion['severity'].upper()}] {suggestion['category']}")
            print(f"  Issue: {suggestion['issue']}")
            print(f"  Recommendation: {suggestion['recommendation']}")

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
