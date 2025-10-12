"""
Fraud detection rule engine for applying business rules to transactions.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

from src.data_models.schemas.transaction import Transaction, FraudScore

logger = logging.getLogger(__name__)


class FraudRule:
    """Base class for fraud detection rules."""

    def __init__(self, name: str, weight: float = 1.0):
        """Initialize a fraud rule.

        Args:
            name: Name of the rule
            weight: Weight of the rule in scoring (0.0 to 1.0)
        """
        self.name = name
        self.weight = weight

    def evaluate(self, transaction: Transaction, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate the rule against a transaction.

        Args:
            transaction: Transaction to evaluate
            context: Additional context (e.g., user history)

        Returns:
            Dict with rule evaluation results
        """
        raise NotImplementedError("Subclasses must implement evaluate method")


class HighAmountRule(FraudRule):
    """Rule for detecting high-value transactions."""

    def __init__(self, threshold: float = 10000.0):
        """Initialize high amount rule.

        Args:
            threshold: Amount threshold for flagging transactions
        """
        super().__init__("high_amount", weight=0.3)
        self.threshold = threshold

    def evaluate(self, transaction: Transaction, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate if transaction amount is suspiciously high."""
        amount = float(transaction.amount)
        is_high = amount > self.threshold

        return {
            'triggered': is_high,
            'score': 0.8 if is_high else 0.0,
            'details': {
                'amount': amount,
                'threshold': self.threshold,
                'exceeds_threshold': is_high
            }
        }


class HighFrequencyRule(FraudRule):
    """Rule for detecting high-frequency transactions."""

    def __init__(self, max_transactions: int = 10, time_window_minutes: int = 5):
        """Initialize high frequency rule.

        Args:
            max_transactions: Maximum transactions allowed in time window
            time_window_minutes: Time window in minutes
        """
        super().__init__("high_frequency", weight=0.25)
        self.max_transactions = max_transactions
        self.time_window_minutes = time_window_minutes

    def evaluate(self, transaction: Transaction, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate if user has too many transactions in recent time window."""
        if not context or 'user_transactions' not in context:
            return {
                'triggered': False,
                'score': 0.0,
                'details': {'reason': 'No user transaction history available'}
            }

        user_transactions = context['user_transactions']
        recent_transactions = [
            t for t in user_transactions
            if t.transaction_id != transaction.transaction_id and
            abs((t.timestamp - transaction.timestamp).total_seconds()
                ) <= self.time_window_minutes * 60
        ]

        is_high_frequency = len(recent_transactions) >= self.max_transactions

        return {
            'triggered': is_high_frequency,
            'score': 0.9 if is_high_frequency else 0.0,
            'details': {
                'recent_transactions': len(recent_transactions),
                'max_allowed': self.max_transactions,
                'time_window_minutes': self.time_window_minutes
            }
        }


class GeographicAnomalyRule(FraudRule):
    """Rule for detecting geographic anomalies."""

    def __init__(self, suspicious_countries: List[str] = None):
        """Initialize geographic anomaly rule.

        Args:
            suspicious_countries: List of countries considered suspicious
        """
        super().__init__("geographic_anomaly", weight=0.25)
        self.suspicious_countries = suspicious_countries or [
            'RU', 'NG', 'BR', 'MX']

    def evaluate(self, transaction: Transaction, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate if transaction location is suspicious."""
        if not transaction.location:
            return {
                'triggered': False,
                'score': 0.0,
                'details': {'reason': 'No location information available'}
            }

        country = transaction.location.country
        is_suspicious_country = country in self.suspicious_countries

        # Check for location inconsistency with user history
        location_inconsistent = False
        if context and 'user_locations' in context:
            user_locations = context['user_locations']
            if user_locations and country not in user_locations:
                location_inconsistent = True

        is_anomaly = is_suspicious_country or location_inconsistent

        return {
            'triggered': is_anomaly,
            'score': 0.7 if is_anomaly else 0.0,
            'details': {
                'country': country,
                'is_suspicious_country': is_suspicious_country,
                'location_inconsistent': location_inconsistent,
                'suspicious_countries': self.suspicious_countries
            }
        }


class SuspiciousMerchantRule(FraudRule):
    """Rule for detecting transactions with suspicious merchants."""

    def __init__(self, suspicious_categories: List[str] = None):
        """Initialize suspicious merchant rule.

        Args:
            suspicious_categories: List of merchant categories considered suspicious
        """
        super().__init__("suspicious_merchant", weight=0.2)
        self.suspicious_categories = suspicious_categories or [
            'gambling', 'unknown', 'cryptocurrency']

    def evaluate(self, transaction: Transaction, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Evaluate if merchant is suspicious."""
        merchant_category = transaction.metadata.get(
            'merchant_category', 'unknown')
        is_suspicious = merchant_category in self.suspicious_categories

        return {
            'triggered': is_suspicious,
            'score': 0.6 if is_suspicious else 0.0,
            'details': {
                'merchant_category': merchant_category,
                'is_suspicious': is_suspicious,
                'suspicious_categories': self.suspicious_categories
            }
        }


class FraudRuleEngine:
    """Engine for applying fraud detection rules to transactions."""

    def __init__(self):
        """Initialize the fraud rule engine."""
        self.rules = [
            HighAmountRule(),
            HighFrequencyRule(),
            GeographicAnomalyRule(),
            SuspiciousMerchantRule()
        ]

        # User transaction history (in production, this would be in a database)
        self.user_history = {}

        logger.info(
            "Initialized fraud rule engine with %d rules", len(self.rules))

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get context for a user (transaction history, locations, etc.)."""
        if user_id not in self.user_history:
            return {}

        user_data = self.user_history[user_id]

        return {
            'user_transactions': user_data.get('transactions', []),
            'user_locations': user_data.get('locations', set()),
            'user_risk_profile': user_data.get('risk_profile', 'low')
        }

    def update_user_history(self, transaction: Transaction):
        """Update user transaction history."""
        user_id = transaction.user_id

        if user_id not in self.user_history:
            self.user_history[user_id] = {
                'transactions': [],
                'locations': set(),
                'risk_profile': 'low'
            }

        # Add transaction to history
        self.user_history[user_id]['transactions'].append(transaction)

        # Update locations
        if transaction.location:
            self.user_history[user_id]['locations'].add(
                transaction.location.country)

        # Keep only recent transactions (last 24 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.user_history[user_id]['transactions'] = [
            t for t in self.user_history[user_id]['transactions']
            if t.timestamp > cutoff_time
        ]

    def evaluate_transaction(self, transaction: Transaction) -> FraudScore:
        """Evaluate a transaction using all fraud detection rules.

        Args:
            transaction: Transaction to evaluate

        Returns:
            FraudScore with calculated risk score and details
        """
        # Update user history
        self.update_user_history(transaction)

        # Get user context
        context = self.get_user_context(transaction.user_id)

        # Apply all rules
        rule_results = {}
        total_score = 0.0
        total_weight = 0.0
        triggered_rules = []

        for rule in self.rules:
            result = rule.evaluate(transaction, context)
            rule_results[rule.name] = result

            if result['triggered']:
                triggered_rules.append(rule.name)
                total_score += result['score'] * rule.weight
                total_weight += rule.weight

        # Calculate weighted average score
        final_score = total_score / total_weight if total_weight > 0 else 0.0

        # Determine risk level
        if final_score >= 0.8:
            risk_level = "CRITICAL"
        elif final_score >= 0.6:
            risk_level = "HIGH"
        elif final_score >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Create fraud score
        fraud_score = FraudScore(
            transaction_id=transaction.transaction_id,
            score=final_score,
            risk_level=risk_level,
            factors=rule_results,
            rules_triggered=triggered_rules
        )

        logger.info(
            "Transaction %s evaluated: score=%.3f, risk=%s, rules_triggered=%s",
            transaction.transaction_id, final_score, risk_level, triggered_rules
        )

        return fraud_score

    def get_rule_summary(self) -> Dict[str, Any]:
        """Get summary of all rules."""
        return {
            'total_rules': len(self.rules),
            'rules': [
                {
                    'name': rule.name,
                    'weight': rule.weight,
                    'description': rule.__class__.__doc__
                }
                for rule in self.rules
            ]
        }
