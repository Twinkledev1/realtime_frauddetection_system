#!/usr/bin/env python3
"""
Metrics collector for comprehensive system monitoring.
Collects performance, fraud detection, and business metrics.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric data points."""
    name: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)

    def add_point(self, value: float, timestamp: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None):
        """Add a new data point to the series."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=timestamp,
            labels=self.labels,
            metadata=metadata or {}
        )
        self.points.append(point)

    def get_latest(self) -> Optional[MetricPoint]:
        """Get the most recent data point."""
        return self.points[-1] if self.points else None

    def get_average(self, minutes: int = 5) -> Optional[float]:
        """Get average value over the last N minutes."""
        if not self.points:
            return None

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [p for p in self.points if p.timestamp >= cutoff_time]

        if not recent_points:
            return None

        return sum(p.value for p in recent_points) / len(recent_points)


class MetricsCollector:
    """Comprehensive metrics collector for system monitoring."""

    def __init__(self):
        self.metrics: Dict[str, MetricSeries] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)

        # Performance tracking
        self.performance_timers: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)

        # Business metrics
        self.transaction_metrics = {
            'total_transactions': 0,
            'fraudulent_transactions': 0,
            'suspicious_transactions': 0,
            'total_amount': 0.0,
            'average_amount': 0.0,
            'transactions_per_minute': 0,
            'fraud_rate': 0.0
        }

        # System health metrics
        self.system_health = {
            'uptime': 0.0,
            'memory_usage': 0.0,
            'cpu_usage': 0.0,
            'disk_usage': 0.0,
            'active_connections': 0
        }

        # Thread safety
        self._lock = threading.Lock()

        # Start background collection
        self._start_background_collection()

    def _start_background_collection(self):
        """Start background metric collection."""
        def collect_system_metrics():
            while True:
                try:
                    self._collect_system_health()
                    time.sleep(30)  # Collect every 30 seconds
                except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
                    logger.error("Error collecting system metrics: %s", e)
                    time.sleep(60)  # Wait longer on error

        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()

    def record_transaction(self, transaction_data: Dict[str, Any]):
        """Record transaction metrics."""
        with self._lock:
            # Increment counters
            self.transaction_metrics['total_transactions'] += 1
            self.transaction_metrics['total_amount'] += transaction_data.get(
                'amount', 0)

            # Update fraud metrics
            fraud_score = transaction_data.get('fraud_score', 0)
            if fraud_score >= 0.8:
                self.transaction_metrics['fraudulent_transactions'] += 1
            elif fraud_score >= 0.6:
                self.transaction_metrics['suspicious_transactions'] += 1

            # Update averages
            total = self.transaction_metrics['total_transactions']
            if total > 0:
                self.transaction_metrics['average_amount'] = self.transaction_metrics['total_amount'] / total
                self.transaction_metrics['fraud_rate'] = (
                    self.transaction_metrics['fraudulent_transactions'] / total
                )

            # Record time series metrics
            self._record_metric('transaction_count', 1)
            self._record_metric('transaction_amount',
                                transaction_data.get('amount', 0))
            self._record_metric('fraud_score', fraud_score)

    def record_performance(self, operation: str, duration: float, success: bool = True):
        """Record performance metrics."""
        with self._lock:
            # Record timing
            self.performance_timers[operation].append(duration)
            if len(self.performance_timers[operation]) > 100:
                self.performance_timers[operation].pop(0)

            # Record success/failure
            if not success:
                self.error_counts[operation] += 1

            # Record time series metrics
            self._record_metric(f'{operation}_duration', duration)
            self._record_metric(
                f'{operation}_success_rate', 1.0 if success else 0.0)

    def record_system_metric(self, metric_name: str, value: float):
        """Record system-level metrics."""
        with self._lock:
            self._record_metric(metric_name, value)

    def record_error(self, error_type: str, error_message: str = ""):
        """Record error metrics."""
        with self._lock:
            self.error_counts[error_type] += 1
            self._record_metric('error_count', 1, {'error_type': error_type})
            logger.error("Error recorded: %s - %s", error_type, error_message)

    def _record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric data point."""
        if name not in self.metrics:
            self.metrics[name] = MetricSeries(name=name, labels=labels or {})

        self.metrics[name].add_point(value, metadata={'labels': labels or {}})

    def _collect_system_health(self):
        """Collect system health metrics."""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_system_metric('cpu_usage', cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.record_system_metric('memory_usage', memory.percent)

            # Disk usage
            disk = psutil.disk_usage('/')
            self.record_system_metric(
                'disk_usage', (disk.used / disk.total) * 100)

            # Update system health
            self.system_health.update({
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'disk_usage': (disk.used / disk.total) * 100
            })

        except ImportError:
            logger.warning(
                "psutil not available - system metrics not collected")
        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error collecting system health: %s", e)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self._lock:
            # Calculate performance averages
            performance_metrics = {}
            for operation, timings in self.performance_timers.items():
                if timings:
                    performance_metrics[operation] = {
                        'avg_duration': sum(timings) / len(timings),
                        'min_duration': min(timings),
                        'max_duration': max(timings),
                        'total_operations': len(timings),
                        'error_count': self.error_counts.get(operation, 0)
                    }

            # Get recent metric trends
            metric_trends = {}
            for name, series in self.metrics.items():
                latest = series.get_latest()
                if latest:
                    metric_trends[name] = {
                        'current_value': latest.value,
                        'timestamp': latest.timestamp.isoformat(),
                        '5min_average': series.get_average(5),
                        '15min_average': series.get_average(15)
                    }

            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'transaction_metrics': self.transaction_metrics.copy(),
                'system_health': self.system_health.copy(),
                'performance_metrics': performance_metrics,
                'error_counts': dict(self.error_counts),
                'metric_trends': metric_trends,
                'uptime': time.time()  # Process uptime in seconds
            }

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        with self._lock:
            # Determine overall health
            health_indicators = []

            # Check error rates
            total_errors = sum(self.error_counts.values())
            total_operations = sum(len(timings)
                                   for timings in self.performance_timers.values())
            error_rate = (total_errors / total_operations *
                          100) if total_operations > 0 else 0

            if error_rate > 5:
                health_indicators.append('high_error_rate')

            # Check system resources
            if self.system_health.get('cpu_usage', 0) > 80:
                health_indicators.append('high_cpu_usage')

            if self.system_health.get('memory_usage', 0) > 85:
                health_indicators.append('high_memory_usage')

            if self.system_health.get('disk_usage', 0) > 90:
                health_indicators.append('high_disk_usage')

            # Determine overall status
            if not health_indicators:
                status = 'healthy'
            elif len(health_indicators) <= 2:
                status = 'warning'
            else:
                status = 'critical'

            return {
                'status': status,
                'health_indicators': health_indicators,
                'error_rate': error_rate,
                'system_metrics': self.system_health.copy(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

    def export_metrics(self, output_format: str = 'json') -> str:
        """Export metrics in specified format."""
        summary = self.get_metrics_summary()

        if output_format.lower() == 'json':
            return json.dumps(summary, indent=2, default=str)
        elif output_format.lower() == 'prometheus':
            return self._export_prometheus_format()
        else:
            raise ValueError(f"Unsupported export format: {output_format}")

    def _export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Add transaction metrics
        lines.append(
            "# HELP fraud_detection_transactions_total Total number of transactions")
        lines.append("# TYPE fraud_detection_transactions_total counter")
        lines.append(
            f"fraud_detection_transactions_total {self.transaction_metrics['total_transactions']}")

        lines.append(
            "# HELP fraud_detection_fraudulent_transactions_total Total number of fraudulent transactions")
        lines.append(
            "# TYPE fraud_detection_fraudulent_transactions_total counter")
        lines.append(
            f"fraud_detection_fraudulent_transactions_total {self.transaction_metrics['fraudulent_transactions']}")

        # Add system metrics
        lines.append("# HELP fraud_detection_cpu_usage CPU usage percentage")
        lines.append("# TYPE fraud_detection_cpu_usage gauge")
        lines.append(
            f"fraud_detection_cpu_usage {self.system_health.get('cpu_usage', 0)}")

        lines.append(
            "# HELP fraud_detection_memory_usage Memory usage percentage")
        lines.append("# TYPE fraud_detection_memory_usage gauge")
        lines.append(
            f"fraud_detection_memory_usage {self.system_health.get('memory_usage', 0)}")

        return '\n'.join(lines)

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.performance_timers.clear()
            self.error_counts.clear()
            self.transaction_metrics = {
                'total_transactions': 0,
                'fraudulent_transactions': 0,
                'suspicious_transactions': 0,
                'total_amount': 0.0,
                'average_amount': 0.0,
                'transactions_per_minute': 0,
                'fraud_rate': 0.0
            }


# Global metrics collector instance
metrics_collector = MetricsCollector()
