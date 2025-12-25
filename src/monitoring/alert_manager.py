#!/usr/bin/env python3
"""
Alert manager for handling fraud alerts, system alerts, and performance alerts.
Provides notification capabilities and alert escalation.
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types."""
    FRAUD_DETECTED = "fraud_detected"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONNECTION_FAILURE = "connection_failure"
    DATA_ANOMALY = "data_anomaly"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    escalation_level: int = 0


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    type: AlertType
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    message_template: str
    cooldown_minutes: int = 5
    escalation_enabled: bool = True
    notification_channels: List[str] = field(
        default_factory=lambda: ['log', 'email'])


class NotificationChannel:
    """Base class for notification channels."""

    def send_notification(self, alert: Alert) -> bool:
        """Send notification for an alert."""
        raise NotImplementedError


class LogNotificationChannel(NotificationChannel):
    """Log-based notification channel."""

    def send_notification(self, alert: Alert) -> bool:
        """Send notification via logging."""
        try:
            log_message = f"ALERT [{alert.severity.value.upper()}] {alert.type.value}: {alert.title} - {alert.message}"
            if alert.severity == AlertSeverity.CRITICAL:
                logger.critical(log_message)
            elif alert.severity == AlertSeverity.HIGH:
                logger.error(log_message)
            elif alert.severity == AlertSeverity.MEDIUM:
                logger.warning(log_message)
            else:
                logger.info(log_message)
            return True
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Failed to send log notification: %s", e)
            return False


class EmailNotificationChannel(NotificationChannel):
    """Email-based notification channel."""

    def __init__(self, smtp_config: Dict[str, str]):
        self.smtp_config = smtp_config
        self.recipients = smtp_config.get('recipients', '').split(',')

    def send_notification(self, alert: Alert) -> bool:
        """Send notification via email."""
        try:
            if not self.recipients:
                logger.warning("No email recipients configured")
                return False

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get(
                'from_email', 'alerts@frauddetection.com')
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            # Email body
            body = f"""
Alert Details:
- Type: {alert.type.value}
- Severity: {alert.severity.value}
- Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
- Source: {alert.source}

Message: {alert.message}

Metadata: {json.dumps(alert.metadata, indent=2)}

---
Fraud Detection System
            """

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            with smtplib.SMTP(self.smtp_config.get('smtp_server', 'localhost'),
                              int(self.smtp_config.get('smtp_port', '587'))) as server:
                if self.smtp_config.get('use_tls', 'true').lower() == 'true':
                    server.starttls()

                if self.smtp_config.get('username') and self.smtp_config.get('password'):
                    server.login(
                        self.smtp_config['username'], self.smtp_config['password'])

                server.send_message(msg)

            logger.info(
                "Email alert sent to %d recipients", len(self.recipients))
            return True

        except (ValueError, RuntimeError, AttributeError, smtplib.SMTPException) as e:
            logger.error("Failed to send email notification: %s", e)
            return False


