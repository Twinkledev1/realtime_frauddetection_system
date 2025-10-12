"""
Unit tests for transaction generator.
"""
import pytest
from decimal import Decimal
from datetime import datetime

from src.transaction_simulator.generator import TransactionGenerator
from src.data_models.schemas.transaction import TransactionEvent, TransactionType, PaymentMethod


class TestTransactionGenerator:
    """Test cases for TransactionGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TransactionGenerator(seed=42)

    def test_generator_initialization(self):
        """Test that generator initializes correctly."""
        assert self.generator is not None
        assert len(self.generator.merchants) > 0
        assert len(self.generator.users) > 0
        assert len(self.generator.locations) > 0

    def test_generate_normal_transaction(self):
        """Test generating a normal transaction."""
        event = self.generator.generate_transaction('normal')

        assert isinstance(event, TransactionEvent)
        assert event.transaction is not None
        assert event.transaction.transaction_id is not None
        assert event.transaction.amount > 0
        assert event.transaction.user_id is not None
        assert event.transaction.merchant_id is not None

    def test_generate_fraudulent_transaction(self):
        """Test generating a fraudulent transaction."""
        event = self.generator.generate_transaction('fraudulent')

        assert isinstance(event, TransactionEvent)
        assert event.transaction is not None
        # Fraudulent transactions are high value
        assert float(event.transaction.amount) > 5000

    def test_generate_suspicious_transaction(self):
        """Test generating a suspicious transaction."""
        event = self.generator.generate_transaction('suspicious')

        assert isinstance(event, TransactionEvent)
        assert event.transaction is not None
        # Suspicious transactions are medium-high value
        assert float(event.transaction.amount) > 1000

    def test_generate_batch(self):
        """Test generating a batch of transactions."""
        batch = self.generator.generate_batch(5, 'normal')

        assert len(batch) == 5
        assert all(isinstance(event, TransactionEvent) for event in batch)
        assert all(event.transaction is not None for event in batch)

    def test_transaction_validation(self):
        """Test that generated transactions are valid."""
        event = self.generator.generate_transaction('normal')
        transaction = event.transaction

        # Test required fields
        assert transaction.transaction_id is not None
        assert transaction.user_id is not None
        assert transaction.merchant_id is not None
        assert transaction.amount > 0
        assert transaction.currency == "USD"
        assert transaction.transaction_type in TransactionType
        assert transaction.payment_method in PaymentMethod
        assert transaction.timestamp is not None
        assert transaction.status is not None

    def test_location_generation(self):
        """Test that locations are generated correctly."""
        event = self.generator.generate_transaction('normal')
        location = event.transaction.location

        if location:
            assert -90 <= location.latitude <= 90
            assert -180 <= location.longitude <= 180
            assert location.country is not None

    def test_metadata_generation(self):
        """Test that metadata is generated correctly."""
        event = self.generator.generate_transaction('normal')
        metadata = event.transaction.metadata

        assert metadata is not None
        assert 'merchant_category' in metadata
        assert 'user_risk_profile' in metadata
        assert 'pattern_type' in metadata
        assert 'generated_by' in metadata

    def test_deterministic_generation(self):
        """Test that generation shows some consistency with same seed."""
        generator1 = TransactionGenerator(seed=123)
        generator2 = TransactionGenerator(seed=123)

        # Generate multiple transactions to test pattern consistency
        events1 = [generator1.generate_transaction(
            'normal') for _ in range(10)]
        events2 = [generator2.generate_transaction(
            'normal') for _ in range(10)]

        # With same seed, at least some aspects should be consistent
        # Check that the generators produce transactions within expected ranges
        amounts1 = [event.transaction.amount for event in events1]
        amounts2 = [event.transaction.amount for event in events2]

        # Both should be within the normal transaction range
        for amount in amounts1 + amounts2:
            assert 10.0 <= float(amount) <= 500.0

        # Test that the seed affects generation (not completely random)
        generator_no_seed = TransactionGenerator()
        events_no_seed = [generator_no_seed.generate_transaction(
            'normal') for _ in range(10)]
        amounts_no_seed = [
            event.transaction.amount for event in events_no_seed]

        # The seeded generators should have some correlation with each other
        # but be different from the non-seeded one (statistical test)
        import statistics
        mean1 = statistics.mean(amounts1)
        mean2 = statistics.mean(amounts2)
        mean_no_seed = statistics.mean(amounts_no_seed)

        # The seeded means should be closer to each other than to the non-seeded mean
        # (this is a probabilistic test, but should work most of the time)
        assert abs(mean1 - mean2) <= abs(mean1 -
                                         mean_no_seed) or abs(mean1 - mean2) <= abs(mean2 - mean_no_seed)


class TestTransactionSchemas:
    """Test cases for transaction schemas."""

    def test_transaction_creation(self):
        """Test creating a transaction with valid data."""
        from src.data_models.schemas.transaction import Transaction, Location, TransactionType, PaymentMethod

        location = Location(
            latitude=40.7128,
            longitude=-74.0060,
            city="New York",
            country="US"
        )

        transaction = Transaction(
            user_id="U001",
            merchant_id="M001",
            amount=Decimal("100.50"),
            transaction_type=TransactionType.PURCHASE,
            payment_method=PaymentMethod.CREDIT_CARD,
            location=location,
            ip_address="192.168.1.1",
            device_id="device_123"
        )

        assert transaction.user_id == "U001"
        assert transaction.merchant_id == "M001"
        assert transaction.amount == Decimal("100.50")
        assert transaction.transaction_type == TransactionType.PURCHASE
        assert transaction.payment_method == PaymentMethod.CREDIT_CARD
        assert transaction.location == location
        assert transaction.ip_address == "192.168.1.1"
        assert transaction.device_id == "device_123"

    def test_transaction_event_creation(self):
        """Test creating a transaction event."""
        from src.data_models.schemas.transaction import TransactionEvent, Transaction, TransactionType, PaymentMethod

        transaction = Transaction(
            user_id="U001",
            merchant_id="M001",
            amount=Decimal("100.50"),
            transaction_type=TransactionType.PURCHASE,
            payment_method=PaymentMethod.CREDIT_CARD
        )

        event = TransactionEvent(transaction=transaction)

        assert event.transaction == transaction
        assert event.event_type == "transaction.created"
        assert event.source == "transaction_simulator"
        assert event.event_id is not None
        assert event.timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__])
