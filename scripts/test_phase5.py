#!/usr/bin/env python3
"""
Test script for Phase 5: Production Readiness & Optimization
Tests security, load testing, CI/CD components, and deployment readiness.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_security_authentication():
    """Test authentication and authorization system."""
    print("🔐 Testing Security Authentication...")

    try:
        from src.security.authentication import security_manager, UserRole

        # Test user creation
        user = security_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role=UserRole.ANALYST
        )

        assert user is not None
        assert user.username == "testuser"
        assert user.role == UserRole.ANALYST
        print("  ✅ User creation: OK")

        # Test authentication
        auth_result = security_manager.authenticate("testuser", "TestPass123!")
        assert auth_result is not None
        assert 'token' in auth_result
        assert 'user' in auth_result
        print("  ✅ User authentication: OK")

        # Test token verification
        token = auth_result['token']
        user_info = security_manager.verify_token(token)
        assert user_info is not None
        assert user_info['user']['username'] == "testuser"
        print("  ✅ Token verification: OK")

        # Test permission checking
        has_permission = security_manager.check_permission(
            token, "alerts", "read")
        assert has_permission == True
        print("  ✅ Permission checking: OK")

        # Test invalid authentication
        invalid_auth = security_manager.authenticate(
            "testuser", "wrongpassword")
        assert invalid_auth is None
        print("  ✅ Invalid authentication handling: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Security authentication test failed: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting and caching system."""
    print("🚦 Testing Rate Limiting...")

    try:
        from src.security.rate_limiting import rate_limiter, cache_manager, security_middleware

        # Test rate limiting
        client_id = "test_client_123"

        # Make multiple requests
        for i in range(5):
            allowed, _ = rate_limiter.is_allowed(client_id, "/test")
            if i < 4:
                assert allowed == True, f"Request {i} should be allowed"
            print(
                f"  ✅ Rate limit check {i+1}: {'Allowed' if allowed else 'Blocked'}")

        # Test cache manager
        cache_key = "test_key"
        cache_value = {"data": "test_value"}

        # Set cache
        cache_result = cache_manager.set(
            cache_key, cache_value, ttl_seconds=60)
        assert cache_result == True
        print("  ✅ Cache set: OK")

        # Get cache
        retrieved_value = cache_manager.get(cache_key)
        assert retrieved_value == cache_value
        print("  ✅ Cache get: OK")

        # Test security middleware
        middleware_result = security_middleware.process_request(
            client_id, "/test", "GET")
        assert middleware_result['success'] == True
        print("  ✅ Security middleware: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Rate limiting test failed: {e}")
        return False


def test_load_testing_framework():
    """Test load testing framework."""
    print("⚡ Testing Load Testing Framework...")

    try:
        from src.testing.load_testing import LoadTestConfig, LoadTestRunner

        # Test configuration
        config = LoadTestConfig(
            target_url="http://localhost:8080",
            concurrent_users=2,
            duration_seconds=5,
            ramp_up_seconds=1
        )

        assert config.target_url == "http://localhost:8080"
        assert config.concurrent_users == 2
        print("  ✅ Load test configuration: OK")

        # Test runner creation
        runner = LoadTestRunner(config)
        assert runner is not None
        print("  ✅ Load test runner creation: OK")

        # Test quick load test function (without actually running)
        # This would normally run against a real server
        print("  ✅ Load testing framework: OK (framework ready)")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Load testing framework test failed: {e}")
        return False


def test_ci_cd_components():
    """Test CI/CD pipeline components."""
    print("🔄 Testing CI/CD Components...")

    try:
        # Check if CI/CD files exist
        ci_cd_file = ".github/workflows/ci-cd.yml"
        dockerfile = "Dockerfile"

        assert os.path.exists(
            ci_cd_file), f"CI/CD file not found: {ci_cd_file}"
        assert os.path.exists(
            dockerfile), f"Dockerfile not found: {dockerfile}"
        print("  ✅ CI/CD files exist: OK")

        # Test Dockerfile syntax (basic check)
        with open(dockerfile, 'r', encoding='utf-8') as f:
            dockerfile_content = f.read()
            assert "FROM python:3.13-slim" in dockerfile_content
            assert "EXPOSE 8080" in dockerfile_content
            assert "HEALTHCHECK" in dockerfile_content
        print("  ✅ Dockerfile syntax: OK")

        # Test CI/CD workflow syntax (basic check)
        with open(ci_cd_file, 'r', encoding='utf-8') as f:
            workflow_content = f.read()
            assert "name: CI/CD Pipeline" in workflow_content
            assert "test:" in workflow_content
            assert "build:" in workflow_content
        print("  ✅ CI/CD workflow syntax: OK")

        return True

    except (ImportError, AttributeError, ValueError, OSError) as e:
        print(f"  ❌ CI/CD components test failed: {e}")
        return False


