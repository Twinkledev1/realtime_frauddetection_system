"""
Streaming pipeline manager for orchestrating the fraud detection data flow.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from src.data_models.schemas.transaction import TransactionEvent, FraudScore, Alert
from src.fraud_detection.rules.rule_engine import FraudRuleEngine
from src.kafka_producers.transaction_producer import TransactionProducer
from src.kafka_consumers.transaction_consumer import TransactionConsumer

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Statistics for the streaming pipeline."""
    start_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    total_transactions_processed: int = 0
    total_fraudulent_transactions: int = 0
    total_alerts_generated: int = 0
    average_processing_time_ms: float = 0.0
    last_activity: Optional[datetime] = None
    errors_count: int = 0

    def update_processing_time(self, processing_time_ms: float):
        """Update average processing time."""
        if self.total_transactions_processed == 0:
            self.average_processing_time_ms = processing_time_ms
        else:
            self.average_processing_time_ms = (
                (self.average_processing_time_ms * self.total_transactions_processed +
                 processing_time_ms) / (self.total_transactions_processed + 1)
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'start_time': self.start_time.isoformat(),
            'total_transactions_processed': self.total_transactions_processed,
            'total_fraudulent_transactions': self.total_fraudulent_transactions,
            'total_alerts_generated': self.total_alerts_generated,
            'average_processing_time_ms': self.average_processing_time_ms,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'errors_count': self.errors_count,
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            'transactions_per_second': (
                self.total_transactions_processed /
                max(1, (datetime.now(timezone.utc) -
                    self.start_time).total_seconds())
            )
        }


