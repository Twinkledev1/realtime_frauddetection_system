"""
Transaction generator for simulating realistic financial transactions.
"""
import random

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Any
import uuid

from faker import Faker
from src.data_models.schemas.transaction import (
    Transaction, TransactionType, PaymentMethod, Location, TransactionEvent
)


class TransactionGenerator:
    """Generates realistic transaction data for fraud detection testing."""

    def __init__(self, seed: int = None):
        """Initialize the transaction generator."""
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        # Predefined data for realistic transactions
        self.merchants = self._load_merchants()
        self.users = self._load_users()
        self.locations = self._load_locations()
        self.device_ids = self._load_device_ids()
        self.ip_ranges = self._load_ip_ranges()

        # Transaction patterns
        self.transaction_patterns = {
            'normal': {
                'amount_range': (10.0, 500.0),
                'frequency_range': (1, 5),  # transactions per hour
                'location_consistency': 0.9,
                'time_pattern': 'regular'
            },
            'suspicious': {
                'amount_range': (1000.0, 10000.0),
                'frequency_range': (10, 50),
                'location_consistency': 0.3,
                'time_pattern': 'irregular'
            },
            'fraudulent': {
                'amount_range': (5000.0, 50000.0),
                'frequency_range': (50, 200),
                'location_consistency': 0.1,
                'time_pattern': 'burst'
            }
        }

    def _load_merchants(self) -> List[Dict[str, Any]]:
        """Load merchant data."""
        return [
            {'id': 'M001', 'name': 'Amazon',
                'category': 'retail', 'risk_level': 'low'},
            {'id': 'M002', 'name': 'Walmart',
                'category': 'retail', 'risk_level': 'low'},
            {'id': 'M003', 'name': 'Gas Station',
                'category': 'fuel', 'risk_level': 'medium'},
            {'id': 'M004', 'name': 'Online Casino',
                'category': 'gambling', 'risk_level': 'high'},
            {'id': 'M005', 'name': 'Cryptocurrency Exchange',
                'category': 'finance', 'risk_level': 'high'},
            {'id': 'M006', 'name': 'Grocery Store',
                'category': 'retail', 'risk_level': 'low'},
            {'id': 'M007', 'name': 'Restaurant',
                'category': 'food', 'risk_level': 'low'},
            {'id': 'M008', 'name': 'Travel Agency',
                'category': 'travel', 'risk_level': 'medium'},
            {'id': 'M009', 'name': 'Electronics Store',
                'category': 'retail', 'risk_level': 'medium'},
            {'id': 'M010', 'name': 'Suspicious Vendor',
                'category': 'unknown', 'risk_level': 'high'},
        ]

    def _load_users(self) -> List[Dict[str, Any]]:
        """Load user data."""
        return [
            {'id': 'U001', 'name': 'John Smith',
                'risk_profile': 'low', 'location': 'US'},
            {'id': 'U002', 'name': 'Jane Doe',
                'risk_profile': 'low', 'location': 'US'},
            {'id': 'U003', 'name': 'Bob Wilson',
                'risk_profile': 'medium', 'location': 'CA'},
            {'id': 'U004', 'name': 'Alice Brown',
                'risk_profile': 'high', 'location': 'UK'},
            {'id': 'U005', 'name': 'Charlie Davis',
                'risk_profile': 'fraudulent', 'location': 'RU'},
            {'id': 'U006', 'name': 'Diana Miller',
                'risk_profile': 'low', 'location': 'US'},
            {'id': 'U007', 'name': 'Edward Garcia',
                'risk_profile': 'medium', 'location': 'MX'},
            {'id': 'U008', 'name': 'Fiona Taylor',
                'risk_profile': 'high', 'location': 'BR'},
            {'id': 'U009', 'name': 'George Anderson',
                'risk_profile': 'fraudulent', 'location': 'NG'},
            {'id': 'U010', 'name': 'Helen Martinez',
                'risk_profile': 'low', 'location': 'ES'},
        ]

    def _load_locations(self) -> List[Dict[str, Any]]:
        """Load location data."""
        return [
            {'country': 'US', 'city': 'New York', 'lat': 40.7128, 'lng': -74.0060},
            {'country': 'US', 'city': 'Los Angeles',
                'lat': 34.0522, 'lng': -118.2437},
            {'country': 'US', 'city': 'Chicago', 'lat': 41.8781, 'lng': -87.6298},
            {'country': 'CA', 'city': 'Toronto', 'lat': 43.6532, 'lng': -79.3832},
            {'country': 'UK', 'city': 'London', 'lat': 51.5074, 'lng': -0.1278},
            {'country': 'RU', 'city': 'Moscow', 'lat': 55.7558, 'lng': 37.6176},
            {'country': 'MX', 'city': 'Mexico City',
                'lat': 19.4326, 'lng': -99.1332},
            {'country': 'BR', 'city': 'São Paulo',
                'lat': -23.5505, 'lng': -46.6333},
            {'country': 'NG', 'city': 'Lagos', 'lat': 6.5244, 'lng': 3.3792},
            {'country': 'ES', 'city': 'Madrid', 'lat': 40.4168, 'lng': -3.7038},
        ]

    def _load_device_ids(self) -> List[str]:
        """Load device ID data."""
        return [
            f"device_{uuid.uuid4().hex[:8]}" for _ in range(20)
        ]

    def _load_ip_ranges(self) -> List[str]:
        """Load IP range data."""
        return [
            "192.168.1.1", "10.0.0.1", "172.16.0.1",
            "203.0.113.1", "198.51.100.1", "203.0.113.2"
        ]

    def generate_transaction(self, pattern: str = 'normal', user_id: str = None) -> TransactionEvent:
        """Generate a single transaction event."""
        pattern_config = self.transaction_patterns[pattern]

        # Select user
        if user_id is None:
            user = random.choice(self.users)
            user_id = user['id']
        else:
            user = next(
                (u for u in self.users if u['id'] == user_id), self.users[0])

        # Select merchant based on user risk profile
        if user['risk_profile'] == 'fraudulent':
            merchant = random.choice(
                [m for m in self.merchants if m['risk_level'] == 'high'])
        elif user['risk_profile'] == 'high':
            merchant = random.choice(
                [m for m in self.merchants if m['risk_level'] in ['medium', 'high']])
        else:
            merchant = random.choice(self.merchants)

        # Generate amount based on pattern
        min_amount, max_amount = pattern_config['amount_range']
        amount = Decimal(str(random.uniform(min_amount, max_amount))).quantize(
            Decimal('0.01'))

        # Generate location
        location = self._generate_location(
            user, pattern_config['location_consistency'])

        # Generate timestamp
        timestamp = self._generate_timestamp(pattern_config['time_pattern'])

        # Generate transaction
        transaction = Transaction(
            user_id=user_id,
            merchant_id=merchant['id'],
            amount=amount,
            transaction_type=random.choice(list(TransactionType)),
            payment_method=random.choice(list(PaymentMethod)),
            timestamp=timestamp,
            location=location,
            ip_address=random.choice(self.ip_ranges),
            device_id=random.choice(self.device_ids),
            metadata={
                'merchant_category': merchant['category'],
                'user_risk_profile': user['risk_profile'],
                'pattern_type': pattern,
                'generated_by': 'transaction_simulator'
            }
        )

        return TransactionEvent(transaction=transaction)

    def _generate_location(self, user: Dict[str, Any], consistency: float) -> Location:
        """Generate location based on user and consistency."""
        if random.random() < consistency:
            # Use user's typical location
            user_location = next(
                (loc for loc in self.locations if loc['country'] == user['location']), self.locations[0])
            return Location(
                latitude=user_location['lat'] + random.uniform(-0.1, 0.1),
                longitude=user_location['lng'] + random.uniform(-0.1, 0.1),
                city=user_location['city'],
                country=user_location['country']
            )
        else:
            # Use random location (suspicious behavior)
            random_location = random.choice(self.locations)
            return Location(
                latitude=random_location['lat'] + random.uniform(-0.1, 0.1),
                longitude=random_location['lng'] + random.uniform(-0.1, 0.1),
                city=random_location['city'],
                country=random_location['country']
            )

    def _generate_timestamp(self, pattern: str) -> datetime:
        """Generate timestamp based on pattern."""
        now = datetime.now(timezone.utc)

        if pattern == 'regular':
            # Regular business hours
            hour = random.randint(9, 17)
            minute = random.randint(0, 59)
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif pattern == 'irregular':
            # Random hours
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif pattern == 'burst':
            # Recent timestamp (high frequency)
            return now - timedelta(minutes=random.randint(0, 5))
        else:
            return now

    def generate_batch(self, count: int, pattern: str = 'normal') -> List[TransactionEvent]:
        """Generate a batch of transactions."""
        events = []
        for _ in range(count):
            events.append(self.generate_transaction(pattern))
        return events

    def generate_fraudulent_batch(self, count: int) -> List[TransactionEvent]:
        """Generate a batch of fraudulent transactions."""
        return self.generate_batch(count, 'fraudulent')

    def generate_suspicious_batch(self, count: int) -> List[TransactionEvent]:
        """Generate a batch of suspicious transactions."""
        return self.generate_batch(count, 'suspicious')
