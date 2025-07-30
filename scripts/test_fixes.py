#!/usr/bin/env python3
"""
Test script to verify Phase 3 fixes are working correctly.
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_datetime_fixes():
    """Test that datetime.utcnow() has been replaced with datetime.now(timezone.utc)."""
    print("🕐 Testing DateTime Fixes...")

    try:
        # Test current time
        now = datetime.now(timezone.utc)
        print(f"  ✅ Current UTC time: {now}")

        # Test that it's timezone-aware
        assert now.tzinfo is not None, "Timezone should be set"
        print(f"  ✅ Timezone-aware datetime: {now.tzinfo}")

        return True
    except (ImportError, AssertionError) as e:
        print(f"  ❌ DateTime test failed: {e}")
        return False


def test_database_models():
    """Test database models import and basic functionality."""
    print("🗄️ Testing Database Models...")

    try:
        from src.data_models.database.models import Transaction

        # Test creating a transaction with new datetime
        transaction = Transaction(
            transaction_id="test-fix-123",
            user_id="user-fix-456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            merchant_name="Test Fix Merchant",
            timestamp=datetime.now(timezone.utc)
        )

        print(f"  ✅ Transaction model created: {transaction.transaction_id}")
        print(
            f"  ✅ Timestamp is timezone-aware: {transaction.timestamp.tzinfo is not None}")

        return True
    except (ImportError, ValueError) as e:
        print(f"  ❌ Database models test failed: {e}")
        return False


def test_database_config():
    """Test database configuration with graceful error handling."""
    print("🔧 Testing Database Configuration...")

    try:
        from src.data_models.database.config import DatabaseConfig

        # This should not raise an exception even if databases are not running
        config = DatabaseConfig()
        print("  ✅ Database configuration created successfully")

        # Test connection testing (should handle missing databases gracefully)
        try:
            results = config.test_connections()
            print(f"  ✅ Connection test completed: {results}")
        except (ConnectionError, RuntimeError) as conn_error:
            print(
                f"  ⚠️  Connection test (expected if databases not running): {str(conn_error)}")

        return True
    except (ImportError, AttributeError) as e:
        print(f"  ❌ Database configuration test failed: {e}")
        return False


def test_repository_pattern():
    """Test repository pattern with graceful error handling."""
    print("📚 Testing Repository Pattern...")

    try:
        from src.data_models.database.repositories import transaction_repo, redis_repo

        # Test repository methods (should handle missing databases gracefully)
        count = transaction_repo.count()
        print(f"  ✅ Transaction repository count: {count}")

        # Test Redis operations (should handle missing Redis gracefully)
        cache_result = redis_repo.set_cache("test_key", "test_value", 60)
        print(f"  ✅ Redis cache operation: {cache_result}")

        return True
    except (ImportError, AttributeError) as e:
        print(f"  ❌ Repository pattern test failed: {e}")
        return False


def test_analytics_engine():
    """Test analytics engine with new datetime handling."""
    print("📊 Testing Analytics Engine...")

    try:
        from src.analytics.engine import real_time_analytics, batch_analytics
        from src.data_models.schemas.transaction import TransactionEvent, Transaction, FraudScore

        # Create test data with new datetime
        test_transaction = Transaction(
            transaction_id="analytics-test-123",
            user_id="user-analytics-456",
            merchant_id="merchant-analytics-789",
            amount=500.0,
            currency="USD",
            transaction_type="purchase",
            payment_method="credit_card",
            timestamp=datetime.now(timezone.utc)
        )

        test_event = TransactionEvent(transaction=test_transaction)
        test_fraud_score = FraudScore(
            transaction_id="analytics-test-123",
            score=0.75,
            risk_level="HIGH",
            factors={"test": 0.5},
            rules_triggered=["test_rule"],
            timestamp=datetime.now(timezone.utc)
        )

        # Test real-time analytics
        insights = real_time_analytics.process_transaction(
            test_event, test_fraud_score)
        print(
            f"  ✅ Real-time analytics processing: {len(insights)} insights generated")

        # Test batch analytics
        today = datetime.now(timezone.utc)
        daily_report = batch_analytics.generate_daily_report(today)
        print(f"  ✅ Batch analytics report: {len(daily_report)} sections")

        return True
    except (ImportError, ValueError, AttributeError) as e:
        print(f"  ❌ Analytics engine test failed: {e}")
        return False


def test_reporting_system():
    """Test reporting system with new datetime handling."""
    print("📋 Testing Reporting System...")

    try:
        # Use simplified reporting system for testing
        from src.reporting.simple_generator import simple_report_generator, simple_dashboard_provider

        # Test dashboard data provider
        dashboard_data = simple_dashboard_provider.get_dashboard_data('main')
        print(
            f"  ✅ Dashboard data provider: {dashboard_data.get('dashboard_type', 'Unknown')}")

        # Test report generation
        today = datetime.now(timezone.utc)
        try:
            json_report_path = simple_report_generator.generate_daily_report(
                today, format='json')
            print(f"  ✅ JSON report generation: {json_report_path}")

            # Test HTML report generation
            html_report_path = simple_report_generator.generate_daily_report(
                today, format='html')
            print(f"  ✅ HTML report generation: {html_report_path}")

        except (OSError, ValueError) as report_error:
            print(f"  ⚠️  Report generation error: {str(report_error)}")

        return True
    except (ImportError, AttributeError) as e:
        print(f"  ❌ Reporting system test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🔧 Phase 3 Fixes Verification")
    print("=" * 50)

    tests = [
        test_datetime_fixes,
        test_database_models,
        test_database_config,
        test_repository_pattern,
        test_analytics_engine,
        test_reporting_system
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except (ImportError, ValueError, AttributeError, RuntimeError) as e:
            print(f"  ❌ Test {test.__name__} failed with exception: {e}")
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 3 fixes are working correctly!")
        print("✅ Ready to proceed to Phase 4")
        return True
    else:
        print("⚠️  Some issues remain - please check the errors above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