class StreamingPipelineManager:
    """Manages the complete streaming pipeline for fraud detection."""

    def __init__(self,
                 kafka_bootstrap_servers: str,
                 input_topic: str = "fraud-transactions",
                 output_topic: str = "fraud-alerts",
                 consumer_group_id: str = None):
        """Initialize the streaming pipeline manager.

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers
            input_topic: Topic to consume transaction events from
            output_topic: Topic to publish fraud alerts to
            consumer_group_id: Consumer group ID
        """
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.consumer_group_id = consumer_group_id

        # Initialize components
        self.rule_engine = FraudRuleEngine()
        self.stats = PipelineStats()

        # Pipeline state
        self.running = False
        self.consumer = None
        self.producer = None

        # Callbacks
        self.on_transaction_processed: Optional[Callable[[
            TransactionEvent, FraudScore], None]] = None
        self.on_alert_generated: Optional[Callable[[Alert], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        logger.info(
            "Streaming pipeline manager initialized for topics: %s -> %s",
            input_topic, output_topic)

    def set_callbacks(self,
                      on_transaction_processed: Callable[[
                          TransactionEvent, FraudScore], None] = None,
                      on_alert_generated: Callable[[Alert], None] = None,
                      on_error: Callable[[Exception], None] = None):
        """Set callback functions for pipeline events."""
        self.on_transaction_processed = on_transaction_processed
        self.on_alert_generated = on_alert_generated
        self.on_error = on_error

    def _initialize_components(self):
        """Initialize Kafka consumer and producer."""
        try:
            # Initialize consumer
            self.consumer = TransactionConsumer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                topic=self.input_topic,
                group_id=self.consumer_group_id
            )

            # Initialize producer
            self.producer = TransactionProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                topic=self.output_topic
            )

            logger.info("Kafka components initialized successfully")

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Failed to initialize Kafka components: %s", e)
            raise

    def _process_transaction(self, transaction_event: TransactionEvent) -> FraudScore:
        """Process a single transaction through the fraud detection engine."""
        start_time = time.time()

        try:
            # Evaluate transaction
            fraud_score = self.rule_engine.evaluate_transaction(
                transaction_event.transaction)

            # Update statistics
            processing_time_ms = (time.time() - start_time) * 1000
            self.stats.total_transactions_processed += 1
            self.stats.last_activity = datetime.now(timezone.utc)
            self.stats.update_processing_time(processing_time_ms)

            # Check if transaction is fraudulent
            if fraud_score.score >= 0.6:
                self.stats.total_fraudulent_transactions += 1

            # Call callback if set
            if self.on_transaction_processed:
                self.on_transaction_processed(transaction_event, fraud_score)

            logger.debug(
                "Processed transaction %s in %.2fms, score: %.3f",
                transaction_event.transaction.transaction_id,
                processing_time_ms,
                fraud_score.score
            )

            return fraud_score

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            self.stats.errors_count += 1
            logger.error(
                "Error processing transaction %s: %s",
                transaction_event.transaction.transaction_id, e
            )

            if self.on_error:
                self.on_error(e)

            raise

    def _generate_alert(self, transaction_event: TransactionEvent,
                        fraud_score: FraudScore) -> Optional[Alert]:
        """Generate an alert for high-risk transactions."""
        if fraud_score.score < 0.6:
            return None

        try:
            alert = Alert(
                transaction_id=transaction_event.transaction.transaction_id,
                fraud_score=fraud_score,
                alert_type="FRAUD_DETECTED" if fraud_score.score >= 0.8 else "SUSPICIOUS_ACTIVITY",
                severity="CRITICAL" if fraud_score.score >= 0.8 else "HIGH",
                description=(f"Fraud score: {fraud_score.score:.3f} for transaction "
                             f"{transaction_event.transaction.transaction_id}")
            )

            self.stats.total_alerts_generated += 1

            # Call callback if set
            if self.on_alert_generated:
                self.on_alert_generated(alert)

            logger.info(
                "Generated alert for transaction %s: score=%.3f, severity=%s",
                transaction_event.transaction.transaction_id,
                fraud_score.score,
                alert.severity
            )

            return alert

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            self.stats.errors_count += 1
            logger.error(
                "Error generating alert for transaction %s: %s",
                transaction_event.transaction.transaction_id, e
            )

            if self.on_error:
                self.on_error(e)

            return None

    def _send_alert(self, alert: Alert) -> bool:
        """Send alert to Kafka output topic."""
        try:
            if self.producer:
                # Convert alert to dict for JSON serialization
                alert_dict = alert.dict()
                alert_dict['timestamp'] = datetime.now(
                    timezone.utc).isoformat()

                # Send to Kafka
                success = self.producer.send_transaction_sync(
                    # Using TransactionEvent as wrapper
                    TransactionEvent(transaction=alert_dict),
                    timeout=10
                )

                if success:
                    logger.debug(
                        "Alert sent to Kafka: %s", alert.transaction_id)
                    return True
                else:
                    logger.error(
                        "Failed to send alert to Kafka: %s", alert.transaction_id)
                    return False
            else:
                logger.error("Producer not initialized")
                return False

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            self.stats.errors_count += 1
            logger.error("Error sending alert to Kafka: %s", e)

            if self.on_error:
                self.on_error(e)

            return False

    def _message_handler(self, transaction_event: TransactionEvent):
        """Handle incoming transaction messages."""
        try:
            # Process transaction
            fraud_score = self._process_transaction(transaction_event)

            # Generate alert if needed
            alert = self._generate_alert(transaction_event, fraud_score)

            # Send alert to Kafka
            if alert:
                self._send_alert(alert)

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            self.stats.errors_count += 1
            logger.error("Error in message handler: %s", e)

            if self.on_error:
                self.on_error(e)

    def start(self):
        """Start the streaming pipeline."""
        if self.running:
            logger.warning("Pipeline is already running")
            return

        try:
            logger.info("Starting streaming pipeline...")

            # Initialize components
            self._initialize_components()

            # Set running flag
            self.running = True

            # Start consuming messages
            self.consumer.consume_messages(self._message_handler)

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error starting pipeline: %s", e)
            self.running = False
            raise

    def stop(self):
        """Stop the streaming pipeline."""
        if not self.running:
            logger.warning("Pipeline is not running")
            return

        logger.info("Stopping streaming pipeline...")
        self.running = False

        # Close components
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()

        logger.info("Streaming pipeline stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.stats.to_dict()

    def get_rule_summary(self) -> Dict[str, Any]:
        """Get fraud rule summary."""
        return self.rule_engine.get_rule_summary()

    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self.running


class AsyncStreamingPipelineManager:
    """Asynchronous version of the streaming pipeline manager."""

    def __init__(self,
                 kafka_bootstrap_servers: str,
                 input_topic: str = "fraud-transactions",
                 output_topic: str = "fraud-alerts",
                 consumer_group_id: str = None):
        """Initialize the async streaming pipeline manager."""
        self.sync_manager = StreamingPipelineManager(
            kafka_bootstrap_servers=kafka_bootstrap_servers,
            input_topic=input_topic,
            output_topic=output_topic,
            consumer_group_id=consumer_group_id
        )
        self.running = False

    async def start(self):
        """Start the async streaming pipeline."""
        if self.running:
            logger.warning("Async pipeline is already running")
            return

        logger.info("Starting async streaming pipeline...")
        self.running = True

        # Run the sync pipeline in a thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sync_manager.start)

    async def stop(self):
        """Stop the async streaming pipeline."""
        if not self.running:
            logger.warning("Async pipeline is not running")
            return

        logger.info("Stopping async streaming pipeline...")
        self.running = False

        # Stop the sync pipeline
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sync_manager.stop)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.sync_manager.get_stats()

    def get_rule_summary(self) -> Dict[str, Any]:
        """Get fraud rule summary."""
        return self.sync_manager.get_rule_summary()

    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self.running and self.sync_manager.is_running()
