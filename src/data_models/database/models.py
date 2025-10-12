"""
Database models for the fraud detection system.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Float, DateTime, Text, Boolean,
    ForeignKey, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column


Base = declarative_base()


class Transaction(Base):
    """Transaction model for storing financial transaction data."""

    __tablename__ = 'transactions'

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Transaction details
    transaction_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Merchant information
    merchant_name: Mapped[Optional[str]] = mapped_column(String(255))
    merchant_category: Mapped[Optional[str]] = mapped_column(String(100))

    # Location information
    location_country: Mapped[Optional[str]] = mapped_column(String(2))
    location_city: Mapped[Optional[str]] = mapped_column(String(100))

    # Technical details
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    device_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    fraud_scores: Mapped[List["FraudScore"]] = relationship(
        "FraudScore", back_populates="transaction")
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="transaction")

    def __repr__(self):
        return f"<Transaction(id={self.id}, transaction_id='{self.transaction_id}', amount={self.amount})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'merchant_name': self.merchant_name,
            'merchant_category': self.merchant_category,
            'location_country': self.location_country,
            'location_city': self.location_city,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FraudScore(Base):
    """Fraud score model for storing fraud detection results."""

    __tablename__ = 'fraud_scores'

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to transaction
    transaction_id: Mapped[str] = mapped_column(String(255), ForeignKey(
        'transactions.transaction_id'), nullable=False, index=True)

    # Fraud detection results
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    rules_triggered: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="fraud_scores")

    def __repr__(self):
        return f"<FraudScore(id={self.id}, transaction_id='{self.transaction_id}', score={self.score})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'transaction_id': self.transaction_id,
            'score': self.score,
            'risk_level': self.risk_level,
            'factors': self.factors,
            'rules_triggered': self.rules_triggered,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Alert(Base):
    """Alert model for storing fraud alerts."""

    __tablename__ = 'alerts'

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to transaction
    transaction_id: Mapped[str] = mapped_column(String(255), ForeignKey(
        'transactions.transaction_id'), nullable=False, index=True)

    # Alert details
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default='PENDING', index=True)

    # Processing information
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, transaction_id='{self.transaction_id}', alert_type='{self.alert_type}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'transaction_id': self.transaction_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'description': self.description,
            'status': self.status,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Analytics(Base):
    """Analytics model for storing aggregated metrics."""

    __tablename__ = 'analytics'

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Metric information
    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Dimensions for aggregation
    dimension_name: Mapped[Optional[str]] = mapped_column(String(100))
    dimension_value: Mapped[Optional[str]] = mapped_column(String(255))

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Analytics(id={self.id}, metric_name='{self.metric_name}', value={self.metric_value})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'dimension_name': self.dimension_name,
            'dimension_value': self.dimension_value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserSession(Base):
    """User session model for Redis caching."""

    __tablename__ = 'user_sessions'

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Session details
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    # Session state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id='{self.user_id}', active={self.is_active})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'is_active': self.is_active,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


# Create indexes for performance optimization
Index('idx_transactions_timestamp', Transaction.timestamp)
Index('idx_transactions_user_id', Transaction.user_id)
Index('idx_transactions_amount', Transaction.amount)
Index('idx_fraud_scores_transaction_id', FraudScore.transaction_id)
Index('idx_fraud_scores_score', FraudScore.score)
Index('idx_alerts_status', Alert.status)
Index('idx_alerts_created_at', Alert.created_at)
Index('idx_analytics_timestamp', Analytics.timestamp)
Index('idx_analytics_metric_name', Analytics.metric_name)
Index('idx_user_sessions_user_id', UserSession.user_id)
Index('idx_user_sessions_token', UserSession.session_token)
