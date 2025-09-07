"""Report Generator for Analytics Module
Generates comprehensive analytics reports in various formats.
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import logging
from dataclasses import dataclass, field
from jinja2 import Template
import matplotlib.pyplot as plt
import io
import base64


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    report_format: str = "pdf"  # pdf, html, json, csv
    include_charts: bool = True
    include_tables: bool = True
    include_metrics: bool = True
    template_path: Optional[str] = None
    output_path: Optional[str] = None


@dataclass
class ReportSection:
    """Represents a section in the report."""
    title: str
    content: Union[str, pd.DataFrame, Dict[str, Any]]
    section_type: str  # text, table, chart, metrics
    order: int


class ReportGenerator:
    """Generates comprehensive analytics reports."""
    
    def __init__(self, config: ReportConfig):
        """Initialize the report generator with configuration.
        
        Args:
            config: ReportConfig object with generation parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.sections: List[ReportSection] = []
        
    def add_section(self, title: str, content: Union[str, pd.DataFrame, Dict[str, Any]], 
                   section_type: str, order: int = 0):
        """Add a section to the report.
        
        Args:
            title: Section title
            content: Section content (text, DataFrame, or dictionary)
            section_type: Type of section (text, table, chart, metrics)
            order: Order of section in report
        """
        section = ReportSection(title=title, content=content, section_type=section_type, order=order)
        self.sections.append(section)
        
    def add_text_section(self, title: str, text: str, order: int = 0):
        """Add a text section to the report.
        
        Args:
            title: Section title
            text: Text content
            order: Order of section in report
        """
        self.add_section(title, text, "text", order)
        
    def add_table_section(self, title: str, table: pd.DataFrame, order: int = 0):
        """Add a table section to the report.
        
        Args:
            title: Section title
            table: DataFrame to include as table
            order: Order of section in report
        """
        self.add_section(title, table, "table", order)
        
    def add_metrics_section(self, title: str, metrics: Dict[str, Any], order: int = 0):
        """Add a metrics section to the report.
        
        Args:
            title: Section title
            metrics: Dictionary of metrics
            order: Order of section in report
        """
        self.add_section(title, metrics, "metrics", order)
        
    def generate_daily_report(self, portfolio_data: Dict[str, Any], 
                            performance_metrics: Dict[str, Any],
                            risk_metrics: Dict[str, Any]) -> str:
        """Generate a daily analytics report.
        
        Args:
            portfolio_data: Portfolio information
            performance_metrics: Performance metrics dictionary
            risk_metrics: Risk metrics dictionary
            
        Returns:
            Generated report as string (format depends on config)
        """
        try:
            # Clear existing sections
            self.sections = []
            
            # Add report header
            report_date = datetime.now().strftime("%Y-%m-%d")
            self.add_text_section("Daily Analytics Report", 
                                f"Generated on {report_date}\n\nThis report provides a comprehensive analysis of trading performance and risk metrics.",
                                order=0)
            
            # Add portfolio summary
            portfolio_summary = {
                "Total Equity": portfolio_data.get("total_equity", 0),
                "Cash Balance": portfolio_data.get("cash_balance", 0),
                "Unrealized PnL": portfolio_data.get("unrealized_pnl", 0),
                "Realized PnL": portfolio_data.get("realized_pnl", 0),
                "Number of Positions": len(portfolio_data.get("positions", {}))
            }
            self.add_metrics_section("Portfolio Summary", portfolio_summary, order=1)
            
            # Add performance metrics
            self.add_metrics_section("Performance Metrics", performance_metrics, order=2)
            
            # Add risk metrics
            self.add_metrics_section("Risk Metrics", risk_metrics, order=3)
            
            # Add positions summary if available
            positions = portfolio_data.get("positions", {})
            if positions:
                positions_df = pd.DataFrame.from_dict(positions, orient='index')
                self.add_table_section("Current Positions", positions_df, order=4)
            
            # Generate report based on format
            if self.config.report_format == "json":
                return self._generate_json_report()
            elif self.config.report_format == "html":
                return self._generate_html_report()
            else:
                return self._generate_text_report()
                
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return f"Error generating report: {e}"
    
    def generate_monthly_report(self, monthly_data: Dict[str, Any]) -> str:
        """Generate a monthly analytics report.
        
        Args:
            monthly_data: Dictionary containing monthly performance data
            
        Returns:
            Generated report as string
        """
        try:
            # Clear existing sections
            self.sections = []
            
            # Add report header
            report_date = datetime.now().strftime("%Y-%m")
            self.add_text_section("Monthly Analytics Report", 
                                f"Generated for {report_date}\n\nThis report provides a comprehensive analysis of monthly trading performance.",
                                order=0)
            
            # Add monthly summary
            monthly_summary = {
                "Total Return": monthly_data.get("total_return", 0),
                "Annualized Return": monthly_data.get("annualized_return", 0),
                "Max Drawdown": monthly_data.get("max_drawdown", 0),
                "Sharpe Ratio": monthly_data.get("sharpe_ratio", 0),
                "Total Trades": monthly_data.get("total_trades", 0),
                "Win Rate": monthly_data.get("win_rate", 0)
            }
            self.add_metrics_section("Monthly Summary", monthly_summary, order=1)
            
            # Add detailed metrics if available
            if "daily_returns" in monthly_data:
                returns_df = pd.DataFrame(monthly_data["daily_returns"])
                self.add_table_section("Daily Returns", returns_df, order=2)
            
            # Generate report based on format
            if self.config.report_format == "json":
                return self._generate_json_report()
            elif self.config.report_format == "html":
                return self._generate_html_report()
            else:
                return self._generate_text_report()
                
        except Exception as e:
            self.logger.error(f"Error generating monthly report: {e}")
            return f"Error generating report: {e}"
    
    def _generate_text_report(self) -> str:
        """Generate a text format report.
        
        Returns:
            Report as text string
        """
        try:
            # Sort sections by order
            sorted_sections = sorted(self.sections, key=lambda x: x.order)
            
            report_lines = []
            
            for section in sorted_sections:
                report_lines.append(f"\n{'='*50}")
                report_lines.append(f"{section.title}")
                report_lines.append(f"{'='*50}")
                
                if section.section_type == "text":
                    report_lines.append(str(section.content))
                elif section.section_type == "metrics":
                    for key, value in section.content.items():
                        report_lines.append(f"{key}: {value}")
                elif section.section_type == "table":
                    report_lines.append(section.content.to_string())
                elif section.section_type == "chart":
                    report_lines.append("[Chart Section - See HTML/PDF for visualization]")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating text report: {e}")
            return f"Error generating report: {e}"
    
    def _generate_json_report(self) -> str:
        """Generate a JSON format report.
        
        Returns:
            Report as JSON string
        """
        try:
            report_dict = {
                "generated_at": datetime.now().isoformat(),
                "format": "json",
                "sections": []
            }
            
            # Sort sections by order
            sorted_sections = sorted(self.sections, key=lambda x: x.order)
            
            for section in sorted_sections:
                section_dict = {
                    "title": section.title,
                    "type": section.section_type,
                    "order": section.order
                }
                
                if section.section_type == "text":
                    section_dict["content"] = str(section.content)
                elif section.section_type == "metrics":
                    section_dict["content"] = section.content
                elif section.section_type == "table":
                    section_dict["content"] = section.content.to_dict()
                elif section.section_type == "chart":
                    section_dict["content"] = "Chart data not included in JSON format"
                
                report_dict["sections"].append(section_dict)
            
            return json.dumps(report_dict, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error generating JSON report: {e}")
            return json.dumps({"error": f"Error generating report: {e}"})
    
    def _generate_html_report(self) -> str:
        """Generate an HTML format report.
        
        Returns:
            Report as HTML string
        """
        try:
            # Simple HTML template
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Analytics Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1, h2 { color: #333; }
                    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .section { margin: 30px 0; }
                </style>
            </head>
            <body>
                <h1>Analytics Report</h1>
                <p>Generated on: {{ generated_at }}</p>
                
                {% for section in sections %}
                <div class="section">
                    <h2>{{ section.title }}</h2>
                    {% if section.type == "text" %}
                        <p>{{ section.content }}</p>
                    {% elif section.type == "metrics" %}
                        <table>
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for key, value in section.content.items() %}
                                <tr>
                                    <td>{{ key }}</td>
                                    <td>{{ value }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% elif section.type == "table" %}
                        {{ section.content.to_html(classes="table", escape=False) }}
                    {% elif section.type == "chart" %}
                        <p>Chart visualization would appear here in a full implementation.</p>
                    {% endif %}
                </div>
                {% endfor %}
            </body>
            </html>
            """
            
            # Sort sections by order
            sorted_sections = sorted(self.sections, key=lambda x: x.order)
            
            template = Template(html_template)
            return template.render(
                generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sections=sorted_sections
            )
            
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {e}")
            return f"<html><body><h1>Error generating report</h1><p>{e}</p></body></html>"