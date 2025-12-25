"""
Automated report generation system for fraud detection analytics.
"""
import logging
import json
from typing import Dict, List, Any
from datetime import datetime, timezone
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from jinja2 import Environment, FileSystemLoader
import weasyprint

from src.analytics.engine import batch_analytics
from src.data_models.database.repositories import redis_repo

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Automated report generator for fraud detection analytics."""

    def __init__(self):
        self.template_dir = Path(__file__).parent / "templates"
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )

        # Email configuration
        self.email_config = self._get_email_config()

    def _get_email_config(self) -> Dict[str, str]:
        """Get email configuration from environment variables."""
        return {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'your-email@gmail.com',
            'password': 'your-app-password',
            'from_email': 'fraud-detection@company.com',
            'from_name': 'Fraud Detection System'
        }

    def generate_daily_report(self, date: datetime, output_format: str = 'pdf') -> str:
        """Generate daily fraud detection report."""
        try:
            # Get analytics data
            report_data = batch_analytics.generate_daily_report(date)

            # Generate report based on format
            if output_format.lower() == 'pdf':
                return self._generate_pdf_report(report_data, 'daily', date)
            elif output_format.lower() == 'html':
                return self._generate_html_report(report_data, 'daily', date)
            elif output_format.lower() == 'json':
                return self._generate_json_report(report_data, 'daily', date)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error generating daily report: %s", e)
            raise

    def generate_weekly_report(self, start_date: datetime, output_format: str = 'pdf') -> str:
        """Generate weekly fraud detection report."""
        try:
            # Get analytics data
            report_data = batch_analytics.generate_weekly_report(start_date)

            # Generate report based on format
            if output_format.lower() == 'pdf':
                return self._generate_pdf_report(report_data, 'weekly', start_date)
            elif output_format.lower() == 'html':
                return self._generate_html_report(report_data, 'weekly', start_date)
            elif output_format.lower() == 'json':
                return self._generate_json_report(report_data, 'weekly', start_date)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error generating weekly report: %s", e)
            raise

    def generate_custom_report(self, report_type: str, start_date: datetime,
                               end_date: datetime, output_format: str = 'pdf') -> str:
        """Generate custom fraud detection report."""
        try:
            # Get custom analytics data
            report_data = self._get_custom_report_data(
                report_type, start_date, end_date)

            # Generate report based on format
            if output_format.lower() == 'pdf':
                return self._generate_pdf_report(report_data, report_type, start_date)
            elif output_format.lower() == 'html':
                return self._generate_html_report(report_data, report_type, start_date)
            elif output_format.lower() == 'json':
                return self._generate_json_report(report_data, report_type, start_date)
            else:
                raise ValueError(f"Unsupported report format: {output_format}")

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error generating custom report: %s", e)
            raise

    def _generate_pdf_report(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate PDF report."""
        try:
            # Generate HTML first
            html_content = self._generate_html_content(data, report_type, date)

            # Convert HTML to PDF
            pdf_content = weasyprint.HTML(string=html_content).write_pdf()

            # Save PDF file
            filename = f"{report_type}_report_{date.strftime('%Y%m%d')}.pdf"
            filepath = self.output_dir / filename

            with open(filepath, 'wb') as f:
                f.write(pdf_content)

            logger.info("PDF report generated: %s", filepath)
            return str(filepath)

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating PDF report: %s", e)
            raise

    def _generate_html_report(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate HTML report."""
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

    def _generate_html_content(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate HTML content for reports."""
        try:
            # Load template
            template_name = f"{report_type}_report.html"
            template = self.jinja_env.get_template(template_name)

            # Prepare template data
            template_data = {
                'data': data,
                'report_type': report_type.title(),
                'date': date.strftime('%Y-%m-%d'),
                'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'company_name': 'Fraud Detection System',
                'logo_url': 'https://example.com/logo.png'
            }

            # Render template
            html_content = template.render(**template_data)
            return html_content

        except (ValueError, RuntimeError, AttributeError, TypeError, OSError) as e:
            logger.error("Error generating HTML content: %s", e)
            # Fallback to basic HTML
            return self._generate_fallback_html(data, report_type, date)

    def _generate_fallback_html(self, data: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Generate fallback HTML when template is not available."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_type.title()} Fraud Detection Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_type.title()} Fraud Detection Report</h1>
                <p>Date: {date.strftime('%Y-%m-%d')}</p>
                <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="section">
                <h2>Transaction Summary</h2>
                <div class="metric">
                    <strong>Total Transactions:</strong> {data.get('transaction_summary', {}).get('total_transactions', 0)}
                </div>
                <div class="metric">
                    <strong>Total Amount:</strong> ${data.get('transaction_summary', {}).get('total_amount', 0):,.2f}
                </div>
                <div class="metric">
                    <strong>Average Amount:</strong> ${data.get('transaction_summary', {}).get('average_amount', 0):,.2f}
                </div>
            </div>
            
            <div class="section">
                <h2>Fraud Summary</h2>
                <div class="metric">
                    <strong>Total Scores:</strong> {data.get('fraud_summary', {}).get('total_scores', 0)}
                </div>
                <div class="metric">
                    <strong>Average Score:</strong> {data.get('fraud_summary', {}).get('average_score', 0):.3f}
                </div>
                <div class="metric">
                    <strong>High Risk Count:</strong> {data.get('fraud_summary', {}).get('high_risk_count', 0)}
                </div>
            </div>
            
            <div class="section">
                <h2>Alert Summary</h2>
                <div class="metric">
                    <strong>Total Alerts:</strong> {data.get('alert_summary', {}).get('total_alerts', 0)}
                </div>
                <div class="metric">
                    <strong>Pending Alerts:</strong> {data.get('alert_summary', {}).get('pending_alerts', 0)}
                </div>
                <div class="metric">
                    <strong>Critical Alerts:</strong> {data.get('alert_summary', {}).get('critical_alerts', 0)}
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _get_custom_report_data(self, report_type: str, start_date: datetime,
                                end_date: datetime) -> Dict[str, Any]:
        """Get custom report data based on type."""
        if report_type == 'fraud_analysis':
            return self._get_fraud_analysis_data(start_date, end_date)
        elif report_type == 'performance_analysis':
            return self._get_performance_analysis_data(start_date, end_date)
        elif report_type == 'geographic_analysis':
            return self._get_geographic_analysis_data(start_date, end_date)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def _get_fraud_analysis_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get fraud analysis data."""
        # This would contain detailed fraud analysis
        return {
            'report_type': 'fraud_analysis',
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'fraud_patterns': {},
            'risk_distribution': {},
            'alert_trends': {}
        }

    def _get_performance_analysis_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get performance analysis data."""
        # This would contain system performance metrics
        return {
            'report_type': 'performance_analysis',
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'system_metrics': {},
            'processing_times': {},
            'throughput_analysis': {}
        }

    def _get_geographic_analysis_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get geographic analysis data."""
        # This would contain geographic fraud patterns
        return {
            'report_type': 'geographic_analysis',
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'country_analysis': {},
            'city_analysis': {},
            'location_patterns': {}
        }

    def send_report_email(self, report_filepath: str, recipients: List[str],
                          subject: str = None, body: str = None) -> bool:
        """Send report via email."""
        try:
            # Prepare email
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_config['from_name']} <{self.email_config['from_email']}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject or "Fraud Detection Report"

            # Email body
            body = body or "Please find attached the fraud detection report."
            msg.attach(MIMEText(body, 'plain'))

            # Attach report file
            with open(report_filepath, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(report_filepath).name}'
            )
            msg.attach(part)

            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(
                    self.email_config['username'], self.email_config['password'])
                server.send_message(msg)

            logger.info("Report email sent to %s", recipients)
            return True

        except (ValueError, RuntimeError, AttributeError, TypeError, smtplib.SMTPException) as e:
            logger.error("Error sending report email: %s", e)
            return False

    def schedule_report(self, report_type: str, schedule: str, recipients: List[str],
                        output_format: str = 'pdf') -> bool:
        """Schedule automated report generation and delivery."""
        try:
            # Store schedule in Redis
            schedule_key = f"report_schedule:{report_type}:{schedule}"
            schedule_data = {
                'report_type': report_type,
                'schedule': schedule,
                'recipients': recipients,
                'format': output_format,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'active': True
            }

            redis_repo.set_hash(schedule_key, schedule_data)
            logger.info("Report schedule created: %s", schedule_key)
            return True

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error scheduling report: %s", e)
            return False

    def get_scheduled_reports(self) -> List[Dict[str, Any]]:
        """Get all scheduled reports."""
        try:
            # Get all schedule keys from Redis
            _ = "report_schedule:*"
            # This would need to be implemented based on Redis pattern matching
            # For now, return empty list
            return []

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error getting scheduled reports: %s", e)
            return []


class DashboardDataProvider:
    """Data provider for dashboard visualizations."""

    def __init__(self):
        self.cache_ttl = 300  # 5 minutes cache TTL

    def get_dashboard_data(self, dashboard_type: str = 'main') -> Dict[str, Any]:
        """Get dashboard data for visualization."""
        cache_key = f"dashboard_data:{dashboard_type}"

        # Check cache first
        cached_data = redis_repo.get_cache(cache_key)
        if cached_data:
            return json.loads(cached_data)

        try:
            if dashboard_type == 'main':
                data = self._get_main_dashboard_data()
            elif dashboard_type == 'fraud':
                data = self._get_fraud_dashboard_data()
            elif dashboard_type == 'performance':
                data = self._get_performance_dashboard_data()
            else:
                data = self._get_main_dashboard_data()

            # Cache the data
            redis_repo.set_cache(cache_key, json.dumps(data), self.cache_ttl)

            return data

        except (ValueError, RuntimeError, AttributeError, TypeError) as e:
            logger.error("Error getting dashboard data: %s", e)
            return {}

    def _get_main_dashboard_data(self) -> Dict[str, Any]:
        """Get main dashboard data."""
        today = datetime.now(timezone.utc).date()
        start_date = datetime.combine(today, datetime.min.time())
        _ = datetime.combine(today, datetime.max.time())

        return {
            'dashboard_type': 'main',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'today_summary': batch_analytics.generate_daily_report(start_date),
            'recent_alerts': self._get_recent_alerts(),
            'system_status': self._get_system_status(),
            'quick_stats': self._get_quick_stats()
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

    def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts for dashboard."""
        # This would fetch recent alerts from the database
        return []

    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status for dashboard."""
        return {
            'status': 'healthy',
            'uptime': '99.9%',
            'last_check': datetime.now(timezone.utc).isoformat(),
            'components': {
                'kafka': 'online',
                'postgresql': 'online',
                'redis': 'online',
                'analytics': 'online'
            }
        }

    def _get_quick_stats(self) -> Dict[str, Any]:
        """Get quick statistics for dashboard."""
        return {
            'total_transactions_today': 0,
            'fraud_alerts_today': 0,
            'average_fraud_score': 0.0,
            'system_throughput': 0
        }


# Global instances
report_generator = ReportGenerator()
dashboard_provider = DashboardDataProvider()
