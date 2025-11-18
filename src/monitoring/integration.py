#!/usr/bin/env python3
"""
Integration layer for connecting monitoring components with the fraud detection system.
Provides hooks and decorators for automatic metrics collection and alerting.
"""

import time
import functools
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Callable
import logging

from src.monitoring.metrics_collector import metrics_collector
from src.monitoring.alert_manager import alert_manager, AlertSeverity, AlertType

logger = logging.getLogger(__name__)


class MonitoringIntegration:
    """Integration layer for monitoring fraud detection system."""

    def __init__(self):
        self.enabled = True
        self.performance_tracking = True
        self.error_tracking = True
        self.transaction_tracking = True

    def track_transaction(self, transaction_data: Dict[str, Any]):
        """Track transaction metrics."""
        if not self.enabled or not self.transaction_tracking:
            return

        try:
            # Record transaction metrics
            metrics_collector.record_transaction(transaction_data)

            # Evaluate metrics for alerts
            metrics_summary = metrics_collector.get_metrics_summary()
            alert_manager.evaluate_metrics(metrics_summary)

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error tracking transaction: %s", e)

    def track_performance(self, operation: str, duration: float, success: bool = True):
        """Track performance metrics."""
        if not self.enabled or not self.performance_tracking:
            return

        try:
            metrics_collector.record_performance(operation, duration, success)
        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error tracking performance: %s", e)

    def track_error(self, error_type: str, error_message: str = "", context: Optional[Dict[str, Any]] = None):
        """Track error metrics and create alerts."""
        if not self.enabled or not self.error_tracking:
            return

        try:
            # Record error metrics
            metrics_collector.record_error(error_type, error_message)

            # Create error alert
            alert_manager.create_alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.MEDIUM,
                title=f"System Error: {error_type}",
                message=error_message,
                source="monitoring_integration",
                metadata=context or {}
            )

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error tracking error: %s", e)

    def create_fraud_alert(self, transaction_id: str, fraud_score: float,
                           risk_level: str, details: Optional[Dict[str, Any]] = None):
        """Create fraud detection alert."""
        if not self.enabled:
            return

        try:
            # Determine severity based on fraud score
            if fraud_score >= 0.9:
                severity = AlertSeverity.CRITICAL
            elif fraud_score >= 0.7:
                severity = AlertSeverity.HIGH
            elif fraud_score >= 0.5:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW

            # Create alert
            alert_manager.create_alert(
                alert_type=AlertType.FRAUD_DETECTED,
                severity=severity,
                title=f"Fraud Detected - Transaction {transaction_id}",
                message=f"Fraud score: {fraud_score:.3f}, Risk level: {risk_level}",
                source="fraud_detection_engine",
                metadata={
                    'transaction_id': transaction_id,
                    'fraud_score': fraud_score,
                    'risk_level': risk_level,
                    'details': details or {}
                }
            )

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error creating fraud alert: %s", e)


# Global monitoring integration instance
monitoring_integration = MonitoringIntegration()


def monitor_performance(operation_name: Optional[str] = None):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                # Track the error
                monitoring_integration.track_error(
                    error_type=f"{operation}_error",
                    error_message=str(e),
                    context={'function': func.__name__,
                             'args': str(args), 'kwargs': str(kwargs)}
                )
                raise
            finally:
                duration = (time.time() - start_time) * \
                    1000  # Convert to milliseconds
                monitoring_integration.track_performance(
                    operation, duration, success)

        return wrapper
    return decorator


