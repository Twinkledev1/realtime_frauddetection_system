"""
Kafka consumer for transaction events with proper error handling and configuration.
"""
import json
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime

from kafka import KafkaConsumer
from kafka.errors import KafkaError, KafkaTimeoutError

from src.data_models.schemas.transaction import TransactionEvent

logger = logging.getLogger(__name__)


class TransactionConsumer:
    """Kafka consumer for transaction events."""

    def __init__(self, bootstrap_servers: str, topic: str, group_id: str = None, **kwargs):
        """Initialize the Kafka consumer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Topic to consume messages from
            group_id: Consumer group ID
            **kwargs: Additional Kafka consumer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id or f"fraud-detection-consumer-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        # Default consumer configuration
        default_config = {
            'bootstrap_servers': bootstrap_servers,
            'group_id': self.group_id,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'session_timeout_ms': 30000,
            'heartbeat_interval_ms': 3000,
            'max_poll_records': 500,
            'max_poll_interval_ms': 300000,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
            'key_deserializer': lambda m: m.decode('utf-8') if m else None,
        }

        # Override with provided kwargs
        default_config.update(kwargs)

        try:
            self.consumer = KafkaConsumer(**default_config)
            self.consumer.subscribe([topic])
            logger.info(
                "Kafka consumer initialized for topic: %s, group: %s", topic, self.group_id)
        except (ValueError, RuntimeError, ImportError) as e:
            logger.error("Failed to initialize Kafka consumer: %s", e)
            raise

    def consume_messages(self, message_handler: Callable[[TransactionEvent], None],
                         timeout_ms: int = 1000, max_messages: int = None):
        """Consume messages from Kafka topic.

        Args:
            message_handler: Function to handle each message
            timeout_ms: Timeout for polling messages
            max_messages: Maximum number of messages to consume (None for unlimited)
        """
        message_count = 0

        try:
            logger.info(
                "Starting to consume messages from topic: %s", self.topic)

            while True:
                if max_messages and message_count >= max_messages:
                    logger.info(
                        "Reached maximum message count: %d", max_messages)
                    break

                try:
                    # Poll for messages
                    message_batch = self.consumer.poll(timeout_ms=timeout_ms)

                    for _, messages in message_batch.items():
                        for message in messages:
                            try:
                                # Parse message
                                event_data = message.value
                                transaction_event = TransactionEvent(
                                    **event_data)

                                # Handle message
                                message_handler(transaction_event)

                                message_count += 1
                                logger.debug(
                                    "Processed message %d: %s", message_count, transaction_event.transaction.transaction_id)

                            except (ValueError, AttributeError, TypeError) as e:
                                logger.error("Error processing message: %s", e)
                                continue

                except KafkaTimeoutError:
                    # No messages available, continue polling
                    continue
                except KafkaError as e:
                    logger.error("Kafka error: %s", e)
                    continue
                except (ValueError, RuntimeError, AttributeError) as e:
                    logger.error("Unexpected error: %s", e)
                    continue

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping consumer")
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Error in consumer loop: %s", e)
        finally:
            self.close()

    def consume_single_message(self, timeout_ms: int = 5000) -> Optional[TransactionEvent]:
        """Consume a single message from the topic.

        Args:
            timeout_ms: Timeout for polling messages

        Returns:
            TransactionEvent if message found, None otherwise
        """
        try:
            message_batch = self.consumer.poll(timeout_ms=timeout_ms)

            for _, messages in message_batch.items():
                for message in messages:
                    try:
                        event_data = message.value
                        transaction_event = TransactionEvent(**event_data)
                        return transaction_event
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.error("Error parsing message: %s", e)
                        continue

            return None

        except KafkaTimeoutError:
            return None
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Error consuming message: %s", e)
            return None

    def get_topic_info(self) -> Dict[str, Any]:
        """Get information about the topic."""
        try:
            partitions = self.consumer.partitions_for_topic(self.topic)
            if partitions:
                return {
                    'topic': self.topic,
                    'partitions': list(partitions),
                    'group_id': self.group_id,
                    'consumer_id': self.consumer.config['group_id']
                }
            else:
                return {
                    'topic': self.topic,
                    'error': 'Topic not found or no partitions available'
                }
        except (ValueError, RuntimeError, AttributeError) as e:
            return {
                'topic': self.topic,
                'error': str(e)
            }

    def close(self, timeout_ms: int = 5000):
        """Close the Kafka consumer.

        Args:
            timeout_ms: Timeout for close operation
        """
        try:
            self.consumer.close(timeout_ms=timeout_ms)
            logger.info("Kafka consumer closed successfully")
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.error("Error closing Kafka consumer: %s", e)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class TransactionConsumerFactory:
    """Factory for creating transaction consumers with different configurations."""

    @staticmethod
    def create_high_throughput_consumer(bootstrap_servers: str, topic: str, group_id: str = None) -> TransactionConsumer:
        """Create a consumer optimized for high throughput."""
        config = {
            'max_poll_records': 1000,
            'fetch_max_bytes': 52428800,  # 50MB
            'fetch_max_wait_ms': 500,
            'max_partition_fetch_bytes': 1048576,  # 1MB
        }
        return TransactionConsumer(bootstrap_servers, topic, group_id, **config)

    @staticmethod
    def create_low_latency_consumer(bootstrap_servers: str, topic: str, group_id: str = None) -> TransactionConsumer:
        """Create a consumer optimized for low latency."""
        config = {
            'max_poll_records': 100,
            'fetch_max_wait_ms': 100,
            'max_partition_fetch_bytes': 1048576,  # 1MB
        }
        return TransactionConsumer(bootstrap_servers, topic, group_id, **config)

    @staticmethod
    def create_reliable_consumer(bootstrap_servers: str, topic: str, group_id: str = None) -> TransactionConsumer:
        """Create a consumer optimized for reliability."""
        config = {
            'enable_auto_commit': False,
            'max_poll_records': 100,
            'session_timeout_ms': 60000,
            'heartbeat_interval_ms': 10000,
        }
        return TransactionConsumer(bootstrap_servers, topic, group_id, **config)
