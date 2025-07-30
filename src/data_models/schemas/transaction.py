"""
Transaction data models and schemas for the fraud detection system.
"""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class TransactionType(str, Enum):
    """Types of financial transactions."""
    PURCHASE = "purchase"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    REFUND = "refund"


class PaymentMethod(str, Enum):
    """Payment methods for transactions."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CASH = "cash"


class TransactionStatus(str, Enum):
    """Transaction status values."""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FRAUDULENT = "fraudulent"
    SUSPICIOUS = "suspicious"


class Location(BaseModel):
    """Geographic location information."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = Field(..., min_length=2, max_length=3)
    postal_code: Optional[str] = None


class Transaction(BaseModel):
    """Core transaction model."""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    transaction_type: TransactionType
    payment_method: PaymentMethod
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    location: Optional[Location] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Validate amount has appropriate precision."""
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount cannot have more than 2 decimal places')
        return v

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        """Basic IP address validation."""
        if v is not None:
            parts = v.split('.')
            if len(parts) != 4:
                raise ValueError('Invalid IP address format')
            for part in parts:
                if not part.isdigit() or not 0 <= int(part) <= 255:
                    raise ValueError('Invalid IP address format')
        return v

    model_config = ConfigDict()


class TransactionEvent(BaseModel):
    """Event wrapper for transaction data."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(default="transaction.created")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    transaction: Transaction
    source: str = Field(default="transaction_simulator")

    model_config = ConfigDict()


class FraudScore(BaseModel):
    """Fraud detection score and analysis."""
    transaction_id: str
    score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    factors: Dict[str, Any] = Field(default_factory=dict)
    rules_triggered: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()


class Alert(BaseModel):
    """Fraud alert model."""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str
    fraud_score: FraudScore
    alert_type: str = Field(...,
                            pattern="^(FRAUD_DETECTED|SUSPICIOUS_ACTIVITY|HIGH_RISK)$")
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    description: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(
        default="OPEN", pattern="^(OPEN|INVESTIGATING|RESOLVED|FALSE_POSITIVE)$")

    model_config = ConfigDict()
