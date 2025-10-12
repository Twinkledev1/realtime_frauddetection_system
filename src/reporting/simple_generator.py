#!/usr/bin/env python3
"""
Simplified report generator for testing purposes.
This version doesn't require WeasyPrint or external system libraries.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SimpleReportGenerator:
    """Simplified report generator for testing without external dependencies."""

    def __init__(self):
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

    def generate_daily_report(self, date: datetime, output_format: str = 'json') -> str:
        """Generate daily fraud detection report."""
        try:
            # Create simple report data
            report_data = {
                'report_type': 'daily_fraud_detection',
                'date': date.strftime('%Y-%m-%d'),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'summary': {
                    'total_transactions': 0,
                    'fraudulent_transactions': 0,
                    'suspicious_transactions': 0,
                    'total_amount': 0.0,
                    'average_fraud_score': 0.0
                },
                'metrics': {
                    'transactions_per_hour': 0,
                    'fraud_rate': 0.0,
                    'average_response_time': 0.0
                },
                'alerts': [],
                'top_merchants': [],
                'risk_distribution': {
                    'LOW': 0,
                    'MEDIUM': 0,
                    'HIGH': 0,
                    'CRITICAL': 0
                }
            }

            # Generate report based on format
            if output_format.lower() == 'json':
                return self._generate_json_report(report_data, 'daily', date)
            elif output_format.lower() == 'html':
                return self._generate_html_report(report_data, 'daily', date)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating daily report: %s", e)
            raise

    def generate_weekly_report(self, start_date: datetime, output_format: str = 'json') -> str:
        """Generate weekly fraud detection report."""
        try:
            # Create simple report data
            report_data = {
                'report_type': 'weekly_fraud_detection',
                'week_start': start_date.strftime('%Y-%m-%d'),
                'week_end': (start_date + timedelta(days=7)).strftime('%Y-%m-%d'),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'summary': {
                    'total_transactions': 0,
                    'fraudulent_transactions': 0,
                    'suspicious_transactions': 0,
                    'total_amount': 0.0,
                    'average_fraud_score': 0.0
                },
                'trends': {
                    'daily_transactions': [0] * 7,
                    'daily_fraud_rate': [0.0] * 7,
                    'daily_alerts': [0] * 7
                },
                'top_merchants': [],
                'risk_distribution': {
                    'LOW': 0,
                    'MEDIUM': 0,
                    'HIGH': 0,
                    'CRITICAL': 0
                }
            }

            # Generate report based on format
            if output_format.lower() == 'json':
                return self._generate_json_report(report_data, 'weekly', start_date)
            elif output_format.lower() == 'html':
                return self._generate_html_report(report_data, 'weekly', start_date)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating weekly report: %s", e)
            raise

    def _generate_json_report(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate JSON report."""
        try:
            # Add metadata
            data['report_metadata'] = {
                'report_type': report_type,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'date': date.strftime('%Y-%m-%d'),
                'version': '1.0'
            }

            # Save JSON file
            filename = f"{report_type}_report_{date.strftime('%Y%m%d')}.json"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info("JSON report generated: %s", filepath)
            return str(filepath)

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating JSON report: %s", e)
            raise

    def _generate_html_report(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate simple HTML report."""
        try:
            # Generate HTML content
            html_content = self._generate_html_content(data, report_type, date)

            # Save HTML file
            filename = f"{report_type}_report_{date.strftime('%Y%m%d')}.html"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info("HTML report generated: %s", filepath)
            return str(filepath)

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating HTML report: %s", e)
            raise

    def _generate_html_content(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate HTML content for reports."""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type.title()} Fraud Detection Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
        .footer {{ margin-top: 30px; padding: 10px; background-color: #f9f9f9; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report_type.title()} Fraud Detection Report</h1>
        <p>Date: {date.strftime('%Y-%m-%d')}</p>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="metric">
            <strong>Total Transactions:</strong> {data.get('summary', {}).get('total_transactions', 0)}
        </div>
        <div class="metric">
            <strong>Fraudulent:</strong> {data.get('summary', {}).get('fraudulent_transactions', 0)}
        </div>
        <div class="metric">
            <strong>Total Amount:</strong> ${data.get('summary', {}).get('total_amount', 0):,.2f}
        </div>
    </div>
    
    <div class="section">
        <h2>Risk Distribution</h2>
        <div class="metric">
            <strong>Low Risk:</strong> {data.get('risk_distribution', {}).get('LOW', 0)}
        </div>
        <div class="metric">
            <strong>Medium Risk:</strong> {data.get('risk_distribution', {}).get('MEDIUM', 0)}
        </div>
        <div class="metric">
            <strong>High Risk:</strong> {data.get('risk_distribution', {}).get('HIGH', 0)}
        </div>
        <div class="metric">
            <strong>Critical Risk:</strong> {data.get('risk_distribution', {}).get('CRITICAL', 0)}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by Fraud Detection System</p>
    </div>
</body>
</html>
        """
        return html


class SimpleDashboardProvider:
    """Simplified dashboard data provider for testing."""

    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache TTL

    def get_dashboard_data(self, dashboard_type: str = 'main') -> Dict[str, Any]:
        """Get dashboard data for visualization."""
        try:
            if dashboard_type == 'main':
                data = self._get_main_dashboard_data()
            elif dashboard_type == 'fraud':
                data = self._get_fraud_dashboard_data()
            elif dashboard_type == 'performance':
                data = self._get_performance_dashboard_data()
            else:
                data = self._get_main_dashboard_data()

            return data

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error getting dashboard data: %s", e)
            return {}

    def _get_main_dashboard_data(self) -> Dict[str, Any]:
        """Get main dashboard data."""
        return {
            'dashboard_type': 'main',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'today_summary': {
                'total_transactions': 0,
                'fraudulent_transactions': 0,
                'total_amount': 0.0
            },
            'recent_alerts': [],
            'system_status': {
                'status': 'healthy',
                'uptime': '99.9%',
                'last_check': datetime.now(timezone.utc).isoformat(),
                'components': {
                    'kafka': 'online',
                    'postgresql': 'online',
                    'redis': 'online',
                    'analytics': 'online'
                }
            },
            'quick_stats': {
                'transactions_per_minute': 0,
                'average_fraud_score': 0.0,
                'active_alerts': 0
            }
        }

    def _get_fraud_dashboard_data(self) -> Dict[str, Any]:
        """Get fraud dashboard data."""
        return {
            'dashboard_type': 'fraud',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'fraud_trends': {},
            'risk_distribution': {},
            'alert_summary': {},
            'pattern_analysis': {}
        }

    def _get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get performance dashboard data."""
        return {
            'dashboard_type': 'performance',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'throughput_metrics': {},
            'processing_times': {},
            'system_health': {},
            'resource_usage': {}
        }


# Create instances for easy import
simple_report_generator = SimpleReportGenerator()
simple_dashboard_provider = SimpleDashboardProvider()
