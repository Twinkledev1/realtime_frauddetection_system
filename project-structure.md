# Real-Time Fraud Detection System - Project Structure

```
real-time-fraud-detection/
│
├── 📁 .github/
│   └── 📁 workflows/
│       ├── 📄 ci-cd.yml                    # GitHub Actions CI/CD pipeline
│       ├── 📄 test.yml                     # Automated testing workflow
│       ├── 📄 deploy.yml                   # Deployment workflow
│       └── 📄 security-scan.yml            # Security scanning workflow
│
├── 📁 infrastructure/
│   ├── 📁 terraform/
│   │   ├── 📁 modules/
│   │   │   ├── 📁 vpc/                     # VPC module
│   │   │   ├── 📁 kafka/                   # Kafka cluster module
│   │   │   ├── 📁 spark/                   # Spark cluster module
│   │   │   ├── 📁 s3/                      # S3 buckets module
│   │   │   ├── 📁 lambda/                  # Lambda functions module
│   │   │   ├── 📁 redshift/                # Redshift cluster module
│   │   │   ├── 📁 monitoring/              # CloudWatch monitoring module
│   │   │   └── 📁 security/                # Security groups and IAM module
│   │   ├── 📁 environments/
│   │   │   ├── 📁 development/
│   │   │   │   ├── 📄 main.tf
│   │   │   │   ├── 📄 variables.tf
│   │   │   │   ├── 📄 outputs.tf
│   │   │   │   └── 📄 terraform.tfvars
│   │   │   ├── 📁 staging/
│   │   │   │   ├── 📄 main.tf
│   │   │   │   ├── 📄 variables.tf
│   │   │   │   ├── 📄 outputs.tf
│   │   │   │   └── 📄 terraform.tfvars
│   │   │   └── 📁 production/
│   │   │       ├── 📄 main.tf
│   │   │       ├── 📄 variables.tf
│   │   │       ├── 📄 outputs.tf
│   │   │       └── 📄 terraform.tfvars
│   │   ├── 📄 main.tf                      # Main Terraform configuration
│   │   ├── 📄 variables.tf                 # Terraform variables
│   │   ├── 📄 outputs.tf                   # Terraform outputs
│   │   └── 📄 versions.tf                  # Provider versions
│   │
│   ├── 📁 docker/
│   │   ├── 📄 Dockerfile.app               # Application Dockerfile
│   │   ├── 📄 Dockerfile.spark             # Spark Dockerfile
│   │   ├── 📄 Dockerfile.kafka             # Kafka Dockerfile
│   │   └── 📄 .dockerignore
│   │
│   └── 📁 kubernetes/
│       ├── 📁 namespaces/
│       │   └── 📄 fraud-detection.yml
│       ├── 📁 deployments/
│       │   ├── 📄 kafka.yml
│       │   ├── 📄 spark-master.yml
│       │   ├── 📄 spark-worker.yml
│       │   ├── 📄 fraud-detection-app.yml
│       │   └── 📄 monitoring.yml
│       ├── 📁 services/
│       │   ├── 📄 kafka-service.yml
│       │   ├── 📄 spark-service.yml
│       │   └── 📄 app-service.yml
│       ├── 📁 configmaps/
│       │   ├── 📄 app-config.yml
│       │   └── 📄 spark-config.yml
│       └── 📁 secrets/
│           └── 📄 aws-credentials.yml
│
├── 📁 src/
│   ├── 📁 transaction_simulator/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                      # Main simulator entry point
│   │   ├── 📄 generator.py                 # Transaction data generator
│   │   ├── 📄 models.py                    # Transaction data models
│   │   ├── 📄 config.py                    # Simulator configuration
│   │   └── 📄 utils.py                     # Simulator utilities
│   │
│   ├── 📁 kafka_producers/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 producer.py                  # Kafka producer implementation
│   │   ├── 📄 schema_registry.py           # Schema registry integration
│   │   ├── 📄 serializers.py               # Data serialization
│   │   └── 📄 config.py                    # Kafka configuration
│   │
│   ├── 📁 spark_streaming/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 fraud_detection_job.py       # Main Spark Streaming job
│   │   ├── 📄 stream_processor.py          # Stream processing logic
│   │   ├── 📄 window_operations.py         # Window-based operations
│   │   ├── 📄 state_management.py          # State management
│   │   └── 📄 config.py                    # Spark configuration
│   │
│   ├── 📁 fraud_detection/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 engine.py                    # Main fraud detection engine
│   │   ├── 📄 rules/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 velocity_check.py        # Velocity-based fraud detection
│   │   │   ├── 📄 amount_anomaly.py        # Amount anomaly detection
│   │   │   ├── 📄 geographic_check.py      # Geographic anomaly detection
│   │   │   ├── 📄 time_pattern.py          # Time-based pattern detection
│   │   │   ├── 📄 device_fingerprint.py    # Device fingerprinting
│   │   │   └── 📄 merchant_risk.py         # Merchant risk scoring
│   │   ├── 📄 scoring/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 risk_calculator.py       # Risk score calculation
│   │   │   ├── 📄 confidence_engine.py     # Confidence scoring
│   │   │   └── 📄 threshold_manager.py     # Threshold management
│   │   ├── 📄 ml_models/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 anomaly_detector.py      # ML anomaly detection
│   │   │   ├── 📄 classifier.py            # ML classification
│   │   │   └── 📄 model_manager.py         # Model management
│   │   └── 📄 config.py                    # Fraud detection configuration
│   │
│   ├── 📁 lambda_functions/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 alert_processor/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 main.py                  # Alert processing Lambda
│   │   │   ├── 📄 notifier.py              # Notification logic
│   │   │   └── 📄 config.py                # Lambda configuration
│   │   ├── 📄 data_processor/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 main.py                  # Data processing Lambda
│   │   │   ├── 📄 transformer.py           # Data transformation
│   │   │   └── 📄 config.py                # Lambda configuration
│   │   └── 📄 utils/
│   │       ├── 📄 __init__.py
│   │       ├── 📄 aws_helpers.py           # AWS service helpers
│   │       └── 📄 logging.py               # Lambda logging utilities
│   │
│   ├── 📁 data_models/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 transaction.py               # Transaction data model
│   │   ├── 📄 alert.py                     # Alert data model
│   │   ├── 📄 fraud_score.py               # Fraud score model
│   │   ├── 📄 schemas/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 avro_schemas.py          # Avro schema definitions
│   │   │   ├── 📄 json_schemas.py          # JSON schema definitions
│   │   │   └── 📄 validation.py            # Schema validation
│   │   └── 📄 database/
│   │       ├── 📄 __init__.py
│   │       ├── 📄 models.py                # Database models
│   │       ├── 📄 migrations/              # Database migrations
│   │       └── 📄 connection.py            # Database connection
│   │
│   ├── 📁 api/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                      # FastAPI application
│   │   ├── 📄 routes/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 transactions.py          # Transaction endpoints
│   │   │   ├── 📄 alerts.py                # Alert endpoints
│   │   │   ├── 📄 metrics.py               # Metrics endpoints
│   │   │   └── 📄 health.py                # Health check endpoints
│   │   ├── 📄 middleware/
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 auth.py                  # Authentication middleware
│   │   │   ├── 📄 logging.py               # Logging middleware
│   │   │   └── 📄 cors.py                  # CORS middleware
│   │   └── 📄 config.py                    # API configuration
│   │
│   ├── 📁 utils/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 logger.py                    # Logging utilities
│   │   ├── 📄 config.py                    # Configuration management
│   │   ├── 📄 aws_client.py                # AWS client utilities
│   │   ├── 📄 kafka_client.py              # Kafka client utilities
│   │   ├── 📄 spark_client.py              # Spark client utilities
│   │   ├── 📄 metrics.py                   # Metrics collection
│   │   ├── 📄 encryption.py                # Encryption utilities
│   │   └── 📄 helpers.py                   # General helper functions
│   │
│   └── 📄 main.py                          # Main application entry point
│
├── 📁 tests/
│   ├── 📁 unit/
│   │   ├── 📄 __init__.py
│   │   ├── 📁 transaction_simulator/
│   │   │   ├── 📄 test_generator.py
│   │   │   └── 📄 test_models.py
│   │   ├── 📁 fraud_detection/
│   │   │   ├── 📄 test_engine.py
│   │   │   ├── 📄 test_rules/
│   │   │   │   ├── 📄 test_velocity_check.py
│   │   │   │   ├── 📄 test_amount_anomaly.py
│   │   │   │   └── 📄 test_geographic_check.py
│   │   │   └── 📄 test_scoring/
│   │   │       ├── 📄 test_risk_calculator.py
│   │   │       └── 📄 test_confidence_engine.py
│   │   ├── 📁 data_models/
│   │   │   ├── 📄 test_transaction.py
│   │   │   └── 📄 test_alert.py
│   │   └── 📁 utils/
│   │       ├── 📄 test_logger.py
│   │       └── 📄 test_config.py
│   │
│   ├── 📁 integration/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_kafka_integration.py    # Kafka integration tests
│   │   ├── 📄 test_spark_integration.py    # Spark integration tests
│   │   ├── 📄 test_aws_integration.py      # AWS integration tests
│   │   ├── 📄 test_end_to_end.py           # End-to-end tests
│   │   └── 📄 conftest.py                  # Integration test configuration
│   │
│   └── 📁 performance/
│       ├── 📄 __init__.py
│       ├── 📄 locustfile.py                # Load testing with Locust
│       ├── 📄 stress_test.py               # Stress testing
│       ├── 📄 benchmark.py                 # Performance benchmarks
│       └── 📄 conftest.py                  # Performance test configuration
│
├── 📁 config/
│   ├── 📁 development/
│   │   ├── 📄 app.yml                      # Development app configuration
│   │   ├── 📄 kafka.yml                    # Development Kafka configuration
│   │   ├── 📄 spark.yml                    # Development Spark configuration
│   │   ├── 📄 aws.yml                      # Development AWS configuration
│   │   └── 📄 monitoring.yml               # Development monitoring configuration
│   │
│   ├── 📁 staging/
│   │   ├── 📄 app.yml                      # Staging app configuration
│   │   ├── 📄 kafka.yml                    # Staging Kafka configuration
│   │   ├── 📄 spark.yml                    # Staging Spark configuration
│   │   ├── 📄 aws.yml                      # Staging AWS configuration
│   │   └── 📄 monitoring.yml               # Staging monitoring configuration
│   │
│   └── 📁 production/
│       ├── 📄 app.yml                      # Production app configuration
│       ├── 📄 kafka.yml                    # Production Kafka configuration
│       ├── 📄 spark.yml                    # Production Spark configuration
│       ├── 📄 aws.yml                      # Production AWS configuration
│       └── 📄 monitoring.yml               # Production monitoring configuration
│
├── 📁 docs/
│   ├── 📄 architecture.md                  # System architecture documentation
│   ├── 📄 api.md                           # API documentation
│   ├── 📄 deployment.md                    # Deployment guide
│   ├── 📄 troubleshooting.md               # Troubleshooting guide
│   ├── 📄 security.md                      # Security documentation
│   ├── 📄 performance.md                   # Performance optimization guide
│   ├── 📄 contributing.md                  # Contributing guidelines
│   └── 📁 diagrams/
│       ├── 📄 system-architecture.png      # System architecture diagram
│       ├── 📄 data-flow.png                # Data flow diagram
│       └── 📄 deployment-diagram.png       # Deployment diagram
│
├── 📁 scripts/
│   ├── 📄 setup.sh                         # Initial setup script
│   ├── 📄 deploy.sh                        # Deployment script
│   ├── 📄 backup.sh                        # Backup script
│   ├── 📄 restore.sh                       # Restore script
│   ├── 📄 health_check.sh                  # Health check script
│   ├── 📄 performance_test.sh              # Performance testing script
│   ├── 📄 cleanup.sh                       # Cleanup script
│   └── 📄 generate_data.py                 # Data generation script
│
├── 📁 monitoring/
│   ├── 📁 grafana/
│   │   ├── 📁 dashboards/
│   │   │   ├── 📄 fraud-detection.json     # Fraud detection dashboard
│   │   │   ├── 📄 system-metrics.json      # System metrics dashboard
│   │   │   ├── 📄 kafka-metrics.json       # Kafka metrics dashboard
│   │   │   └── 📄 spark-metrics.json       # Spark metrics dashboard
│   │   └── 📁 datasources/
│   │       ├── 📄 prometheus.yml           # Prometheus data source
│   │       └── 📄 elasticsearch.yml        # Elasticsearch data source
│   │
│   ├── 📁 prometheus/
│   │   ├── 📄 prometheus.yml               # Prometheus configuration
│   │   ├── 📄 alert_rules.yml              # Alert rules
│   │   └── 📄 recording_rules.yml          # Recording rules
│   │
│   ├── 📁 elasticsearch/
│   │   ├── 📄 elasticsearch.yml            # Elasticsearch configuration
│   │   └── 📄 logstash.conf                # Logstash configuration
│   │
│   └── 📁 custom_metrics/
│       ├── 📄 fraud_metrics.py             # Custom fraud detection metrics
│       ├── 📄 business_metrics.py          # Business metrics
│       └── 📄 system_metrics.py            # System performance metrics
│
├── 📁 data/
│   ├── 📁 raw/                             # Raw transaction data
│   ├── 📁 processed/                       # Processed transaction data
│   ├── 📁 alerts/                          # Generated alerts
│   ├── 📁 models/                          # ML models
│   └── 📁 samples/                         # Sample data for testing
│
├── 📁 logs/                                # Application logs
│
├── 📁 .env.example                         # Environment variables template
├── 📄 .env                                 # Environment variables (gitignored)
├── 📄 .gitignore                           # Git ignore file
├── 📄 README.md                            # Project README
├── 📄 plan.md                              # Project plan and OKRs
├── 📄 technical-requirements.md            # Technical requirements
├── 📄 requirements.txt                     # Python dependencies
├── 📄 requirements-dev.txt                 # Development dependencies
├── 📄 pyproject.toml                       # Project configuration
├── 📄 docker-compose.yml                   # Docker Compose configuration
├── 📄 Makefile                             # Build and deployment commands
├── 📄 LICENSE                              # Project license
├── 📄 CHANGELOG.md                         # Change log
├── 📄 CONTRIBUTING.md                      # Contributing guidelines
├── 📄 SECURITY.md                          # Security policy
└── 📄 CODE_OF_CONDUCT.md                   # Code of conduct
```