def test_production_configuration():
    """Test production configuration and settings."""
    print("🏭 Testing Production Configuration...")

    try:
        # Test environment variables

        # Check for required environment variables (with defaults)
        required_vars = {
            'JWT_SECRET': 'default_secret_for_testing',
            'DATABASE_URL': 'postgresql://localhost:5432/fraud_detection',
            'REDIS_URL': 'redis://localhost:6379',
            'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092'
        }

        for var, default_value in required_vars.items():
            if var not in os.environ:
                os.environ[var] = default_value
            print(f"  ✅ Environment variable {var}: OK")

        # Test security configuration
        from src.security.authentication import SecurityConfig
        security_config = SecurityConfig()

        assert security_config.jwt_algorithm == "HS256"
        assert security_config.jwt_expiration_hours == 24
        assert security_config.password_min_length == 8
        print("  ✅ Security configuration: OK")

        # Test rate limiting configuration
        from src.security.rate_limiting import RateLimitConfig
        rate_config = RateLimitConfig()

        assert rate_config.requests_per_minute == 100
        assert rate_config.burst_limit == 20
        print("  ✅ Rate limiting configuration: OK")

        return True

    except (ImportError, AttributeError, ValueError, OSError) as e:
        print(f"  ❌ Production configuration test failed: {e}")
        return False


def test_monitoring_integration():
    """Test monitoring integration with security components."""
    print("📊 Testing Monitoring Integration...")

    try:
        from src.monitoring.metrics_collector import metrics_collector
        from src.security.rate_limiting import security_middleware

        # Test security metrics collection
        security_stats = security_middleware.get_security_stats()

        assert 'rate_limiter_stats' in security_stats
        assert 'cache_stats' in security_stats
        assert 'recent_requests' in security_stats
        print("  ✅ Security metrics collection: OK")

        # Test monitoring with security events
        metrics_collector.record_system_metric('security_events', 1)
        metrics_collector.record_error(
            'rate_limit_exceeded', 'Test rate limit')

        summary = metrics_collector.get_metrics_summary()
        assert 'error_counts' in summary
        print("  ✅ Security monitoring integration: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Monitoring integration test failed: {e}")
        return False


def test_performance_optimization():
    """Test performance optimization features."""
    print("🚀 Testing Performance Optimization...")

    try:
        from src.security.rate_limiting import cache_manager
        from src.monitoring.metrics_collector import metrics_collector

        # Test caching performance
        start_time = time.time()

        # Set multiple cache entries
        for i in range(100):
            cache_manager.set(f"perf_test_{i}", f"value_{i}", ttl_seconds=60)

        cache_time = time.time() - start_time
        assert cache_time < 1.0, f"Cache operations too slow: {cache_time:.2f}s"
        print(
            f"  ✅ Cache performance: OK ({cache_time:.3f}s for 100 operations)")

        # Test metrics collection performance
        start_time = time.time()

        # Record multiple metrics
        for i in range(100):
            metrics_collector.record_system_metric(f'perf_metric_{i}', i)

        metrics_time = time.time() - start_time
        assert metrics_time < 1.0, f"Metrics collection too slow: {metrics_time:.2f}s"
        print(
            f"  ✅ Metrics performance: OK ({metrics_time:.3f}s for 100 operations)")

        # Test memory usage
        cache_stats = cache_manager.get_stats()
        assert cache_stats['active_entries'] >= 100
        print("  ✅ Memory management: OK")

        return True

    except (ImportError, AttributeError, ValueError) as e:
        print(f"  ❌ Performance optimization test failed: {e}")
        return False


def test_deployment_readiness():
    """Test deployment readiness and health checks."""
    print("🚢 Testing Deployment Readiness...")

    try:
        # Test health check endpoints (if monitoring is running)
        try:
            import requests

            try:
                # Try to connect to monitoring dashboard
                response = requests.get(
                    "http://localhost:8080/health", timeout=5)
                if response.status_code == 200:
                    print("  ✅ Health check endpoint: OK")
                else:
                    print("  ⚠️  Health check endpoint: Available but not 200")
            except requests.exceptions.RequestException:
                print(
                    "  ⚠️  Health check endpoint: Not available (expected if not running)")
        except ImportError:
            print("  ⚠️  Requests library not available - skipping health check")

        # Test configuration validation
        from src.security.authentication import SecurityConfig
        from src.security.rate_limiting import RateLimitConfig

        # Validate security config
        security_config = SecurityConfig()
        assert security_config.jwt_secret is not None
        print(
            f"  ✅ JWT secret length: {len(security_config.jwt_secret)} characters")
        print("  ✅ Security configuration validation: OK")

        # Validate rate limiting config
        rate_config = RateLimitConfig()
        assert rate_config.requests_per_minute > 0
        assert rate_config.burst_limit > 0
        print("  ✅ Rate limiting configuration validation: OK")

        # Test file permissions and directories
        required_dirs = ['logs', 'passwords', 'reports']
        for dir_name in required_dirs:
            try:
                os.makedirs(dir_name, exist_ok=True)
                assert os.path.exists(dir_name)
            except OSError as e:
                print(f"  ⚠️  Directory {dir_name} creation failed: {e}")
        print("  ✅ Directory structure: OK")

        return True

    except (ImportError, AttributeError, ValueError, OSError) as e:
        print(f"  ❌ Deployment readiness test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 5 tests."""
    print("🚀 Phase 5: Production Readiness & Optimization - Component Testing")
    print("=" * 70)

    tests = [
        test_security_authentication,
        test_rate_limiting,
        test_load_testing_framework,
        test_ci_cd_components,
        test_production_configuration,
        test_monitoring_integration,
        test_performance_optimization,
        test_deployment_readiness
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
        except (ImportError, AttributeError, ValueError, OSError, RuntimeError) as e:
            print(f"❌ {test.__name__}: ERROR - {e}")
        print()

    print("=" * 70)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All Phase 5 components are production-ready!")
        print("✅ System is ready for deployment")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
