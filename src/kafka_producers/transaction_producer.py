"""
Kafka producer for transaction events with proper error handling and configuration.
"""
import json
import logging
from typing import Dict, Optional
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
from kafka.producer.future import FutureRecordMetadata

from src.data_models.schemas.transaction import TransactionEvent

logger = logging.getLogger(__name__)


class TransactionProducer:
    """Kafka producer for transaction events."""

    def __init__(self, bootstrap_servers: str, topic: str, **kwargs):
        """Initialize the Kafka producer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Topic to produce messages to
            **kwargs: Additional Kafka producer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

        # Default producer configuration
        default_config = {
            'bootstrap_servers': bootstrap_servers,
            'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',  # Wait for all replicas
            'retries': 3,  # Retry failed sends
            'batch_size': 16384,  # 16KB batch size
            'linger_ms': 10,  # Wait 10ms for more messages
            'buffer_memory': 33554432,  # 32MB buffer
            'max_request_size': 1048576,  # 1MB max request size
            'compression_type': 'gzip',  # Compress messages
            'max_in_flight_requests_per_connection': 5,
            'request_timeout_ms': 30000,  # 30 second timeout
            'delivery_timeout_ms': 120000,  # 2 minute delivery timeout
        }

        # Override with provided kwargs
        default_config.update(kwargs)

        try:
            self.producer = KafkaProducer(**default_config)
            logger.info("Kafka producer initialized for topic: %s", topic)
        except (ValueError, RuntimeError, ImportError) as e:
            logger.error("Failed to initialize Kafka producer: %s", e)
            raise

    def send_transaction(self, event: TransactionEvent, key: Optional[str] = None) -> FutureRecordMetadata:
        """Send a transaction event to Kafka.

        Args:
            event: Transaction event to send
            key: Optional key for partitioning (defaults to transaction_id)

        Returns:
            FutureRecordMetadata: Future object for the send operation

        Raises:
            KafkaError: If there's an error sending the message
        """
        try:
            # Use transaction ID as key if not provided
            if key is None:
                key = event.transaction.transaction_id

            # Convert event to dict for JSON serialization
            event_dict = event.dict()

            # Add metadata
            event_dict['produced_at'] = datetime.utcnow().isoformat()
            event_dict['producer_id'] = 'transaction_producer'

            # Send to Kafka
            future = self.producer.send(
                topic=self.topic,
                key=key,
                value=event_dict
            )

            logger.debug(
                "Transaction sent: %s", event.transaction.transaction_id)
            return future

        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error(
                "Error sending transaction %s: %s", event.transaction.transaction_id, e)
            raise

    def send_transaction_sync(self, event: TransactionEvent, key: Optional[str] = None, timeout: int = 10) -> bool:
        """Send a transaction event synchronously.

        Args:
            event: Transaction event to send
            key: Optional key for partitioning
            timeout: Timeout in seconds for the send operation

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            future = self.send_transaction(event, key)
            record_metadata = future.get(timeout=timeout)

            logger.info(
                "Transaction sent successfully: %s to partition %d at offset %d",
                event.transaction.transaction_id, record_metadata.partition, record_metadata.offset
            )

            return True

        except KafkaTimeoutError:
            logger.error(
                "Timeout sending transaction %s", event.transaction.transaction_id)
            return False
        except KafkaError as e:
            logger.error(
                "Kafka error sending transaction %s: %s", event.transaction.transaction_id, e)
            return False
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error(
                "Unexpected error sending transaction %s: %s", event.transaction.transaction_id, e)
            return False

    def send_batch(self, events: list[TransactionEvent], timeout: int = 30) -> Dict[str, int]:
        """Send a batch of transaction events.

        Args:
            events: List of transaction events to send
            timeout: Timeout in seconds for the entire batch

        Returns:
            Dict with success and error counts
        """
        results = {
            'total': len(events),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        futures = []

        # Send all events
        for event in events:
            try:
                future = self.send_transaction(event)
                futures.append((event, future))
            except (ValueError, RuntimeError, AttributeError) as e:
                results['failed'] += 1
                results['errors'].append(
                    f"Send error for {event.transaction.transaction_id}: {e}")

        # Wait for all futures to complete
        for event, future in futures:
            try:
                _ = future.get(timeout=timeout)
                results['successful'] += 1
                logger.debug(
                    "Batch transaction sent: %s", event.transaction.transaction_id)
            except (ValueError, RuntimeError, AttributeError, KafkaError) as e:
                results['failed'] += 1
                results['errors'].append(
                    f"Delivery error for {event.transaction.transaction_id}: {e}")

        logger.info(
            "Batch send completed: %d/%d successful", results['successful'], results['total'])
        return results

    def flush(self, timeout: int = 30):
        """Flush all pending messages.

        Args:
            timeout: Timeout in seconds for flush operation
        """
        try:
            self.producer.flush(timeout=timeout)
            logger.info("Kafka producer flushed successfully")
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Error flushing Kafka producer: %s", e)
            raise

    def close(self, timeout: int = 30):
        """Close the Kafka producer.

        Args:
            timeout: Timeout in seconds for close operation
        """
        try:
            self.flush(timeout=timeout)
            self.producer.close(timeout=timeout)
            logger.info("Kafka producer closed successfully")
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Error closing Kafka producer: %s", e)
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class TransactionProducerFactory:
    """Factory for creating transaction producers with different configurations."""

    @staticmethod
    def create_high_throughput_producer(bootstrap_servers: str, topic: str) -> TransactionProducer:
        """Create a producer optimized for high throughput."""
        config = {
            'batch_size': 32768,  # 32KB batch size
            'linger_ms': 5,  # 5ms linger
            'buffer_memory': 67108864,  # 64MB buffer
            'compression_type': 'lz4',  # Faster compression
            'max_in_flight_requests_per_connection': 10,
        }
        return TransactionProducer(bootstrap_servers, topic, **config)

    @staticmethod
    def create_low_latency_producer(bootstrap_servers: str, topic: str) -> TransactionProducer:
        """Create a producer optimized for low latency."""
        config = {
            'batch_size': 8192,  # 8KB batch size
            'linger_ms': 0,  # No linger
            'buffer_memory': 16777216,  # 16MB buffer
            'compression_type': 'none',  # No compression
            'max_in_flight_requests_per_connection': 1,
        }
        return TransactionProducer(bootstrap_servers, topic, **config)

    @staticmethod
    def create_reliable_producer(bootstrap_servers: str, topic: str) -> TransactionProducer:
        """Create a producer optimized for reliability."""
        config = {
            'acks': 'all',
            'retries': 5,
            'batch_size': 16384,
            'linger_ms': 20,
            'buffer_memory': 33554432,
            'compression_type': 'gzip',
            'max_in_flight_requests_per_connection': 1,
            'enable_idempotence': True,
        }
        return TransactionProducer(bootstrap_servers, topic, **config)
