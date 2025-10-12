"""
FastAPI application for fraud detection system monitoring and management.
"""
import logging
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.data_models.schemas.transaction import Transaction, TransactionEvent, Alert
from src.fraud_detection.rules.rule_engine import FraudRuleEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Real-Time Fraud Detection System",
    description="API for monitoring and managing the fraud detection system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
rule_engine = FraudRuleEngine()
kafka_producer = None

# System statistics
system_stats = {
    'start_time': datetime.now(timezone.utc),
    'total_transactions_processed': 0,
    'total_alerts_generated': 0,
    'total_fraudulent_transactions': 0,
    'average_fraud_score': 0.0,
    'last_activity': None
}


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    # global kafka_producer  # Commented out since not used

    try:
        # Initialize Kafka producer (optional - will work without Kafka)
        # bootstrap_servers = os.getenv(
        #     'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        # topic = os.getenv('KAFKA_TOPIC_TRANSACTIONS', 'fraud-transactions')

        # Note: Kafka producer initialization is optional for API functionality
        # kafka_producer = TransactionProducerFactory.create_reliable_producer(
        #     bootstrap_servers, topic
        # )

        logger.info("FastAPI application started successfully")

    except Exception as e:
        logger.error("Failed to initialize application: %s", e)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    # global kafka_producer  # Commented out since not used

    if kafka_producer:
        kafka_producer.close()
        logger.info("Kafka producer closed")


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "Real-Time Fraud Detection System API",
        "version": "1.0.0",
        "status": "running",
        "uptime": str(datetime.utcnow() - system_stats['start_time'])
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "kafka_producer": "connected" if kafka_producer else "disconnected",
            "rule_engine": "ready"
        }
    }


@app.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    return {
        **system_stats,
        'start_time': system_stats['start_time'].isoformat(),
        'last_activity': system_stats['last_activity'].isoformat() if system_stats['last_activity'] else None
    }


@app.post("/transactions/evaluate")
async def evaluate_transaction(transaction: Transaction):
    """Evaluate a single transaction for fraud."""
    try:
        # Evaluate transaction
        fraud_score = rule_engine.evaluate_transaction(transaction)

        # Update statistics
        system_stats['total_transactions_processed'] += 1
        system_stats['last_activity'] = datetime.utcnow()

        # Update average fraud score
        current_avg = system_stats['average_fraud_score']
        total_processed = system_stats['total_transactions_processed']
        new_avg = ((current_avg * (total_processed - 1)) +
                   fraud_score.score) / total_processed
        system_stats['average_fraud_score'] = new_avg

        # Check if alert should be generated
        alert = None
        if fraud_score.score >= 0.6:
            system_stats['total_alerts_generated'] += 1
            if fraud_score.score >= 0.8:
                system_stats['total_fraudulent_transactions'] += 1

            alert = Alert(
                transaction_id=transaction.transaction_id,
                fraud_score=fraud_score,
                alert_type="FRAUD_DETECTED" if fraud_score.score >= 0.8 else "SUSPICIOUS_ACTIVITY",
                severity=fraud_score.risk_level,
                description=f"Fraud score: {fraud_score.score:.3f} for transaction {transaction.transaction_id}"
            )

        return {
            "transaction_id": transaction.transaction_id,
            "fraud_score": fraud_score,
            "alert": alert.dict() if alert else None
        }

    except Exception as e:
        logger.error("Error evaluating transaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/transactions/send")
async def send_transaction(transaction_event: TransactionEvent):
    """Send a transaction event to Kafka."""
    try:
        if not kafka_producer:
            raise HTTPException(
                status_code=503, detail="Kafka producer not available")

        # Send to Kafka
        success = kafka_producer.send_transaction_sync(transaction_event)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to send transaction to Kafka")

        # Update statistics
        system_stats['last_activity'] = datetime.now(timezone.utc)

        return {
            "message": "Transaction sent successfully",
            "transaction_id": transaction_event.transaction.transaction_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Error sending transaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/rules")
async def get_fraud_rules():
    """Get information about fraud detection rules."""
    try:
        rule_summary = rule_engine.get_rule_summary()
        return rule_summary

    except Exception as e:
        logger.error("Error getting fraud rules: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/users/{user_id}/history")
async def get_user_history(user_id: str):
    """Get transaction history for a specific user."""
    try:
        context = rule_engine.get_user_context(user_id)

        return {
            "user_id": user_id,
            "transaction_count": len(context.get('user_transactions', [])),
            "locations": list(context.get('user_locations', [])),
            "risk_profile": context.get('user_risk_profile', 'low'),
            "recent_transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "amount": float(t.amount),
                    "timestamp": t.timestamp.isoformat(),
                    "merchant_id": t.merchant_id
                }
                # Last 10 transactions
                for t in context.get('user_transactions', [])[-10:]
            ]
        }

    except Exception as e:
        logger.error("Error getting user history: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/simulate/transaction")
async def simulate_transaction(background_tasks: BackgroundTasks):
    """Simulate a transaction for testing purposes."""
    try:
        from src.transaction_simulator.generator import TransactionGenerator

        # Generate a test transaction
        generator = TransactionGenerator()
        event = generator.generate_transaction('normal')

        # Send to Kafka in background
        if kafka_producer:
            background_tasks.add_task(
                kafka_producer.send_transaction_sync, event
            )

        return {
            "message": "Test transaction generated and sent",
            "transaction": event.transaction.dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Error simulating transaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/simulate/fraudulent")
async def simulate_fraudulent_transaction(background_tasks: BackgroundTasks):
    """Simulate a fraudulent transaction for testing purposes."""
    try:
        from src.transaction_simulator.generator import TransactionGenerator

        # Generate a fraudulent transaction
        generator = TransactionGenerator()
        event = generator.generate_transaction('fraudulent')

        # Send to Kafka in background
        if kafka_producer:
            background_tasks.add_task(
                kafka_producer.send_transaction_sync, event
            )

        return {
            "message": "Fraudulent transaction generated and sent",
            "transaction": event.transaction.dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Error simulating fraudulent transaction: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def main():
    """Run the FastAPI application."""
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