class AlertManager:
    """Comprehensive alert manager for fraud detection system."""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.escalation_rules: Dict[AlertSeverity, Dict[str, Any]] = {}

        # Alert tracking
        self.alert_counts: Dict[AlertType, int] = {}
        self.last_alert_times: Dict[str, datetime] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Initialize default notification channels
        self._initialize_default_channels()

        # Initialize default alert rules
        self._initialize_default_rules()

        # Start background processing
        self._start_background_processing()

    def _initialize_default_channels(self):
        """Initialize default notification channels."""
        # Log channel (always available)
        self.notification_channels['log'] = LogNotificationChannel()

        # Email channel (if configured)
        try:
            smtp_config = {
                'smtp_server': 'localhost',
                'smtp_port': '587',
                'use_tls': 'true',
                'from_email': 'alerts@frauddetection.com',
                'recipients': 'admin@frauddetection.com'
            }
            self.notification_channels['email'] = EmailNotificationChannel(
                smtp_config)
        except (ValueError, RuntimeError, AttributeError, ImportError) as e:
            logger.warning("Email notification channel not available: %s", e)

    def _initialize_default_rules(self):
        """Initialize default alert rules."""
        # High fraud rate rule
        self.add_rule(AlertRule(
            name="high_fraud_rate",
            type=AlertType.FRAUD_DETECTED,
            severity=AlertSeverity.HIGH,
            condition=lambda metrics: metrics.get(
                'fraud_rate', 0) > 0.1,  # > 10%
            message_template="Fraud rate has exceeded 10% threshold. Current rate: {fraud_rate:.2%}",
            cooldown_minutes=10
        ))

        # High error rate rule
        self.add_rule(AlertRule(
            name="high_error_rate",
            type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.MEDIUM,
            condition=lambda metrics: metrics.get(
                'error_rate', 0) > 0.05,  # > 5%
            message_template="Error rate has exceeded 5% threshold. Current rate: {error_rate:.2%}",
            cooldown_minutes=5
        ))

        # System resource exhaustion rule
        self.add_rule(AlertRule(
            name="resource_exhaustion",
            type=AlertType.RESOURCE_EXHAUSTION,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: (
                metrics.get('cpu_usage', 0) > 90 or
                metrics.get('memory_usage', 0) > 95 or
                metrics.get('disk_usage', 0) > 95
            ),
            message_template="System resources are critically low. CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%, Disk: {disk_usage:.1f}%",
            cooldown_minutes=2
        ))

        # Performance degradation rule
        self.add_rule(AlertRule(
            name="performance_degradation",
            type=AlertType.PERFORMANCE_DEGRADATION,
            severity=AlertSeverity.MEDIUM,
            condition=lambda metrics: metrics.get(
                'avg_processing_time', 0) > 1000,  # > 1 second
            message_template="Transaction processing time has degraded. Average: {avg_processing_time:.0f}ms",
            cooldown_minutes=5
        ))

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        with self._lock:
            self.rules[rule.name] = rule

    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        with self._lock:
            self.rules.pop(rule_name, None)

    def create_alert(self, alert_type: AlertType, severity: AlertSeverity,
                     title: str, message: str, source: str,
                     metadata: Optional[Dict[str, Any]] = None) -> Alert:
        """Create a new alert."""
        alert_id = f"{alert_type.value}_{int(time.time())}_{len(self.alerts)}"

        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(timezone.utc),
            source=source,
            metadata=metadata or {}
        )

        with self._lock:
            self.alerts[alert_id] = alert
            self.alert_counts[alert_type] = self.alert_counts.get(
                alert_type, 0) + 1

        # Send notifications
        self._send_notifications(alert)

        logger.info("Alert created: %s - %s", alert_id, title)
        return alert

    def evaluate_metrics(self, metrics: Dict[str, Any]):
        """Evaluate metrics against alert rules."""
        with self._lock:
            for rule_name, rule in self.rules.items():
                # Check cooldown
                last_alert_time = self.last_alert_times.get(rule_name)
                if last_alert_time and (datetime.now(timezone.utc) - last_alert_time).total_seconds() < rule.cooldown_minutes * 60:
                    continue

                # Check condition
                try:
                    if rule.condition(metrics):
                        # Create alert
                        message = rule.message_template.format(**metrics)
                        alert = self.create_alert(
                            alert_type=rule.type,
                            severity=rule.severity,
                            title=f"Rule triggered: {rule.name}",
                            message=message,
                            source="alert_manager",
                            metadata={'rule_name': rule_name,
                                      'metrics': metrics}
                        )

                        # Update last alert time
                        self.last_alert_times[rule_name] = alert.timestamp

                except (ValueError, RuntimeError, AttributeError, TypeError) as e:
                    logger.error("Error evaluating rule %s: %s", rule_name, e)

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                logger.info(
                    "Alert %s acknowledged by %s", alert_id, acknowledged_by)
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                logger.info("Alert %s resolved", alert_id)
                return True
        return False

    def get_alerts(self, filters: Optional[Dict[str, Any]] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        with self._lock:
            alerts = list(self.alerts.values())

        if not filters:
            return alerts

        # Apply filters
        filtered_alerts = []
        for alert in alerts:
            include = True

            if 'severity' in filters and alert.severity != filters['severity']:
                include = False

            if 'type' in filters and alert.type != filters['type']:
                include = False

            if 'acknowledged' in filters and alert.acknowledged != filters['acknowledged']:
                include = False

            if 'resolved' in filters and alert.resolved != filters['resolved']:
                include = False

            if 'source' in filters and alert.source != filters['source']:
                include = False

            if include:
                filtered_alerts.append(alert)

        return filtered_alerts

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        with self._lock:
            total_alerts = len(self.alerts)
            active_alerts = len(
                [a for a in self.alerts.values() if not a.resolved])
            unacknowledged_alerts = len(
                [a for a in self.alerts.values() if not a.acknowledged and not a.resolved])

            # Count by severity
            severity_counts = {}
            for severity in AlertSeverity:
                severity_counts[severity.value] = len([
                    a for a in self.alerts.values()
                    if a.severity == severity and not a.resolved
                ])

            # Count by type
            type_counts = {}
            for alert_type in AlertType:
                type_counts[alert_type.value] = len([
                    a for a in self.alerts.values()
                    if a.type == alert_type and not a.resolved
                ])

            return {
                'total_alerts': total_alerts,
                'active_alerts': active_alerts,
                'unacknowledged_alerts': unacknowledged_alerts,
                'severity_distribution': severity_counts,
                'type_distribution': type_counts,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        for channel_name, channel in self.notification_channels.items():
            try:
                success = channel.send_notification(alert)
                if success:
                    logger.debug("Notification sent via %s", channel_name)
                else:
                    logger.warning(
                        "Failed to send notification via %s", channel_name)
            except (ValueError, RuntimeError, AttributeError, TypeError) as e:
                logger.error(
                    "Error sending notification via %s: %s", channel_name, e)

    def _start_background_processing(self):
        """Start background alert processing."""
        def process_alerts():
            while True:
                try:
                    # Check for escalation
                    self._check_escalations()

                    # Clean up old alerts (older than 30 days)
                    self._cleanup_old_alerts()

                    time.sleep(60)  # Check every minute

                except (ValueError, RuntimeError, AttributeError, TypeError) as e:
                    logger.error("Error in background alert processing: %s", e)
                    time.sleep(300)  # Wait 5 minutes on error

        thread = threading.Thread(target=process_alerts, daemon=True)
        thread.start()

    def _check_escalations(self):
        """Check for alert escalations."""
        with self._lock:
            current_time = datetime.now(timezone.utc)

            for alert in self.alerts.values():
                if alert.resolved or alert.acknowledged:
                    continue

                # Check if escalation is needed
                time_since_creation = (
                    current_time - alert.timestamp).total_seconds()

                if time_since_creation > 3600 and alert.escalation_level == 0:  # 1 hour
                    alert.escalation_level = 1
                    self._escalate_alert(alert)
                elif time_since_creation > 7200 and alert.escalation_level == 1:  # 2 hours
                    alert.escalation_level = 2
                    self._escalate_alert(alert)

    def _escalate_alert(self, alert: Alert):
        """Escalate an alert."""
        _ = self.create_alert(
            alert_type=alert.type,
            severity=AlertSeverity.CRITICAL if alert.severity != AlertSeverity.CRITICAL else AlertSeverity.CRITICAL,
            title=f"ESCALATED: {alert.title}",
            message=f"Alert has been escalated after {alert.escalation_level} hour(s). Original: {alert.message}",
            source="alert_manager",
            metadata={'original_alert_id': alert.id,
                      'escalation_level': alert.escalation_level}
        )

        logger.warning(
            "Alert %s escalated to level %d", alert.id, alert.escalation_level)

    def _cleanup_old_alerts(self):
        """Clean up alerts older than 30 days."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)

        with self._lock:
            alerts_to_remove = [
                alert_id for alert_id, alert in self.alerts.items()
                if alert.timestamp < cutoff_time
            ]

            for alert_id in alerts_to_remove:
                del self.alerts[alert_id]

            if alerts_to_remove:
                logger.info("Cleaned up %d old alerts", len(alerts_to_remove))


# Global alert manager instance
alert_manager = AlertManager()
