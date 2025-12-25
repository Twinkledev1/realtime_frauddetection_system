"""
Analytics engine for real-time and batch fraud detection analytics.
"""
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass


from src.data_models.database.repositories import (
    transaction_repo, fraud_score_repo, alert_repo, analytics_repo, redis_repo
)
from src.data_models.schemas.transaction import TransactionEvent, FraudScore as FraudScoreSchema

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsMetrics:
    """Analytics metrics container."""
    metric_name: str
    metric_value: float
    dimension_name: Optional[str] = None
    dimension_value: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class RealTimeAnalytics:
    """Real-time analytics processor."""

    def __init__(self):
        self.metrics_buffer: List[AnalyticsMetrics] = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        self.last_flush = time.time()

    def process_transaction(self, transaction_event: TransactionEvent, fraud_score: FraudScoreSchema) -> Dict[str, Any]:
        """Process a single transaction for real-time analytics."""
        try:
            # Extract transaction data
            transaction = transaction_event.transaction

            # Calculate real-time metrics
            metrics = []

            # Transaction amount metrics
            metrics.append(AnalyticsMetrics(
                metric_name="transaction_amount",
                metric_value=transaction.amount,
                dimension_name="currency",
                dimension_value=transaction.currency
            ))

            # Fraud score metrics
            metrics.append(AnalyticsMetrics(
                metric_name="fraud_score",
                metric_value=fraud_score.score,
                dimension_name="risk_level",
                dimension_value=fraud_score.risk_level
            ))

            # Transaction type metrics
            metrics.append(AnalyticsMetrics(
                metric_name="transaction_count",
                metric_value=1.0,
                dimension_name="transaction_type",
                dimension_value=transaction.transaction_type
            ))

            # Merchant metrics
            if hasattr(transaction, 'merchant_name') and transaction.merchant_name:
                metrics.append(AnalyticsMetrics(
                    metric_name="merchant_transaction_count",
                    metric_value=1.0,
                    dimension_name="merchant_name",
                    dimension_value=transaction.merchant_name
                ))
            elif hasattr(transaction, 'merchant_id') and transaction.merchant_id:
                metrics.append(AnalyticsMetrics(
                    metric_name="merchant_transaction_count",
                    metric_value=1.0,
                    dimension_name="merchant_id",
                    dimension_value=transaction.merchant_id
                ))

            # Location metrics
            if hasattr(transaction, 'location_country') and transaction.location_country:
                metrics.append(AnalyticsMetrics(
                    metric_name="location_transaction_count",
                    metric_value=1.0,
                    dimension_name="country",
                    dimension_value=transaction.location_country
                ))
            elif hasattr(transaction, 'location') and transaction.location and transaction.location.country:
                metrics.append(AnalyticsMetrics(
                    metric_name="location_transaction_count",
                    metric_value=1.0,
                    dimension_name="country",
                    dimension_value=transaction.location.country
                ))

            # Add to buffer
            self.metrics_buffer.extend(metrics)

            # Flush if buffer is full or time interval reached
            self._check_flush()

            # Return real-time insights
            return self._generate_real_time_insights(transaction, fraud_score)

        except (AttributeError, ValueError, TypeError) as e:
            logger.error("Error processing transaction for analytics: %s", e)
            return {}

    def _check_flush(self):
        """Check if metrics buffer should be flushed."""
        current_time = time.time()

        if (len(self.metrics_buffer) >= self.buffer_size or
                current_time - self.last_flush >= self.flush_interval):
            self._flush_metrics()

    def _flush_metrics(self):
        """Flush metrics buffer to database."""
        try:
            for metric in self.metrics_buffer:
                analytics_repo.store_metric(
                    metric_name=metric.metric_name,
                    metric_value=metric.metric_value,
                    dimension_name=metric.dimension_name,
                    dimension_value=metric.dimension_value
                )

            logger.info(
                "Flushed %d metrics to database", len(self.metrics_buffer))
            self.metrics_buffer.clear()
            self.last_flush = time.time()

        except (AttributeError, ValueError, TypeError, RuntimeError) as e:
            logger.error("Error flushing metrics: %s", e)

    def _generate_real_time_insights(self, transaction, fraud_score) -> Dict[str, Any]:
        """Generate real-time insights for a transaction."""
        insights = {
            'transaction_id': transaction.transaction_id,
            'fraud_score': fraud_score.score,
            'risk_level': fraud_score.risk_level,
            'amount_category': self._categorize_amount(transaction.amount),
            'location_risk': self._assess_location_risk(getattr(transaction, 'location_country', None) or (getattr(transaction, 'location', None) and getattr(transaction.location, 'country', None))),
            'merchant_risk': self._assess_merchant_risk(getattr(transaction, 'merchant_name', None) or getattr(transaction, 'merchant_id', None)),
            'time_pattern': self._analyze_time_pattern(transaction.timestamp),
            'overall_risk': self._calculate_overall_risk(transaction, fraud_score)
        }

        return insights

    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amount."""
        if amount < 10:
            return "micro"
        elif amount < 100:
            return "small"
        elif amount < 1000:
            return "medium"
        elif amount < 10000:
            return "large"
        else:
            return "very_large"

    def _assess_location_risk(self, country: Optional[str]) -> str:
        """Assess location-based risk."""
        if not country:
            return "unknown"

        # High-risk countries (example)
        # Replace with actual high-risk countries
        high_risk_countries = ['XX', 'YY', 'ZZ']
        if country in high_risk_countries:
            return "high"

        return "low"

    def _assess_merchant_risk(self, merchant_name: Optional[str]) -> str:
        """Assess merchant-based risk."""
        if not merchant_name:
            return "unknown"

        # High-risk merchant patterns (example)
        high_risk_patterns = ['casino', 'gambling', 'crypto', 'forex']
        merchant_lower = merchant_name.lower()

        for pattern in high_risk_patterns:
            if pattern in merchant_lower:
                return "high"

        return "low"

    def _analyze_time_pattern(self, timestamp: datetime) -> str:
        """Analyze time-based patterns."""
        hour = timestamp.hour

        if 2 <= hour <= 6:
            return "late_night"
        elif 7 <= hour <= 11:
            return "morning"
        elif 12 <= hour <= 17:
            return "afternoon"
        elif 18 <= hour <= 22:
            return "evening"
        else:
            return "night"

    def _calculate_overall_risk(self, transaction, fraud_score) -> str:
        """Calculate overall risk score."""
        risk_factors = []

        # Amount risk
        if transaction.amount > 10000:
            risk_factors.append(0.3)

        # Location risk
        location_country = getattr(transaction, 'location_country', None) or (getattr(
            transaction, 'location', None) and getattr(transaction.location, 'country', None))
        if self._assess_location_risk(location_country) == "high":
            risk_factors.append(0.2)

        # Merchant risk
        merchant_name = getattr(transaction, 'merchant_name', None) or getattr(
            transaction, 'merchant_id', None)
        if self._assess_merchant_risk(merchant_name) == "high":
            risk_factors.append(0.2)

        # Time risk
        if self._analyze_time_pattern(transaction.timestamp) == "late_night":
            risk_factors.append(0.1)

        # Fraud score risk
        risk_factors.append(fraud_score.score * 0.5)

        overall_risk = sum(risk_factors)

        if overall_risk > 0.7:
            return "critical"
        elif overall_risk > 0.5:
            return "high"
        elif overall_risk > 0.3:
            return "medium"
        else:
            return "low"


class BatchAnalytics:
    """Batch analytics processor for historical analysis."""

    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache TTL

    def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily analytics report."""
        cache_key = f"daily_report:{date.strftime('%Y-%m-%d')}"

        # Check cache first
        cached_report = redis_repo.get_cache(cache_key)
        if cached_report:
            return cached_report

        try:
            start_date = date.replace(
                hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            report = {
                'date': date.strftime('%Y-%m-%d'),
                'transaction_summary': self._get_transaction_summary(start_date, end_date),
                'fraud_summary': self._get_fraud_summary(start_date, end_date),
                'alert_summary': self._get_alert_summary(start_date, end_date),
                'performance_metrics': self._get_performance_metrics(start_date, end_date),
                'top_merchants': self._get_top_merchants(start_date, end_date),
                'risk_distribution': self._get_risk_distribution(start_date, end_date),
                'geographic_analysis': self._get_geographic_analysis(start_date, end_date),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

            # Cache the report
            redis_repo.set_cache(cache_key, str(report), self.cache_ttl)

            return report

        except (AttributeError, ValueError, TypeError, RuntimeError) as e:
            logger.error("Error generating daily report: %s", e)
            return {}

    def generate_weekly_report(self, start_date: datetime) -> Dict[str, Any]:
        """Generate weekly analytics report."""
        cache_key = f"weekly_report:{start_date.strftime('%Y-%m-%d')}"

        # Check cache first
        cached_report = redis_repo.get_cache(cache_key)
        if cached_report:
            return cached_report

        try:
            end_date = start_date + timedelta(weeks=1)

            report = {
                'week_start': start_date.strftime('%Y-%m-%d'),
                'week_end': end_date.strftime('%Y-%m-%d'),
                'transaction_summary': self._get_transaction_summary(start_date, end_date),
                'fraud_summary': self._get_fraud_summary(start_date, end_date),
                'alert_summary': self._get_alert_summary(start_date, end_date),
                'performance_metrics': self._get_performance_metrics(start_date, end_date),
                'trends': self._get_weekly_trends(start_date, end_date),
                'top_merchants': self._get_top_merchants(start_date, end_date),
                'risk_distribution': self._get_risk_distribution(start_date, end_date),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

            # Cache the report
            redis_repo.set_cache(cache_key, str(report), self.cache_ttl)

            return report

        except (AttributeError, ValueError, TypeError, RuntimeError) as e:
            logger.error("Error generating weekly report: %s", e)
            return {}

    def _get_transaction_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get transaction summary for a date range."""
        transactions = transaction_repo.get_by_date_range(start_date, end_date)

        if not transactions:
            return {
                'total_transactions': 0,
                'total_amount': 0.0,
                'average_amount': 0.0,
                'max_amount': 0.0,
                'min_amount': 0.0
            }

        amounts = [t.amount for t in transactions]

        return {
            'total_transactions': len(transactions),
            'total_amount': sum(amounts),
            'average_amount': sum(amounts) / len(amounts),
            'max_amount': max(amounts),
            'min_amount': min(amounts)
        }

    def _get_fraud_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get fraud summary for a date range."""
        # Get fraud scores for the period
        fraud_scores = fraud_score_repo.get_high_risk_scores(min_score=0.0)
        period_scores = [
            fs for fs in fraud_scores if start_date <= fs.timestamp <= end_date]

        if not period_scores:
            return {
                'total_scores': 0,
                'average_score': 0.0,
                'high_risk_count': 0,
                'critical_risk_count': 0
            }

        scores = [fs.score for fs in period_scores]
        high_risk = [fs for fs in period_scores if fs.score >= 0.6]
        critical_risk = [fs for fs in period_scores if fs.score >= 0.8]

        return {
            'total_scores': len(period_scores),
            'average_score': sum(scores) / len(scores),
            'high_risk_count': len(high_risk),
            'critical_risk_count': len(critical_risk),
            'high_risk_percentage': (len(high_risk) / len(period_scores)) * 100
        }

    def _get_alert_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get alert summary for a date range."""
        alerts = alert_repo.get_all()
        period_alerts = [a for a in alerts if start_date <=
                         a.created_at <= end_date]

        if not period_alerts:
            return {
                'total_alerts': 0,
                'pending_alerts': 0,
                'processed_alerts': 0,
                'critical_alerts': 0
            }

        pending = [a for a in period_alerts if a.status == 'PENDING']
        processed = [a for a in period_alerts if a.status == 'PROCESSED']
        critical = [a for a in period_alerts if a.severity == 'CRITICAL']

        return {
            'total_alerts': len(period_alerts),
            'pending_alerts': len(pending),
            'processed_alerts': len(processed),
            'critical_alerts': len(critical)
        }

    def _get_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get performance metrics for a date range."""
        # Get metrics from analytics table
        metrics = analytics_repo.get_metric_by_name(
            'transaction_count', start_date, end_date)

        if not metrics:
            return {
                'transactions_per_hour': 0,
                'average_processing_time': 0.0,
                'system_uptime': 100.0
            }

        # Calculate performance metrics
        total_transactions = sum(m.metric_value for m in metrics)
        hours = (end_date - start_date).total_seconds() / 3600

        return {
            'transactions_per_hour': total_transactions / hours if hours > 0 else 0,
            # Would need to be calculated from actual processing times
            'average_processing_time': 0.0,
            'system_uptime': 100.0  # Would need to be calculated from system logs
        }

    def _get_top_merchants(self, start_date: datetime, end_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top merchants by transaction volume."""
        transactions = transaction_repo.get_by_date_range(start_date, end_date)

        if not transactions:
            return []

        # Group by merchant
        merchant_stats = {}
        for t in transactions:
            if t.merchant_name:
                if t.merchant_name not in merchant_stats:
                    merchant_stats[t.merchant_name] = {
                        'merchant_name': t.merchant_name,
                        'transaction_count': 0,
                        'total_amount': 0.0
                    }
                merchant_stats[t.merchant_name]['transaction_count'] += 1
                merchant_stats[t.merchant_name]['total_amount'] += t.amount

        # Sort by transaction count and return top merchants
        sorted_merchants = sorted(
            merchant_stats.values(),
            key=lambda x: x['transaction_count'],
            reverse=True
        )

        return sorted_merchants[:limit]

    def _get_risk_distribution(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Get risk level distribution."""
        fraud_scores = fraud_score_repo.get_high_risk_scores(min_score=0.0)
        period_scores = [
            fs for fs in fraud_scores if start_date <= fs.timestamp <= end_date]

        distribution = {
            'LOW': 0,
            'MEDIUM': 0,
            'HIGH': 0,
            'CRITICAL': 0
        }

        for score in period_scores:
            distribution[score.risk_level] += 1

        return distribution

    def _get_geographic_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get geographic analysis."""
        transactions = transaction_repo.get_by_date_range(start_date, end_date)

        if not transactions:
            return {'countries': {}, 'cities': {}}

        countries = {}
        cities = {}

        for t in transactions:
            # Handle both database and schema models
            location_country = getattr(t, 'location_country', None) or (
                getattr(t, 'location', None) and getattr(t.location, 'country', None))
            if location_country:
                countries[location_country] = countries.get(
                    location_country, 0) + 1

            location_city = getattr(t, 'location_city', None) or (
                getattr(t, 'location', None) and getattr(t.location, 'city', None))
            if location_city:
                cities[location_city] = cities.get(location_city, 0) + 1

        return {
            'countries': dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
            'cities': dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10])
        }

    def _get_weekly_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, List[float]]:
        """Get weekly trends."""
        # This would calculate trends over the week
        # For now, return empty trends (dates will be used in future implementation)
        _ = start_date, end_date  # Acknowledge unused parameters
        return {
            'transaction_trend': [],
            'fraud_score_trend': [],
            'alert_trend': []
        }


class FraudPatternDetector:
    """Advanced fraud pattern detection using machine learning."""

    def __init__(self):
        self.patterns = {}
        self.load_patterns()

    def load_patterns(self):
        """Load known fraud patterns."""
        self.patterns = {
            'velocity_patterns': {
                'high_frequency': {'threshold': 10, 'window_minutes': 60},
                'large_amounts': {'threshold': 10000, 'window_hours': 24},
                'geographic_jumping': {'threshold_km': 1000, 'window_hours': 2}
            },
            'behavioral_patterns': {
                'unusual_hours': {'start_hour': 2, 'end_hour': 6},
                'suspicious_merchants': ['casino', 'gambling', 'crypto'],
                'amount_patterns': {'round_numbers': True, 'repeated_amounts': True}
            }
        }

    def detect_patterns(self, transaction_event: TransactionEvent,
                        user_history: List[TransactionEvent]) -> Dict[str, Any]:
        """Detect fraud patterns in a transaction."""
        patterns_found = {}

        # Velocity patterns
        patterns_found['velocity'] = self._detect_velocity_patterns(
            transaction_event, user_history)

        # Behavioral patterns
        patterns_found['behavioral'] = self._detect_behavioral_patterns(
            transaction_event, user_history)

        # Amount patterns
        patterns_found['amount'] = self._detect_amount_patterns(
            transaction_event, user_history)

        return patterns_found

    def _detect_velocity_patterns(self, transaction: TransactionEvent,
                                  user_history: List[TransactionEvent]) -> Dict[str, bool]:
        """Detect velocity-based fraud patterns."""
        patterns = {}

        # High frequency transactions
        recent_transactions = [
            t for t in user_history
            if (transaction.transaction.timestamp - t.transaction.timestamp).total_seconds() <= 3600
        ]
        patterns['high_frequency'] = len(recent_transactions) >= 10

        # Large amounts
        large_amounts = [
            t for t in user_history
            if (transaction.transaction.timestamp - t.transaction.timestamp).total_seconds() <= 86400
            and t.transaction.amount >= 10000
        ]
        patterns['large_amounts'] = len(large_amounts) >= 3

        return patterns

    def _detect_behavioral_patterns(self, transaction: TransactionEvent,
                                    user_history: List[TransactionEvent]) -> Dict[str, bool]:
        """Detect behavioral fraud patterns."""
        patterns = {}
        _ = user_history  # Will be used in future implementation

        # Unusual hours
        hour = transaction.transaction.timestamp.hour
        patterns['unusual_hours'] = 2 <= hour <= 6

        # Suspicious merchants
        merchant_lower = transaction.transaction.merchant_name.lower(
        ) if transaction.transaction.merchant_name else ""
        patterns['suspicious_merchant'] = any(
            pattern in merchant_lower for pattern in ['casino', 'gambling', 'crypto']
        )

        return patterns

    def _detect_amount_patterns(self, transaction: TransactionEvent,
                                user_history: List[TransactionEvent]) -> Dict[str, bool]:
        """Detect amount-based fraud patterns."""
        patterns = {}

        # Round numbers
        amount = transaction.transaction.amount
        patterns['round_number'] = amount % 100 == 0

        # Repeated amounts
        recent_amounts = [
            t.transaction.amount for t in user_history[-10:]
            if (transaction.transaction.timestamp - t.transaction.timestamp).total_seconds() <= 86400
        ]
        patterns['repeated_amount'] = amount in recent_amounts

        return patterns


# Global analytics instances
real_time_analytics = RealTimeAnalytics()
batch_analytics = BatchAnalytics()
fraud_pattern_detector = FraudPatternDetector()
