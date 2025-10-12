"""
Spark Streaming job for real-time fraud detection.
"""
import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, udf, window, count, sum as sum_col,
    avg, expr, when
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType,
    MapType
)
# Removed unused imports: DataStreamWriter, TransactionEvent, FraudScore, Alert
# from src.fraud_detection.rules.rule_engine import FraudRuleEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FraudDetectionJob:
    """Main Spark Streaming job for fraud detection."""

    def __init__(self):
        """Initialize the fraud detection job."""
        self.spark = None
        # self.rule_engine = FraudRuleEngine()  # Commented out for now
        self.setup_spark()

    def setup_spark(self):
        """Set up Spark session with proper configuration."""
        try:
            self.spark = SparkSession.builder \
                .appName("FraudDetectionStreaming") \
                .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint") \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.sql.adaptive.skewJoin.enabled", "true") \
                .config("spark.sql.streaming.schemaInference", "true") \
                .config("spark.sql.streaming.minBatchesToRetain", "2") \
                .config("spark.sql.streaming.maxBatchesToRetainInMemory", "100") \
                .getOrCreate()

            logger.info("Spark session initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Spark session: %s", e)
            raise

    def get_transaction_schema(self) -> StructType:
        """Get the schema for transaction events."""
        return StructType([
            StructField("event_id", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("source", StringType(), True),
            StructField("transaction", StructType([
                StructField("transaction_id", StringType(), True),
                StructField("user_id", StringType(), True),
                StructField("merchant_id", StringType(), True),
                StructField("amount", DoubleType(), True),
                StructField("currency", StringType(), True),
                StructField("transaction_type", StringType(), True),
                StructField("payment_method", StringType(), True),
                StructField("timestamp", TimestampType(), True),
                StructField("status", StringType(), True),
                StructField("ip_address", StringType(), True),
                StructField("device_id", StringType(), True),
                StructField("location", StructType([
                    StructField("latitude", DoubleType(), True),
                    StructField("longitude", DoubleType(), True),
                    StructField("city", StringType(), True),
                    StructField("state", StringType(), True),
                    StructField("country", StringType(), True),
                    StructField("postal_code", StringType(), True)
                ]), True),
                StructField("metadata", MapType(
                    StringType(), StringType()), True)
            ]), True)
        ])

    def create_kafka_stream(self, bootstrap_servers: str, topic: str):
        """Create Kafka stream for reading transaction events."""
        return self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .option("maxOffsetsPerTrigger", 1000) \
            .load()

    def parse_transactions(self, kafka_df):
        """Parse JSON transaction events from Kafka."""
        schema = self.get_transaction_schema()

        return kafka_df \
            .select(
                col("key").cast("string"),
                from_json(col("value").cast("string"), schema).alias("event")
            ) \
            .select("event.*") \
            .filter(col("event_type") == "transaction.created")

    def apply_fraud_rules(self, transactions_df):
        """Apply fraud detection rules to transactions."""

        # Rule 1: High amount transactions
        high_amount_df = transactions_df \
            .withColumn("is_high_amount", col("transaction.amount") > 10000)

        # Rule 2: Multiple transactions from same user in short time
        _ = high_amount_df \
            .withWatermark("timestamp", "5 minutes") \
            .groupBy(
                window("timestamp", "5 minutes"),
                col("transaction.user_id")
            ) \
            .agg(
                count("*").alias("transaction_count"),
                sum_col("transaction.amount").alias("total_amount"),
                avg("transaction.amount").alias("avg_amount")
            ) \
            .withColumn("is_high_frequency", col("transaction_count") > 10)

        # Rule 3: Geographic anomalies
        geo_anomaly_df = high_amount_df \
            .withColumn("is_geo_anomaly",
                        when(col("transaction.location.country") != "US", True).otherwise(False))

        # Rule 4: Suspicious merchant categories
        suspicious_merchant_df = geo_anomaly_df \
            .withColumn("is_suspicious_merchant",
                        when(col("transaction.metadata.merchant_category").isin(
                            ["gambling", "unknown"]), True)
                        .otherwise(False))

        return suspicious_merchant_df

    def calculate_fraud_score(self, transactions_df):
        """Calculate fraud score for each transaction."""

        def calculate_score(amount, _, is_high_frequency,
                            is_geo_anomaly, is_suspicious_merchant):
            score = 0.0

            # Amount factor (0-30 points)
            if amount > 50000:
                score += 30
            elif amount > 10000:
                score += 20
            elif amount > 5000:
                score += 10

            # Frequency factor (0-25 points)
            if is_high_frequency:
                score += 25

            # Geographic factor (0-25 points)
            if is_geo_anomaly:
                score += 25

            # Merchant factor (0-20 points)
            if is_suspicious_merchant:
                score += 20

            return min(score / 100.0, 1.0)

        score_udf = udf(calculate_score, DoubleType())

        return transactions_df \
            .withColumn("fraud_score", score_udf(
                col("transaction.amount"),
                col("is_high_amount"),
                col("is_high_frequency"),
                col("is_geo_anomaly"),
                col("is_suspicious_merchant")
            )) \
            .withColumn("risk_level",
                        when(col("fraud_score") >= 0.8, "CRITICAL")
                        .when(col("fraud_score") >= 0.6, "HIGH")
                        .when(col("fraud_score") >= 0.4, "MEDIUM")
                        .otherwise("LOW")
                        )

    def generate_alerts(self, scored_df):
        """Generate alerts for high-risk transactions."""
        return scored_df \
            .filter(col("fraud_score") >= 0.6) \
            .withColumn("alert_type",
                        when(col("fraud_score") >= 0.8, "FRAUD_DETECTED")
                        .when(col("fraud_score") >= 0.6, "SUSPICIOUS_ACTIVITY")
                        .otherwise("HIGH_RISK")
                        ) \
            .withColumn("severity",
                        when(col("fraud_score") >= 0.8, "CRITICAL")
                        .when(col("fraud_score") >= 0.6, "HIGH")
                        .otherwise("MEDIUM")
                        ) \
            .withColumn("description",
                        expr(
                            "concat('Fraud score: ', cast(fraud_score as string), "
                            "' for transaction: ', transaction.transaction_id)")
                        )

    def write_to_kafka(self, df, topic: str, bootstrap_servers: str):
        """Write results back to Kafka."""
        return df.writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("topic", topic) \
            .option("checkpointLocation", "/tmp/checkpoint/kafka") \
            .outputMode("append") \
            .start()

    def write_to_console(self, df):
        """Write results to console for debugging."""
        return df.writeStream \
            .format("console") \
            .option("truncate", "false") \
            .outputMode("append") \
            .start()

    def run(self, kafka_bootstrap_servers: str, input_topic: str, output_topic: str):
        """Run the fraud detection streaming job."""
        try:
            logger.info("Starting fraud detection streaming job")

            # Create Kafka stream
            kafka_stream = self.create_kafka_stream(
                kafka_bootstrap_servers, input_topic)

            # Parse transactions
            transactions = self.parse_transactions(kafka_stream)

            # Apply fraud rules
            processed = self.apply_fraud_rules(transactions)

            # Calculate fraud scores
            scored = self.calculate_fraud_score(processed)

            # Generate alerts
            alerts = self.generate_alerts(scored)

            # Write results
            _ = self.write_to_kafka(
                alerts, output_topic, kafka_bootstrap_servers)
            _ = self.write_to_console(alerts)

            logger.info("Fraud detection job started successfully")

            # Wait for termination
            self.spark.streams.awaitAnyTermination()

        except Exception as e:
            logger.error("Error in fraud detection job: %s", e)
            raise
        finally:
            if self.spark:
                self.spark.stop()


def main():
    """Main function to run the fraud detection job."""
    # Load configuration
    kafka_bootstrap_servers = os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    input_topic = os.getenv('KAFKA_TOPIC_TRANSACTIONS', 'fraud-transactions')
    output_topic = os.getenv('KAFKA_TOPIC_ALERTS', 'fraud-alerts')

    # Create and run job
    job = FraudDetectionJob()
    job.run(kafka_bootstrap_servers, input_topic, output_topic)


if __name__ == "__main__":
    main()