def monitor_transactions(func: Callable) -> Callable:
    """Decorator to monitor transaction processing functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)

            # Extract transaction data from result
            if hasattr(result, 'transaction') and hasattr(result, 'fraud_score'):
                transaction_data = {
                    'transaction_id': getattr(result.transaction, 'transaction_id', 'unknown'),
                    'amount': getattr(result.transaction, 'amount', 0),
                    'fraud_score': getattr(result.fraud_score, 'score', 0),
                    'risk_level': getattr(result.fraud_score, 'risk_level', 'unknown'),
                    'user_id': getattr(result.transaction, 'user_id', 'unknown'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                # Track transaction
                monitoring_integration.track_transaction(transaction_data)

                # Create fraud alert if score is high
                fraud_score = transaction_data['fraud_score']
                if fraud_score >= 0.6:  # Alert threshold
                    monitoring_integration.create_fraud_alert(
                        transaction_id=transaction_data['transaction_id'],
                        fraud_score=fraud_score,
                        risk_level=transaction_data['risk_level'],
                        details={
                            'user_id': transaction_data['user_id'], 'amount': transaction_data['amount']}
                    )

            return result

        except Exception as e:
            # Track error
            monitoring_integration.track_error(
                error_type=f"{func.__name__}_error",
                error_message=str(e),
                context={'function': func.__name__}
            )
            raise

    return wrapper


class MonitoringHooks:
    """Hooks for integrating monitoring into existing components."""

    @staticmethod
    def hook_fraud_detection_engine(engine):
        """Hook monitoring into fraud detection engine."""
        original_evaluate = engine.evaluate_transaction

        def monitored_evaluate(transaction):
            start_time = time.time()
            try:
                result = original_evaluate(transaction)

                # Track transaction
                transaction_data = {
                    'transaction_id': getattr(transaction, 'transaction_id', 'unknown'),
                    'amount': getattr(transaction, 'amount', 0),
                    'fraud_score': getattr(result, 'score', 0),
                    'risk_level': getattr(result, 'risk_level', 'unknown'),
                    'user_id': getattr(transaction, 'user_id', 'unknown'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

                monitoring_integration.track_transaction(transaction_data)

                # Create fraud alert if needed
                fraud_score = transaction_data['fraud_score']
                if fraud_score >= 0.6:
                    monitoring_integration.create_fraud_alert(
                        transaction_id=transaction_data['transaction_id'],
                        fraud_score=fraud_score,
                        risk_level=transaction_data['risk_level'],
                        details={
                            'user_id': transaction_data['user_id'], 'amount': transaction_data['amount']}
                    )

                return result

            except Exception as e:
                monitoring_integration.track_error(
                    error_type="fraud_detection_error",
                    error_message=str(e),
                    context={'transaction_id': getattr(
                        transaction, 'transaction_id', 'unknown')}
                )
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                monitoring_integration.track_performance(
                    "fraud_detection_evaluation", duration, True)

        engine.evaluate_transaction = monitored_evaluate
        logger.info("Monitoring hooks installed for fraud detection engine")

    @staticmethod
    def hook_kafka_producer(producer):
        """Hook monitoring into Kafka producer."""
        original_send = producer.send

        def monitored_send(topic, message, **kwargs):
            start_time = time.time()
            try:
                result = original_send(topic, message, **kwargs)
                return result
            except Exception as e:
                monitoring_integration.track_error(
                    error_type="kafka_producer_error",
                    error_message=str(e),
                    context={'topic': topic}
                )
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                monitoring_integration.track_performance(
                    "kafka_producer_send", duration, True)

        producer.send = monitored_send
        logger.info("Monitoring hooks installed for Kafka producer")

    @staticmethod
    def hook_kafka_consumer(consumer):
        """Hook monitoring into Kafka consumer."""
        original_consume = consumer.consume

        def monitored_consume(**kwargs):
            start_time = time.time()
            try:
                result = original_consume(**kwargs)
                return result
            except Exception as e:
                monitoring_integration.track_error(
                    error_type="kafka_consumer_error",
                    error_message=str(e)
                )
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                monitoring_integration.track_performance(
                    "kafka_consumer_consume", duration, True)

        consumer.consume = monitored_consume
        logger.info("Monitoring hooks installed for Kafka consumer")


def enable_monitoring():
    """Enable monitoring integration."""
    monitoring_integration.enabled = True
    logger.info("Monitoring integration enabled")


def disable_monitoring():
    """Disable monitoring integration."""
    monitoring_integration.enabled = False
    logger.info("Monitoring integration disabled")


def get_monitoring_status() -> Dict[str, Any]:
    """Get monitoring integration status."""
    return {
        'enabled': monitoring_integration.enabled,
        'performance_tracking': monitoring_integration.performance_tracking,
        'error_tracking': monitoring_integration.error_tracking,
        'transaction_tracking': monitoring_integration.transaction_tracking,
        'metrics_collector_active': True,
        'alert_manager_active': True,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }


# Convenience functions for direct monitoring calls
def track_transaction(transaction_data: Dict[str, Any]):
    """Track a transaction."""
    monitoring_integration.track_transaction(transaction_data)


def track_performance(operation: str, duration: float, success: bool = True):
    """Track performance metrics."""
    monitoring_integration.track_performance(operation, duration, success)


def track_error(error_type: str, error_message: str = "", context: Optional[Dict[str, Any]] = None):
    """Track an error."""
    monitoring_integration.track_error(error_type, error_message, context)


def create_fraud_alert(transaction_id: str, fraud_score: float, risk_level: str, details: Optional[Dict[str, Any]] = None):
    """Create a fraud alert."""
    monitoring_integration.create_fraud_alert(
        transaction_id, fraud_score, risk_level, details)
