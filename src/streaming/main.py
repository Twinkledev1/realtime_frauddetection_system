#!/usr/bin/env python3
"""
Main script to run the streaming pipeline for fraud detection.
"""
import os
import signal
import sys
import logging
from datetime import datetime

from src.streaming.pipeline_manager import StreamingPipelineManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/streaming_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)


class SignalHandler:
    """Handle system signals for graceful shutdown."""

    def __init__(self, pipeline_manager: StreamingPipelineManager):
        self.pipeline_manager = pipeline_manager

    def __call__(self, signum, frame):
        logger.info("Received signal %d, shutting down gracefully...", signum)
        self.pipeline_manager.stop()
        sys.exit(0)


def setup_callbacks(pipeline_manager: StreamingPipelineManager):
    """Set up callback functions for pipeline events."""

    def on_transaction_processed(transaction_event, fraud_score):
        """Callback for processed transactions."""
        logger.info(
            "Transaction processed: %s (score: %.3f, risk: %s)",
            transaction_event.transaction.transaction_id,
            fraud_score.score,
            fraud_score.risk_level
        )

    def on_alert_generated(alert):
        """Callback for generated alerts."""
        logger.warning(
            "Alert generated: %s (type: %s, severity: %s)",
            alert.transaction_id,
            alert.alert_type,
            alert.severity
        )

    def on_error(error):
        """Callback for errors."""
        logger.error("Pipeline error: %s", error)

    pipeline_manager.set_callbacks(
        on_transaction_processed=on_transaction_processed,
        on_alert_generated=on_alert_generated,
        on_error=on_error
    )


def print_startup_banner():
    """Print startup banner."""
    print("=" * 80)
    print("🚀 Real-Time Fraud Detection Streaming Pipeline")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 80)
    print()


def print_configuration(config: dict):
    """Print configuration information."""
    print("📋 Configuration:")
    print(f"  Kafka Bootstrap Servers: {config['kafka_bootstrap_servers']}")
    print(f"  Input Topic: {config['input_topic']}")
    print(f"  Output Topic: {config['output_topic']}")
    print(f"  Consumer Group ID: {config['consumer_group_id']}")
    print()


def main():
    """Main function to run the streaming pipeline."""
    # Print startup banner
    print_startup_banner()

    # Load configuration from environment
    config = {
        'kafka_bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'input_topic': os.getenv('KAFKA_TOPIC_TRANSACTIONS', 'fraud-transactions'),
        'output_topic': os.getenv('KAFKA_TOPIC_ALERTS', 'fraud-alerts'),
        'consumer_group_id': os.getenv('KAFKA_CONSUMER_GROUP_ID', 'fraud-detection-pipeline'),
    }

    # Print configuration
    print_configuration(config)

    try:
        # Create pipeline manager
        logger.info("Initializing streaming pipeline manager...")
        pipeline_manager = StreamingPipelineManager(
            kafka_bootstrap_servers=config['kafka_bootstrap_servers'],
            input_topic=config['input_topic'],
            output_topic=config['output_topic'],
            consumer_group_id=config['consumer_group_id']
        )

        # Set up callbacks
        setup_callbacks(pipeline_manager)

        # Set up signal handlers
        signal_handler = SignalHandler(pipeline_manager)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Starting streaming pipeline...")
        print("🔄 Starting streaming pipeline...")
        print("Press Ctrl+C to stop gracefully")
        print()

        # Start the pipeline
        pipeline_manager.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        print("\n🛑 Received keyboard interrupt, shutting down...")
    except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
        logger.error("Error in main: %s", e)
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'pipeline_manager' in locals():
            pipeline_manager.stop()
        print("✅ Pipeline stopped")


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    main()
