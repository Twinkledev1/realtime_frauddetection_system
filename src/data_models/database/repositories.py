"""
Repository pattern implementation for data access layer.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, desc, asc, func
from sqlalchemy.exc import SQLAlchemyError

from src.data_models.database.models import Transaction, FraudScore, Alert, Analytics
from src.data_models.database.config import get_db_session, get_redis_client

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common CRUD operations."""

    def __init__(self, model_class):
        self.model_class = model_class

    def create(self, **kwargs) -> Any:
        """Create a new record."""
        with get_db_session() as session:
            if session is None:
                logger.warning(
                    "Database session not available - skipping create operation")
                return None
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    def get_by_id(self, record_id: str) -> Optional[Any]:
        """Get record by ID."""
        with get_db_session() as session:
            if session is None:
                logger.warning(
                    "Database session not available - skipping get_by_id operation")
                return None
            return session.query(self.model_class).filter(self.model_class.id == record_id).first()

    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Any]:
        """Get all records with optional pagination."""
        with get_db_session() as session:
            if session is None:
                logger.warning(
                    "Database session not available - returning empty list")
                return []
            query = session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()

    def update(self, record_id: str, **kwargs) -> Optional[Any]:
        """Update a record."""
        with get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == record_id).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
            return instance

    def delete(self, record_id: str) -> bool:
        """Delete a record."""
        with get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == record_id).first()
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False

    def count(self) -> int:
        """Get total count of records."""
        try:
            with get_db_session() as session:
                if session is None:
                    logger.warning(
                        "Database session not available - returning 0 for count")
                    return 0
                return session.query(self.model_class).count()
        except (AttributeError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.warning(
                "Database count operation failed - returning 0: %s", e)
            return 0


class TransactionRepository(BaseRepository):
    """Repository for transaction data access."""

    def __init__(self):
        super().__init__(Transaction)

    def get_by_transaction_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by transaction ID."""
        with get_db_session() as session:
            return session.query(Transaction).filter(
                Transaction.transaction_id == transaction_id
            ).first()

    def get_by_user_id(self, user_id: str, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions by user ID."""
        with get_db_session() as session:
            query = session.query(Transaction).filter(
                Transaction.user_id == user_id
            ).order_by(desc(Transaction.timestamp))
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Transaction]:
        """Get transactions within a date range."""
        with get_db_session() as session:
            return session.query(Transaction).filter(
                and_(
                    Transaction.timestamp >= start_date,
                    Transaction.timestamp <= end_date
                )
            ).order_by(desc(Transaction.timestamp)).all()

    def get_high_value_transactions(self, min_amount: float, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions above a certain amount."""
        with get_db_session() as session:
            query = session.query(Transaction).filter(
                Transaction.amount >= min_amount
            ).order_by(desc(Transaction.amount))
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_transactions_by_merchant(self, merchant_name: str) -> List[Transaction]:
        """Get transactions by merchant name."""
        with get_db_session() as session:
            return session.query(Transaction).filter(
                Transaction.merchant_name == merchant_name
            ).order_by(desc(Transaction.timestamp)).all()

    def get_transaction_statistics(self, user_id: Optional[str] = None,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get transaction statistics."""
        with get_db_session() as session:
            query = session.query(Transaction)

            if user_id:
                query = query.filter(Transaction.user_id == user_id)
            if start_date:
                query = query.filter(Transaction.timestamp >= start_date)
            if end_date:
                query = query.filter(Transaction.timestamp <= end_date)

            stats = {
                'total_transactions': query.count(),
                'total_amount': query.with_entities(func.sum(Transaction.amount)).scalar() or 0,
                'average_amount': query.with_entities(func.avg(Transaction.amount)).scalar() or 0,
                'max_amount': query.with_entities(func.max(Transaction.amount)).scalar() or 0,
                'min_amount': query.with_entities(func.min(Transaction.amount)).scalar() or 0,
            }

            return stats


class FraudScoreRepository(BaseRepository):
    """Repository for fraud score data access."""

    def __init__(self):
        super().__init__(FraudScore)

    def get_by_transaction_id(self, transaction_id: str) -> Optional[FraudScore]:
        """Get fraud score by transaction ID."""
        with get_db_session() as session:
            return session.query(FraudScore).filter(
                FraudScore.transaction_id == transaction_id
            ).first()

    def get_high_risk_scores(self, min_score: float = 0.6, limit: Optional[int] = None) -> List[FraudScore]:
        """Get fraud scores above a certain threshold."""
        with get_db_session() as session:
            query = session.query(FraudScore).filter(
                FraudScore.score >= min_score
            ).order_by(desc(FraudScore.score))
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_scores_by_risk_level(self, risk_level: str) -> List[FraudScore]:
        """Get fraud scores by risk level."""
        with get_db_session() as session:
            return session.query(FraudScore).filter(
                FraudScore.risk_level == risk_level
            ).order_by(desc(FraudScore.timestamp)).all()

    def get_average_score_by_user(self, user_id: str, days: int = 30) -> float:
        """Get average fraud score for a user over a period."""
        with get_db_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            result = session.query(func.avg(FraudScore.score)).join(Transaction).filter(
                and_(
                    Transaction.user_id == user_id,
                    FraudScore.timestamp >= start_date
                )
            ).scalar()
            return result or 0.0


class AlertRepository(BaseRepository):
    """Repository for alert data access."""

    def __init__(self):
        super().__init__(Alert)

    def get_by_transaction_id(self, transaction_id: str) -> List[Alert]:
        """Get alerts by transaction ID."""
        with get_db_session() as session:
            return session.query(Alert).filter(
                Alert.transaction_id == transaction_id
            ).order_by(desc(Alert.created_at)).all()

    def get_by_status(self, status: str) -> List[Alert]:
        """Get alerts by status."""
        with get_db_session() as session:
            return session.query(Alert).filter(
                Alert.status == status
            ).order_by(desc(Alert.created_at)).all()

    def get_by_severity(self, severity: str) -> List[Alert]:
        """Get alerts by severity."""
        with get_db_session() as session:
            return session.query(Alert).filter(
                Alert.severity == severity
            ).order_by(desc(Alert.created_at)).all()

    def get_pending_alerts(self, limit: Optional[int] = None) -> List[Alert]:
        """Get pending alerts."""
        with get_db_session() as session:
            query = session.query(Alert).filter(
                Alert.status == 'PENDING'
            ).order_by(asc(Alert.created_at))
            if limit:
                query = query.limit(limit)
            return query.all()

    def mark_as_processed(self, alert_id: str) -> bool:
        """Mark alert as processed."""
        with get_db_session() as session:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.status = 'PROCESSED'
                alert.processed_at = datetime.utcnow()
                session.commit()
                return True
            return False


class AnalyticsRepository(BaseRepository):
    """Repository for analytics data access."""

    def __init__(self):
        super().__init__(Analytics)

    def get_metric_by_name(self, metric_name: str,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Analytics]:
        """Get analytics by metric name."""
        with get_db_session() as session:
            query = session.query(Analytics).filter(
                Analytics.metric_name == metric_name)

            if start_date:
                query = query.filter(Analytics.timestamp >= start_date)
            if end_date:
                query = query.filter(Analytics.timestamp <= end_date)

            return query.order_by(desc(Analytics.timestamp)).all()

    def get_metrics_summary(self, metric_names: List[str],
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict[str, float]:
        """Get summary of multiple metrics."""
        with get_db_session() as session:
            query = session.query(Analytics)

            if start_date:
                query = query.filter(Analytics.timestamp >= start_date)
            if end_date:
                query = query.filter(Analytics.timestamp <= end_date)

            results = {}
            for metric_name in metric_names:
                avg_value = query.filter(Analytics.metric_name == metric_name).with_entities(
                    func.avg(Analytics.metric_value)
                ).scalar()
                results[metric_name] = avg_value or 0.0

            return results

    def store_metric(self, metric_name: str, metric_value: float,
                     dimension_name: Optional[str] = None,
                     dimension_value: Optional[str] = None) -> Analytics:
        """Store a new metric."""
        return self.create(
            metric_name=metric_name,
            metric_value=metric_value,
            dimension_name=dimension_name,
            dimension_value=dimension_value,
            timestamp=datetime.utcnow()
        )


class RedisRepository:
    """Repository for Redis data access."""

    def __init__(self):
        try:
            self.redis_client = get_redis_client()
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.warning("Redis client not available: %s", e)
            self.redis_client = None

    def set_cache(self, key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
        """Set cache value."""
        if self.redis_client is None:
            return False
        try:
            self.redis_client.set(key, value, ex=expire_seconds)
            return True
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error setting cache: %s", e)
            return False

    def get_cache(self, key: str) -> Optional[str]:
        """Get cache value."""
        if self.redis_client is None:
            return None
        try:
            return self.redis_client.get(key)
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error getting cache: %s", e)
            return None

    def delete_cache(self, key: str) -> bool:
        """Delete cache value."""
        if self.redis_client is None:
            return False
        try:
            return bool(self.redis_client.delete(key))
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error deleting cache: %s", e)
            return False

    def set_hash(self, key: str, mapping: Dict[str, str], expire_seconds: Optional[int] = None) -> bool:
        """Set hash value."""
        if self.redis_client is None:
            return False
        try:
            self.redis_client.hset(key, mapping=mapping)
            if expire_seconds:
                self.redis_client.expire(key, expire_seconds)
            return True
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error setting hash: %s", e)
            return False

    def get_hash(self, key: str) -> Optional[Dict[str, str]]:
        """Get hash value."""
        if self.redis_client is None:
            return None
        try:
            return self.redis_client.hgetall(key)
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error getting hash: %s", e)
            return None

    def increment_counter(self, key: str, amount: int = 1, expire_seconds: Optional[int] = None) -> Optional[int]:
        """Increment counter."""
        if self.redis_client is None:
            return None
        try:
            value = self.redis_client.incr(key, amount)
            if expire_seconds:
                self.redis_client.expire(key, expire_seconds)
            return value
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error incrementing counter: %s", e)
            return None

    def get_counter(self, key: str) -> Optional[int]:
        """Get counter value."""
        if self.redis_client is None:
            return None
        try:
            value = self.redis_client.get(key)
            return int(value) if value else 0
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error getting counter: %s", e)
            return None


# Repository instances
transaction_repo = TransactionRepository()
fraud_score_repo = FraudScoreRepository()
alert_repo = AlertRepository()
analytics_repo = AnalyticsRepository()
redis_repo = RedisRepository()
