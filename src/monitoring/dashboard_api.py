#!/usr/bin/env python3
"""
Dashboard API for real-time monitoring and visualization.
Provides endpoints for metrics, alerts, and system health data.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Optional
from datetime import datetime, timezone
import logging

from src.monitoring.metrics_collector import metrics_collector
from src.monitoring.alert_manager import alert_manager, AlertSeverity, AlertType

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Fraud Detection Dashboard API",
    description="Real-time monitoring and visualization API for fraud detection system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Dashboard home page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fraud Detection Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }
            .status-healthy { color: green; }
            .status-warning { color: orange; }
            .status-critical { color: red; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 Fraud Detection System Dashboard</h1>
            <p>Real-time monitoring and alerting system</p>
        </div>
        
        <div class="section">
            <h2>Quick Links</h2>
            <ul>
                <li><a href="/metrics">📊 System Metrics</a></li>
                <li><a href="/alerts">🚨 Active Alerts</a></li>
                <li><a href="/health">💚 System Health</a></li>
                <li><a href="/dashboard">📈 Real-time Dashboard</a></li>
                <li><a href="/docs">📖 API Documentation</a></li>
            </ul>
        </div>
        
        <div class="section">
            <h2>System Status</h2>
            <div id="status">Loading...</div>
        </div>
        
        <script>
            // Simple status check
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const statusClass = 'status-' + data.status;
                    statusDiv.innerHTML = `<span class="${statusClass}">● ${data.status.toUpperCase()}</span> - Last updated: ${data.last_updated}`;
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = '<span class="status-critical">● ERROR</span> - Unable to connect';
                });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """System health check endpoint."""
    try:
        health_status = metrics_collector.get_health_status()
        return health_status
    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Health check failed") from e


@app.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics."""
    try:
        metrics_summary = metrics_collector.get_metrics_summary()
        return metrics_summary
    except Exception as e:
        logger.error("Failed to get metrics: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve metrics") from e


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format."""
    try:
        prometheus_metrics = metrics_collector.export_metrics(
            format='prometheus')
        return prometheus_metrics
    except Exception as e:
        logger.error("Failed to export Prometheus metrics: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to export metrics") from e


@app.get("/alerts")
async def get_alerts(
    severity: Optional[str] = Query(
        None, description="Filter by alert severity"),
    alert_type: Optional[str] = Query(
        None, description="Filter by alert type"),
    acknowledged: Optional[bool] = Query(
        None, description="Filter by acknowledgment status"),
    resolved: Optional[bool] = Query(
        None, description="Filter by resolution status"),
    limit: int = Query(100, description="Maximum number of alerts to return")
):
    """Get alerts with optional filtering."""
    try:
        # Build filters
        filters = {}
        if severity:
            try:
                filters['severity'] = AlertSeverity(severity)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail=f"Invalid severity: {severity}") from exc

        if alert_type:
            try:
                filters['type'] = AlertType(alert_type)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail=f"Invalid alert type: {alert_type}") from exc

        if acknowledged is not None:
            filters['acknowledged'] = acknowledged

        if resolved is not None:
            filters['resolved'] = resolved

        # Get alerts
        alerts = alert_manager.get_alerts(filters)

        # Apply limit
        if limit > 0:
            alerts = alerts[:limit]

        # Convert to serializable format
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': alert.id,
                'type': alert.type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'source': alert.source,
                'metadata': alert.metadata,
                'acknowledged': alert.acknowledged,
                'acknowledged_by': alert.acknowledged_by,
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'escalation_level': alert.escalation_level
            })

        return {
            'alerts': alert_data,
            'total_count': len(alert_data),
            'filters_applied': filters
        }

    except Exception as e:
        logger.error("Failed to get alerts: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve alerts") from e


@app.get("/alerts/summary")
async def get_alert_summary():
    """Get alert summary statistics."""
    try:
        summary = alert_manager.get_alert_summary()
        return summary
    except Exception as e:
        logger.error("Failed to get alert summary: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve alert summary") from e


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = Query(..., description="User acknowledging the alert")):
    """Acknowledge an alert."""
    try:
        success = alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        if success:
            return {"message": f"Alert {alert_id} acknowledged by {acknowledged_by}"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Alert {alert_id} not found")
    except Exception as e:
        logger.error("Failed to acknowledge alert %s: %s", alert_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to acknowledge alert") from e


@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert."""
    try:
        success = alert_manager.resolve_alert(alert_id)
        if success:
            return {"message": f"Alert {alert_id} resolved"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Alert {alert_id} not found")
    except Exception as e:
        logger.error("Failed to resolve alert %s: %s", alert_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to resolve alert") from e


@app.post("/alerts/test")
async def create_test_alert(
    alert_type: str = Query("system_error", description="Type of test alert"),
    severity: str = Query("medium", description="Severity of test alert")
):
    """Create a test alert for testing purposes."""
    try:
        # Validate parameters
        try:
            alert_type_enum = AlertType(alert_type)
            severity_enum = AlertSeverity(severity)
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid parameter: {e}") from e

        # Create test alert
        alert = alert_manager.create_alert(
            alert_type=alert_type_enum,
            severity=severity_enum,
            title="Test Alert",
            message="This is a test alert created for testing purposes.",
            source="dashboard_api",
            metadata={'test': True, 'created_by': 'dashboard_api'}
        )

        return {
            "message": "Test alert created successfully",
            "alert_id": alert.id,
            "alert_type": alert.type.value,
            "severity": alert.severity.value
        }

    except Exception as e:
        logger.error("Failed to create test alert: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to create test alert") from e


@app.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data for real-time visualization."""
    try:
        # Get all the data we need
        metrics = metrics_collector.get_metrics_summary()
        health_status = metrics_collector.get_health_status()
        alert_summary = alert_manager.get_alert_summary()

        # Get recent alerts
        recent_alerts = alert_manager.get_alerts({'resolved': False})
        recent_alerts_data = []
        for alert in recent_alerts[:10]:  # Last 10 alerts
            recent_alerts_data.append({
                'id': alert.id,
                'type': alert.type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'timestamp': alert.timestamp.isoformat(),
                'acknowledged': alert.acknowledged
            })

        # Calculate key performance indicators
        transaction_metrics = metrics.get('transaction_metrics', {})
        kpis = {
            'total_transactions': transaction_metrics.get('total_transactions', 0),
            'fraud_rate': transaction_metrics.get('fraud_rate', 0),
            'average_amount': transaction_metrics.get('average_amount', 0),
            'system_uptime': health_status.get('uptime', 0),
            'active_alerts': alert_summary.get('active_alerts', 0),
            'error_rate': health_status.get('error_rate', 0)
        }

        # Performance trends
        performance_metrics = metrics.get('performance_metrics', {})
        trends = {
            'avg_processing_time': 0,
            'transactions_per_minute': 0,
            'system_load': health_status.get('system_metrics', {}).get('cpu_usage', 0)
        }

        if performance_metrics:
            # Calculate average processing time across all operations
            total_operations = 0
            total_time = 0
            for operation_data in performance_metrics.values():
                total_operations += operation_data.get('total_operations', 0)
                total_time += operation_data.get('avg_duration', 0) * \
                    operation_data.get('total_operations', 0)

            if total_operations > 0:
                trends['avg_processing_time'] = total_time / total_operations

        # Calculate transactions per minute (simplified)
        if transaction_metrics.get('total_transactions', 0) > 0:
            trends['transactions_per_minute'] = transaction_metrics['total_transactions'] / \
                max(1, metrics.get('uptime', 1) / 60)

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'kpis': kpis,
            'trends': trends,
            'system_health': health_status,
            'alert_summary': alert_summary,
            'recent_alerts': recent_alerts_data,
            'performance_metrics': performance_metrics
        }

    except Exception as e:
        logger.error("Failed to get dashboard data: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve dashboard data") from e


@app.get("/dashboard/stream")
async def stream_dashboard_data():
    """Stream real-time dashboard data (Server-Sent Events)."""
    # This would implement Server-Sent Events for real-time updates
    # For now, return a message indicating this endpoint
    return {
        "message": "Real-time streaming endpoint - implement Server-Sent Events for live updates",
        "endpoint": "/dashboard/stream",
        "format": "text/event-stream"
    }


@app.get("/system/info")
async def get_system_info():
    """Get system information and configuration."""
    try:
        return {
            'system_name': 'Fraud Detection System',
            'version': '1.0.0',
            'environment': 'development',
            'uptime': metrics_collector.get_metrics_summary().get('uptime', 0),
            'components': {
                'metrics_collector': 'active',
                'alert_manager': 'active',
                'dashboard_api': 'active'
            },
            'capabilities': [
                'real-time transaction monitoring',
                'fraud detection and scoring',
                'alert management and escalation',
                'performance metrics collection',
                'system health monitoring'
            ]
        }
    except Exception as e:
        logger.error("Failed to get system info: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve system information") from e


@app.exception_handler(Exception)
async def global_exception_handler(_, exc):
    """Global exception handler."""
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Health check endpoint for load balancers
@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes/load balancers."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes/load balancers."""
    try:
        # Check if core components are ready
        health_status = metrics_collector.get_health_status()
        return {
            "status": "ready" if health_status['status'] != 'critical' else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_status": health_status['status']
        }
    except (ValueError, RuntimeError, AttributeError, TypeError) as e:
        return {
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
