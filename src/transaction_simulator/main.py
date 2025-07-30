"""
Main transaction simulator for generating and sending transaction data to Kafka.
"""
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import List
import os

from kafka import KafkaProducer
from kafka.errors import KafkaError

from src.transaction_simulator.generator import TransactionGenerator
from src.data_models.schemas.transaction import TransactionEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransactionSimulator:
    """Main transaction simulator that generates and sends transactions to Kafka."""

    def __init__(self, kafka_bootstrap_servers: str, topic: str):
        """Initialize the transaction simulator."""
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.topic = topic
        self.producer = None
        self.generator = TransactionGenerator(seed=42)
        self.running = False
        self.stats = {
            'total_sent': 0,
            'total_errors': 0,
            'start_time': None,
            'last_sent': None
        }

        # Configure Kafka producer
        self._setup_kafka_producer()

    def _setup_kafka_producer(self):
        """Set up Kafka producer with proper configuration."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(
                    v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432,
                max_request_size=1048576
            )
            logger.info("Kafka producer initialized for topic: %s", self.topic)
        except Exception as e:
            logger.error("Failed to initialize Kafka producer: %s", e)
            raise

    def _send_transaction(self, event: TransactionEvent) -> bool:
        """Send a single transaction event to Kafka."""
        try:
            # Use transaction ID as key for partitioning
            key = event.transaction.transaction_id

            # Convert event to dict for JSON serialization
            event_dict = event.dict()

            # Send to Kafka
            future = self.producer.send(
                topic=self.topic,
                key=key,
                value=event_dict
            )

            # Wait for the send to complete
            record_metadata = future.get(timeout=10)

            self.stats['total_sent'] += 1
            self.stats['last_sent'] = datetime.now(timezone.utc)

            logger.debug(
                "Transaction sent: %s to partition %d at offset %d",
                event.transaction.transaction_id,
                record_metadata.partition,
                record_metadata.offset
            )

            return True

        except KafkaError as e:
            logger.error("Kafka error sending transaction: %s", e)
            self.stats['total_errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending transaction: {e}")
            self.stats['total_errors'] += 1
            return False

    def _send_batch(self, events: List[TransactionEvent]) -> int:
        """Send a batch of transaction events to Kafka."""
        successful_sends = 0

        for event in events:
            if self._send_transaction(event):
                successful_sends += 1

        return successful_sends

    async def run_normal_traffic(self, transactions_per_minute: int = 60):
        """Run normal transaction traffic simulation."""
        logger.info(
            f"Starting normal traffic simulation: {transactions_per_minute} transactions/minute")

        while self.running:
            try:
                # Generate batch of normal transactions
                batch_size = max(1, transactions_per_minute // 60)  # Send every second
                events = self.generator.generate_batch(batch_size, 'normal')

                # Send batch
                successful = self._send_batch(events)

                if successful > 0:
                    logger.info(f"Sent {successful} normal transactions")

                # Wait before next batch
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in normal traffic simulation: {e}")
                await asyncio.sleep(1)

    async def run_suspicious_traffic(self, transactions_per_minute: int = 10):
        """Run suspicious transaction traffic simulation."""
        logger.info(
            f"Starting suspicious traffic simulation: {transactions_per_minute} transactions/minute")

        while self.running:
            try:
                # Generate batch of suspicious transactions
                batch_size = max(1, transactions_per_minute // 60)
                events = self.generator.generate_batch(
                    batch_size, 'suspicious')

                # Send batch
                successful = self._send_batch(events)

                if successful > 0:
                    logger.info(f"Sent {successful} suspicious transactions")

                # Wait before next batch
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in suspicious traffic simulation: {e}")
                await asyncio.sleep(1)

    async def run_fraudulent_traffic(self, transactions_per_minute: int = 5):
        """Run fraudulent transaction traffic simulation."""
        logger.info(
            f"Starting fraudulent traffic simulation: {transactions_per_minute} transactions/minute")

        while self.running:
            try:
                # Generate batch of fraudulent transactions
                batch_size = max(1, transactions_per_minute // 60)
                events = self.generator.generate_batch(
                    batch_size, 'fraudulent')

                # Send batch
                successful = self._send_batch(events)

                if successful > 0:
                    logger.info(f"Sent {successful} fraudulent transactions")

                # Wait before next batch
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in fraudulent traffic simulation: {e}")
                await asyncio.sleep(1)

    async def run_mixed_traffic(self):
        """Run mixed traffic simulation with different patterns."""
        logger.info("Starting mixed traffic simulation")

        # Create tasks for different traffic patterns
        tasks = [
            asyncio.create_task(self.run_normal_traffic(60)),
            asyncio.create_task(self.run_suspicious_traffic(10)),
            asyncio.create_task(self.run_fraudulent_traffic(5))
        ]

        try:
            # Wait for all tasks to complete (they won't unless running is set to False)
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in mixed traffic simulation: {e}")

    def start(self):
        """Start the transaction simulator."""
        self.running = True
        self.stats['start_time'] = datetime.now(timezone.utc)
        logger.info("Transaction simulator started")

    def stop(self):
        """Stop the transaction simulator."""
        self.running = False
        logger.info("Transaction simulator stopped")

        if self.producer:
            self.producer.flush()
            self.producer.close()

        # Print final statistics
        self._print_stats()

    def _print_stats(self):
        """Print simulation statistics."""
        duration = (datetime.now(timezone.utc)
                    - self.stats['start_time']) if self.stats['start_time'] else None

        logger.info("=== Simulation Statistics ===")
        logger.info("Total transactions sent: %d", self.stats['total_sent'])
        logger.info("Total errors: %d", self.stats['total_errors'])
        logger.info(
            "Success rate: %.2f%%",
            ((self.stats['total_sent'] - self.stats['total_errors']) / max(1, self.stats['total_sent'])) * 100)

        if duration:
            logger.info("Duration: %s", duration)
            logger.info(
                "Transactions per second: %.2f",
                self.stats['total_sent'] / duration.total_seconds())


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received signal %d, shutting down...", signum)
    if hasattr(signal_handler, 'simulator'):
        signal_handler.simulator.stop()
    sys.exit(0)


async def main():
    """Main function to run the transaction simulator."""
    # Load configuration from environment
    kafka_bootstrap_servers = os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    kafka_topic = os.getenv('KAFKA_TOPIC_TRANSACTIONS', 'fraud-transactions')

    # Create simulator
    simulator = TransactionSimulator(kafka_bootstrap_servers, kafka_topic)

    # Set up signal handlers
    signal_handler.simulator = simulator
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start simulator
        simulator.start()

        # Run mixed traffic simulation
        await simulator.run_mixed_traffic()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
    finally:
        simulator.stop()


if __name__ == "__main__":
    asyncio.run(main())