## Key File Descriptions

### Core Application Files
- **`src/main.py`**: Main application entry point
- **`src/transaction_simulator/main.py`**: Transaction data generator
- **`src/spark_streaming/fraud_detection_job.py`**: Spark Streaming job
- **`src/fraud_detection/engine.py`**: Fraud detection engine
- **`src/api/main.py`**: FastAPI web application

### Configuration Files
- **`config/*/app.yml`**: Application configuration per environment
- **`config/*/kafka.yml`**: Kafka configuration per environment
- **`config/*/spark.yml`**: Spark configuration per environment
- **`config/*/aws.yml`**: AWS configuration per environment

### Infrastructure Files
- **`infrastructure/terraform/main.tf`**: Main Terraform configuration
- **`docker-compose.yml`**: Local development environment
- **`infrastructure/kubernetes/`**: Kubernetes deployment manifests

### Testing Files
- **`tests/unit/`**: Unit tests for individual components
- **`tests/integration/`**: Integration tests for system components
- **`tests/performance/`**: Performance and load tests

### Documentation Files
- **`docs/architecture.md`**: System architecture documentation
- **`docs/api.md`**: API documentation
- **`docs/deployment.md`**: Deployment guide

### Monitoring Files
- **`monitoring/grafana/dashboards/`**: Grafana dashboard configurations
- **`monitoring/prometheus/prometheus.yml`**: Prometheus configuration
- **`monitoring/custom_metrics/`**: Custom metrics collection

### Scripts
- **`scripts/setup.sh`**: Initial project setup
- **`scripts/deploy.sh`**: Deployment automation
- **`scripts/health_check.sh`**: System health monitoring

This structure provides a comprehensive, scalable, and maintainable foundation for the real-time fraud detection system with clear separation of concerns, proper testing structure, and production-ready configuration management.


