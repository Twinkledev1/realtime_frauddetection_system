#!/usr/bin/env python3
"""
Load testing framework for performance testing.
Provides comprehensive load testing capabilities for the fraud detection system.
"""

import time
import threading
import asyncio
import aiohttp
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import json
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration."""
    target_url: str = "http://localhost:8080"
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    ramp_down_seconds: int = 10
    request_timeout: int = 30
    max_requests_per_user: int = 1000
    think_time_seconds: float = 1.0


@dataclass
class TestResult:
    """Individual test result."""
    user_id: int
    request_id: str
    endpoint: str
    method: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status_code: int
    success: bool
    error_message: Optional[str] = None
    response_size_bytes: int = 0


@dataclass
class LoadTestSummary:
    """Load test summary statistics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration_seconds: float
    average_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    error_rate_percent: float
    status_code_distribution: Dict[int, int]
    endpoint_performance: Dict[str, Dict[str, Any]]


class LoadTestUser:
    """Simulates a single user making requests."""

    def __init__(self, user_id: int, config: LoadTestConfig):
        self.user_id = user_id
        self.config = config
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.session.timeout = config.request_timeout
        self.running = False

        # Set up session headers
        self.session.headers.update({
            'User-Agent': f'LoadTestUser-{user_id}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def run(self, _, end_time: datetime):
        """Run load test for this user."""
        self.running = True
        current_time = datetime.now(timezone.utc)

        while current_time < end_time and self.running:
            try:
                # Make request
                result = self._make_request()
                self.results.append(result)

                # Think time
                time.sleep(self.config.think_time_seconds)

                current_time = datetime.now(timezone.utc)

            except (ValueError, RuntimeError, AttributeError, TypeError, OSError,
                    requests.RequestException) as e:
                logger.error("User %d error: %s", self.user_id, e)
                break

    def _make_request(self) -> TestResult:
        """Make a single request."""
        start_time = datetime.now(timezone.utc)
        request_id = f"user_{self.user_id}_{int(time.time() * 1000)}"

        # Select endpoint to test
        endpoint = self._select_endpoint()
        url = f"{self.config.target_url}{endpoint}"

        try:
            if endpoint == "/health":
                response = self.session.get(url)
            elif endpoint == "/metrics":
                response = self.session.get(url)
            elif endpoint == "/alerts":
                response = self.session.get(url)
            elif endpoint == "/dashboard":
                response = self.session.get(url)
            else:
                response = self.session.get(url)

            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return TestResult(
                user_id=self.user_id,
                request_id=request_id,
                endpoint=endpoint,
                method="GET",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
                response_size_bytes=len(response.content)
            )

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError,
                requests.RequestException) as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return TestResult(
                user_id=self.user_id,
                request_id=request_id,
                endpoint=endpoint,
                method="GET",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error_message=str(e)
            )

    def _select_endpoint(self) -> str:
        """Select endpoint to test based on distribution."""
        endpoints = [
            ("/health", 0.2),      # 20% health checks
            ("/metrics", 0.3),     # 30% metrics
            ("/alerts", 0.3),      # 30% alerts
            ("/dashboard", 0.2),   # 20% dashboard
        ]

        import random
        rand = random.random()
        cumulative = 0

        for endpoint, probability in endpoints:
            cumulative += probability
            if rand <= cumulative:
                return endpoint

        return "/health"  # Default fallback

    def stop(self):
        """Stop the user."""
        self.running = False
        self.session.close()

    def get_results(self) -> List[TestResult]:
        """Get test results for this user."""
        return self.results.copy()


class AsyncLoadTestUser:
    """Asynchronous load test user for higher concurrency."""

    def __init__(self, user_id: int, config: LoadTestConfig):
        self.user_id = user_id
        self.config = config
        self.results: List[TestResult] = []
        self.running = False

    async def run(self, _, end_time: datetime):
        """Run async load test for this user."""
        self.running = True
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            current_time = datetime.now(timezone.utc)

            while current_time < end_time and self.running:
                try:
                    # Make request
                    result = await self._make_request(session)
                    self.results.append(result)

                    # Think time
                    await asyncio.sleep(self.config.think_time_seconds)

                    current_time = datetime.now(timezone.utc)

                except (ValueError, RuntimeError, AttributeError, TypeError, OSError,
                        aiohttp.ClientError) as e:
                    logger.error("Async user %d error: %s", self.user_id, e)
                    break

    async def _make_request(self, session: aiohttp.ClientSession) -> TestResult:
        """Make a single async request."""
        start_time = datetime.now(timezone.utc)
        request_id = f"async_user_{self.user_id}_{int(time.time() * 1000)}"

        # Select endpoint to test
        endpoint = self._select_endpoint()
        url = f"{self.config.target_url}{endpoint}"

        try:
            async with session.get(url) as response:
                end_time = datetime.now(timezone.utc)
                duration_ms = (end_time - start_time).total_seconds() * 1000

                content = await response.read()

                return TestResult(
                    user_id=self.user_id,
                    request_id=request_id,
                    endpoint=endpoint,
                    method="GET",
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    status_code=response.status,
                    success=200 <= response.status < 300,
                    response_size_bytes=len(content)
                )

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError,
                aiohttp.ClientError) as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return TestResult(
                user_id=self.user_id,
                request_id=request_id,
                endpoint=endpoint,
                method="GET",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error_message=str(e)
            )

    def _select_endpoint(self) -> str:
        """Select endpoint to test based on distribution."""
        endpoints = [
            ("/health", 0.2),
            ("/metrics", 0.3),
            ("/alerts", 0.3),
            ("/dashboard", 0.2),
        ]

        import random
        rand = random.random()
        cumulative = 0

        for endpoint, probability in endpoints:
            cumulative += probability
            if rand <= cumulative:
                return endpoint

        return "/health"

    def stop(self):
        """Stop the user."""
        self.running = False

    def get_results(self) -> List[TestResult]:
        """Get test results for this user."""
        return self.results.copy()


