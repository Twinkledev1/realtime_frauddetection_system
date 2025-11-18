#!/usr/bin/env python3
"""
Test script for Phase 4: Monitoring & Visualization
Tests metrics collection, alert management, dashboard API, and integration.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_metrics_collector():
    """Test metrics collector functionality."""
    print("📊 Testing Metrics Collector...")

    try:
        from src.monitoring.metrics_collector import metrics_collector

        # Test transaction recording
        test_transaction = {
            'transaction_id': 'test_123',
            'amount': 150.00,
            'fraud_score': 0.75,
            'user_id': 'user_456'
        }

        metrics_collector.record_transaction(test_transaction)
        print("  ✅ Transaction recording: OK")

        # Test performance recording
        metrics_collector.record_performance('test_operation', 125.5, True)
        print("  ✅ Performance recording: OK")

        # Test error recording
        metrics_collector.record_error('test_error', 'Test error message')
        print("  ✅ Error recording: OK")

        # Test metrics summary
        summary = metrics_collector.get_metrics_summary()
        assert 'transaction_metrics' in summary
        assert 'system_health' in summary
        print("  ✅ Metrics summary: OK")

        # Test health status
        health = metrics_collector.get_health_status()
        assert 'status' in health
        print("  ✅ Health status: OK")

        # Test Prometheus export
        prometheus_metrics = metrics_collector.export_metrics(
            format='prometheus')
        assert 'fraud_detection_transactions_total' in prometheus_metrics
        print("  ✅ Prometheus export: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Metrics collector test failed: {e}")
        return False


def test_alert_manager():
    """Test alert manager functionality."""
    print("🚨 Testing Alert Manager...")

    try:
        from src.monitoring.alert_manager import alert_manager, AlertType, AlertSeverity

        # Test alert creation
        alert = alert_manager.create_alert(
            alert_type=AlertType.FRAUD_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Fraud Alert",
            message="This is a test fraud alert",
            source="test_script"
        )

        assert alert.id is not None
        assert alert.type == AlertType.FRAUD_DETECTED
        print("  ✅ Alert creation: OK")

        # Test alert retrieval
        alerts = alert_manager.get_alerts()
        assert len(alerts) > 0
        print("  ✅ Alert retrieval: OK")

        # Test alert filtering
        fraud_alerts = alert_manager.get_alerts(
            {'type': AlertType.FRAUD_DETECTED})
        assert len(fraud_alerts) > 0
        print("  ✅ Alert filtering: OK")

        # Test alert acknowledgment
        ack_result = alert_manager.acknowledge_alert(alert.id, "test_user")
        assert ack_result
        print("  ✅ Alert acknowledgment: OK")

        # Test alert resolution
        resolve_result = alert_manager.resolve_alert(alert.id)
        assert resolve_result
        print("  ✅ Alert resolution: OK")

        # Test alert summary
        summary = alert_manager.get_alert_summary()
        assert 'total_alerts' in summary
        assert 'active_alerts' in summary
        print("  ✅ Alert summary: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Alert manager test failed: {e}")
        return False


def test_monitoring_integration():
    """Test monitoring integration functionality."""
    print("🔗 Testing Monitoring Integration...")

    try:
        from src.monitoring.integration import (
            track_transaction,
            track_performance,
            track_error,
            create_fraud_alert,
            get_monitoring_status
        )

        # Test transaction tracking
        test_data = {
            'transaction_id': 'test_integration_123',
            'amount': 200.00,
            'fraud_score': 0.85,
            'user_id': 'user_789'
        }

        track_transaction(test_data)
        print("  ✅ Transaction tracking: OK")

        # Test performance tracking
        track_performance('integration_test', 150.0, True)
        print("  ✅ Performance tracking: OK")

        # Test error tracking
        track_error('integration_error', 'Test integration error')
        print("  ✅ Error tracking: OK")

        # Test fraud alert creation
        create_fraud_alert('test_tx_456', 0.92, 'high', {'test': True})
        print("  ✅ Fraud alert creation: OK")

        # Test monitoring status
        status = get_monitoring_status()
        assert 'enabled' in status
        assert status['enabled'] == True
        print("  ✅ Monitoring status: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Monitoring integration test failed: {e}")
        return False


def test_dashboard_api_components():
    """Test dashboard API components (without running the server)."""
    print("🌐 Testing Dashboard API Components...")

    try:
        # Test that we can import the app
        from src.monitoring.dashboard_api import app

        # Check that the app has the expected endpoints
        routes = [route.path for route in app.routes]
        expected_routes = ['/', '/health', '/metrics', '/alerts', '/dashboard']

        for route in expected_routes:
            assert route in routes, f"Expected route {route} not found"

        print("  ✅ API routes: OK")

        # Test that we can create the app without errors
        assert app.title == "Fraud Detection Dashboard API"
        print("  ✅ API app creation: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Dashboard API test failed: {e}")
        return False


def test_monitoring_service():
    """Test monitoring service functionality."""
    print("⚙️ Testing Monitoring Service...")

    try:
        from src.monitoring.main import MonitoringService, run_health_check

        # Test service creation
        service = MonitoringService()
        assert service.running == False
        print("  ✅ Service creation: OK")

        # Test health check function
        health_result = run_health_check()
        assert health_result
        print("  ✅ Health check: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Monitoring service test failed: {e}")
        return False


def test_end_to_end_monitoring():
    """Test end-to-end monitoring workflow."""
    print("🔄 Testing End-to-End Monitoring Workflow...")

    try:
        from src.monitoring.metrics_collector import metrics_collector
        from src.monitoring.alert_manager import alert_manager
        from src.monitoring.integration import track_transaction, create_fraud_alert

        # Simulate a complete monitoring workflow

        # 1. Record multiple transactions
        transactions = [
            {'transaction_id': 'tx_001', 'amount': 100.0,
                'fraud_score': 0.1, 'user_id': 'user_1'},
            {'transaction_id': 'tx_002', 'amount': 500.0,
                'fraud_score': 0.8, 'user_id': 'user_2'},
            {'transaction_id': 'tx_003', 'amount': 50.0,
                'fraud_score': 0.3, 'user_id': 'user_3'},
            {'transaction_id': 'tx_004', 'amount': 1000.0,
                'fraud_score': 0.95, 'user_id': 'user_4'},
        ]

        for tx in transactions:
            track_transaction(tx)

        print("  ✅ Transaction workflow: OK")

        # 2. Create fraud alerts for high-risk transactions
        high_risk_txs = [tx for tx in transactions if tx['fraud_score'] >= 0.8]
        for tx in high_risk_txs:
            create_fraud_alert(
                tx['transaction_id'],
                tx['fraud_score'],
                'high' if tx['fraud_score'] >= 0.9 else 'medium'
            )

        print("  ✅ Fraud alert workflow: OK")

        # 3. Check metrics summary
        metrics = metrics_collector.get_metrics_summary()
        assert metrics['transaction_metrics']['total_transactions'] >= 4
        assert metrics['transaction_metrics']['fraudulent_transactions'] >= 2
        print("  ✅ Metrics aggregation: OK")

        # 4. Check alert summary
        alert_summary = alert_manager.get_alert_summary()
        assert alert_summary['total_alerts'] >= len(high_risk_txs)
        print("  ✅ Alert aggregation: OK")

        # 5. Test system health
        health = metrics_collector.get_health_status()
        assert 'status' in health
        print("  ✅ System health monitoring: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ End-to-end monitoring test failed: {e}")
        return False


def test_performance_metrics():
    """Test performance metrics collection."""
    print("⚡ Testing Performance Metrics...")

    try:
        from src.monitoring.metrics_collector import metrics_collector

        # Record various performance metrics
        operations = [
            ('kafka_producer_send', 25.5),
            ('fraud_detection_evaluation', 150.2),
            ('database_query', 45.8),
            ('api_request', 12.3),
        ]

        for operation, duration in operations:
            metrics_collector.record_performance(operation, duration, True)

        # Test error performance
        metrics_collector.record_performance('failed_operation', 200.0, False)

        # Check performance metrics
        summary = metrics_collector.get_metrics_summary()
        performance_metrics = summary.get('performance_metrics', {})

        assert len(performance_metrics) >= len(operations)
        print("  ✅ Performance metrics collection: OK")

        # Test performance trends
        for operation in performance_metrics:
            assert 'avg_duration' in performance_metrics[operation]
            assert 'total_operations' in performance_metrics[operation]

        print("  ✅ Performance metrics analysis: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Performance metrics test failed: {e}")
        return False


def main():
    """Run all Phase 4 tests."""
    print("🚀 Phase 4: Monitoring & Visualization - Component Testing")
    print("=" * 60)

    tests = [
        test_metrics_collector,
        test_alert_manager,
        test_monitoring_integration,
        test_dashboard_api_components,
        test_monitoring_service,
        test_end_to_end_monitoring,
        test_performance_metrics
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__}: PASSED")
            else:
                print(f"❌ {test.__name__}: FAILED")
        except (ImportError, AttributeError, ValueError, RuntimeError) as e:
            print(f"❌ {test.__name__}: ERROR - {e}")
        print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 4 components are working correctly!")
        print("✅ Ready for production deployment")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
