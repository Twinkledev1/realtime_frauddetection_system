#!/usr/bin/env python3
"""
Main script for running the monitoring dashboard API.
Provides real-time monitoring and visualization for the fraud detection system.
"""

from src.monitoring.integration import enable_monitoring, get_monitoring_status
from src.monitoring.alert_manager import alert_manager
from src.monitoring.metrics_collector import metrics_collector
from src.monitoring.dashboard_api import app
import os
import sys
import logging
import signal
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/monitoring.log')
    ]
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Main monitoring service."""

    def __init__(self):
        self.running = False
        self.start_time = None

    def start(self):
        """Start the monitoring service."""
        logger.info("🚀 Starting Fraud Detection Monitoring Service")

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Enable monitoring integration
        enable_monitoring()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True
        self.start_time = datetime.now(timezone.utc)

        logger.info("✅ Monitoring service started successfully")
        logger.info("📊 Dashboard available at: http://localhost:8080")
        logger.info("📖 API documentation at: http://localhost:8080/docs")

        # Log initial status
        status = get_monitoring_status()
        logger.info("📈 Monitoring status: %s", status)

        return True

    def stop(self):
        """Stop the monitoring service."""
        logger.info("🛑 Stopping Fraud Detection Monitoring Service")

        self.running = False

        # Log final metrics
        if self.start_time:
            uptime = (datetime.now(timezone.utc) -
                      self.start_time).total_seconds()
            logger.info("⏱️  Service uptime: %.2f seconds", uptime)

        # Get final metrics summary
        try:
            metrics_summary = metrics_collector.get_metrics_summary()
            alert_summary = alert_manager.get_alert_summary()

            logger.info("📊 Final metrics summary:")
            logger.info(
                "   - Total transactions: %d",
                metrics_summary.get('transaction_metrics', {}).get('total_transactions', 0))
            logger.info(
                "   - Fraud rate: %.2f%%",
                metrics_summary.get('transaction_metrics', {}).get('fraud_rate', 0) * 100)
            logger.info(
                "   - Active alerts: %d", alert_summary.get('active_alerts', 0))

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error getting final metrics: %s", e)

        logger.info("✅ Monitoring service stopped successfully")

    def _signal_handler(self, signum, _):
        """Handle shutdown signals."""
        logger.info("📡 Received signal %d, shutting down gracefully...", signum)
        self.stop()
        sys.exit(0)


def run_dashboard():
    """Run the dashboard API."""
    import uvicorn

    # Create monitoring service
    service = MonitoringService()

    # Start the service
    if not service.start():
        logger.error("❌ Failed to start monitoring service")
        return False

    try:
        # Run the FastAPI app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("📡 Keyboard interrupt received")
    except (ValueError, RuntimeError, AttributeError, TypeError) as e:
        logger.error("❌ Error running dashboard: %s", e)
    finally:
        service.stop()

    return True


def run_health_check():
    """Run a health check on the monitoring system."""
    logger.info("🏥 Running monitoring system health check")

    try:
        # Check metrics collector
        _ = metrics_collector.get_metrics_summary()
        logger.info("✅ Metrics collector: OK")

        # Check alert manager
        _ = alert_manager.get_alert_summary()
        logger.info("✅ Alert manager: OK")

        # Check monitoring integration
        _ = get_monitoring_status()
        logger.info("✅ Monitoring integration: OK")

        # Overall health
        health_status = metrics_collector.get_health_status()
        logger.info("🏥 Overall system health: %s", health_status['status'])

        return True

    except (ValueError, RuntimeError, AttributeError, TypeError) as e:
        logger.error("❌ Health check failed: %s", e)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fraud Detection Monitoring Service")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "health-check"],
        default="dashboard",
        help="Service mode (default: dashboard)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for dashboard API (default: 8080)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for dashboard API (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    if args.mode == "health-check":
        success = run_health_check()
        sys.exit(0 if success else 1)
    else:
        # Update app configuration if needed
        if args.port != 8080 or args.host != "0.0.0.0":
            logger.info(
                "🔧 Using custom configuration: %s:%d", args.host, args.port)

        success = run_dashboard()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