class LoadTestRunner:
    """Main load test runner."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.users: List[LoadTestUser] = []
        self.async_users: List[AsyncLoadTestUser] = []
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def run_sync_test(self) -> LoadTestSummary:
        """Run synchronous load test."""
        logger.info("Starting synchronous load test with %d users",
                    self.config.concurrent_users)

        self.start_time = datetime.now(timezone.utc)
        self.end_time = self.start_time + \
            timedelta(seconds=self.config.duration_seconds)

        # Create users
        self.users = [LoadTestUser(i, self.config)
                      for i in range(self.config.concurrent_users)]

        # Start users with ramp-up
        threads = []
        for i, user in enumerate(self.users):
            # Ramp up delay
            delay = (i / len(self.users)) * self.config.ramp_up_seconds
            thread = threading.Thread(
                target=self._run_user_with_delay, args=(user, delay))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        self.results = []
        for user in self.users:
            self.results.extend(user.get_results())

        return self._generate_summary()

    def run_async_test(self) -> LoadTestSummary:
        """Run asynchronous load test."""
        logger.info("Starting asynchronous load test with %d users",
                    self.config.concurrent_users)

        self.start_time = datetime.now(timezone.utc)
        self.end_time = self.start_time + \
            timedelta(seconds=self.config.duration_seconds)

        # Create async users
        self.async_users = [
            AsyncLoadTestUser(i, self.config)
            for i in range(self.config.concurrent_users)
        ]

        # Run async test
        asyncio.run(self._run_async_test())

        # Collect results
        self.results = []
        for user in self.async_users:
            self.results.extend(user.get_results())

        return self._generate_summary()

    async def _run_async_test(self):
        """Run async test with ramp-up."""
        tasks = []

        for i, user in enumerate(self.async_users):
            # Ramp up delay
            delay = (i / len(self.async_users)) * self.config.ramp_up_seconds
            await asyncio.sleep(delay)

            task = asyncio.create_task(
                user.run(self.start_time, self.end_time))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    def _run_user_with_delay(self, user: LoadTestUser, delay: float):
        """Run user with delay for ramp-up."""
        time.sleep(delay)
        user.run(self.start_time, self.end_time)

    def _generate_summary(self) -> LoadTestSummary:
        """Generate test summary from results."""
        if not self.results:
            return LoadTestSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_duration_seconds=0,
                average_response_time_ms=0,
                median_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                requests_per_second=0,
                error_rate_percent=0,
                status_code_distribution={},
                endpoint_performance={}
            )

        # Basic statistics
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests

        # Duration statistics
        durations = [r.duration_ms for r in self.results]
        average_response_time = statistics.mean(durations)
        median_response_time = statistics.median(durations)

        # Percentile calculations
        sorted_durations = sorted(durations)
        p95_index = int(0.95 * len(sorted_durations))
        p99_index = int(0.99 * len(sorted_durations))

        p95_response_time = sorted_durations[p95_index] if p95_index < len(
            sorted_durations) else 0
        p99_response_time = sorted_durations[p99_index] if p99_index < len(
            sorted_durations) else 0

        min_response_time = min(durations)
        max_response_time = max(durations)

        # Time-based statistics
        total_duration = (self.end_time - self.start_time).total_seconds()
        requests_per_second = total_requests / \
            total_duration if total_duration > 0 else 0
        error_rate_percent = (
            failed_requests / total_requests * 100) if total_requests > 0 else 0

        # Status code distribution
        status_code_distribution = defaultdict(int)
        for result in self.results:
            status_code_distribution[result.status_code] += 1

        # Endpoint performance
        endpoint_performance = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
            'min_response_time': 0,
            'max_response_time': 0
        })

        for result in self.results:
            endpoint = result.endpoint
            endpoint_performance[endpoint]['total_requests'] += 1

            if result.success:
                endpoint_performance[endpoint]['successful_requests'] += 1
            else:
                endpoint_performance[endpoint]['failed_requests'] += 1

        # Calculate endpoint averages
        for endpoint in endpoint_performance:
            endpoint_results = [
                r for r in self.results if r.endpoint == endpoint]
            if endpoint_results:
                endpoint_durations = [r.duration_ms for r in endpoint_results]
                endpoint_performance[endpoint]['average_response_time'] = statistics.mean(
                    endpoint_durations)
                endpoint_performance[endpoint]['min_response_time'] = min(
                    endpoint_durations)
                endpoint_performance[endpoint]['max_response_time'] = max(
                    endpoint_durations)

        return LoadTestSummary(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_duration_seconds=total_duration,
            average_response_time_ms=average_response_time,
            median_response_time_ms=median_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            requests_per_second=requests_per_second,
            error_rate_percent=error_rate_percent,
            status_code_distribution=dict(status_code_distribution),
            endpoint_performance=dict(endpoint_performance)
        )

    def stop(self):
        """Stop all users."""
        for user in self.users:
            user.stop()
        for user in self.async_users:
            user.stop()

    def export_results(self, filename: str):
        """Export results to JSON file."""
        summary = self._generate_summary()

        export_data = {
            'config': {
                'target_url': self.config.target_url,
                'concurrent_users': self.config.concurrent_users,
                'duration_seconds': self.config.duration_seconds,
                'ramp_up_seconds': self.config.ramp_up_seconds
            },
            'summary': {
                'total_requests': summary.total_requests,
                'successful_requests': summary.successful_requests,
                'failed_requests': summary.failed_requests,
                'average_response_time_ms': summary.average_response_time_ms,
                'requests_per_second': summary.requests_per_second,
                'error_rate_percent': summary.error_rate_percent
            },
            'detailed_results': [
                {
                    'user_id': r.user_id,
                    'request_id': r.request_id,
                    'endpoint': r.endpoint,
                    'method': r.method,
                    'start_time': r.start_time.isoformat(),
                    'end_time': r.end_time.isoformat(),
                    'duration_ms': r.duration_ms,
                    'status_code': r.status_code,
                    'success': r.success,
                    'error_message': r.error_message,
                    'response_size_bytes': r.response_size_bytes
                }
                for r in self.results
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)

        logger.info("Results exported to %s", filename)


# Utility functions
def run_quick_load_test(target_url: str = "http://localhost:8080",
                        concurrent_users: int = 5,
                        duration_seconds: int = 30) -> LoadTestSummary:
    """Run a quick load test."""
    config = LoadTestConfig(
        target_url=target_url,
        concurrent_users=concurrent_users,
        duration_seconds=duration_seconds,
        ramp_up_seconds=5
    )

    runner = LoadTestRunner(config)
    return runner.run_sync_test()


def run_stress_test(target_url: str = "http://localhost:8080",
                    concurrent_users: int = 50,
                    duration_seconds: int = 120) -> LoadTestSummary:
    """Run a stress test."""
    config = LoadTestConfig(
        target_url=target_url,
        concurrent_users=concurrent_users,
        duration_seconds=duration_seconds,
        ramp_up_seconds=30,
        think_time_seconds=0.1
    )

    runner = LoadTestRunner(config)
    return runner.run_async_test()
