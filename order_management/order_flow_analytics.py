#!/usr/bin/env python3
"""
Order Flow Analytics and Reporting Dashboard
Provides comprehensive analytics and reporting for order flow analysis
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsTimeframe(Enum):
    """Analytics timeframe options"""
    REAL_TIME = "REAL_TIME"
    MINUTE = "1M"
    FIVE_MINUTES = "5M"
    FIFTEEN_MINUTES = "15M"
    HOUR = "1H"
    FOUR_HOURS = "4H"
    DAY = "1D"
    WEEK = "1W"
    MONTH = "1M"

class OrderFlowMetric(Enum):
    """Order flow metrics"""
    ORDER_COUNT = "ORDER_COUNT"
    VOLUME = "VOLUME"
    NOTIONAL_VALUE = "NOTIONAL_VALUE"
    AVERAGE_ORDER_SIZE = "AVERAGE_ORDER_SIZE"
    FILL_RATE = "FILL_RATE"
    EXECUTION_SPEED = "EXECUTION_SPEED"
    PRICE_IMPROVEMENT = "PRICE_IMPROVEMENT"
    MARKET_IMPACT = "MARKET_IMPACT"
    VENUE_DISTRIBUTION = "VENUE_DISTRIBUTION"
    ALGORITHM_PERFORMANCE = "ALGORITHM_PERFORMANCE"

class ReportType(Enum):
    """Report types"""
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    DETAILED_ANALYTICS = "DETAILED_ANALYTICS"
    VENUE_ANALYSIS = "VENUE_ANALYSIS"
    ALGORITHM_PERFORMANCE = "ALGORITHM_PERFORMANCE"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
    CUSTOM = "CUSTOM"

@dataclass
class OrderFlowData:
    """Order flow data point"""
    timestamp: datetime
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal]
    filled_quantity: Decimal
    average_fill_price: Optional[Decimal]
    venue: str
    algorithm: str
    execution_time: Optional[timedelta]
    commission: Decimal
    market_impact_bps: Optional[Decimal]
    account_id: str
    strategy_id: Optional[str]
    status: str

@dataclass
class AnalyticsMetrics:
    """Analytics metrics for a time period"""
    timeframe: AnalyticsTimeframe
    start_time: datetime
    end_time: datetime
    
    # Volume metrics
    total_orders: int = 0
    total_volume: Decimal = Decimal('0')
    total_notional: Decimal = Decimal('0')
    average_order_size: Decimal = Decimal('0')
    
    # Performance metrics
    fill_rate: Decimal = Decimal('0')
    average_execution_time: Optional[timedelta] = None
    average_price_improvement_bps: Decimal = Decimal('0')
    average_market_impact_bps: Decimal = Decimal('0')
    
    # Distribution metrics
    buy_sell_ratio: Decimal = Decimal('0')
    venue_distribution: Dict[str, Decimal] = field(default_factory=dict)
    algorithm_distribution: Dict[str, Decimal] = field(default_factory=dict)
    symbol_distribution: Dict[str, Decimal] = field(default_factory=dict)
    
    # Quality metrics
    execution_quality_score: Decimal = Decimal('0')
    total_commission: Decimal = Decimal('0')
    commission_rate_bps: Decimal = Decimal('0')

class OrderFlowAnalyzer:
    """Order flow analytics engine"""
    
    def __init__(self, max_history_days: int = 30):
        self.max_history_days = max_history_days
        self.order_flow_data: List[OrderFlowData] = []
        self.real_time_metrics: Dict[str, Any] = {}
        self.cached_analytics: Dict[str, AnalyticsMetrics] = {}
        self.custom_metrics: Dict[str, Callable] = {}
        
        # Time-based data structures for efficient querying
        self.data_by_timeframe: Dict[AnalyticsTimeframe, List[AnalyticsMetrics]] = {
            timeframe: [] for timeframe in AnalyticsTimeframe
        }
        
        logger.info("Order Flow Analyzer initialized")
    
    def add_order_flow_data(self, order_data: OrderFlowData):
        """Add order flow data point"""
        self.order_flow_data.append(order_data)
        
        # Update real-time metrics
        self._update_real_time_metrics(order_data)
        
        # Clean old data
        self._cleanup_old_data()
        
        logger.debug(f"Added order flow data for {order_data.order_id}")
    
    def _update_real_time_metrics(self, order_data: OrderFlowData):
        """Update real-time metrics"""
        current_time = datetime.now()
        
        # Initialize if not exists
        if 'current_session' not in self.real_time_metrics:
            self.real_time_metrics['current_session'] = {
                'start_time': current_time,
                'order_count': 0,
                'total_volume': Decimal('0'),
                'total_notional': Decimal('0'),
                'venues': set(),
                'symbols': set(),
                'algorithms': set()
            }
        
        session = self.real_time_metrics['current_session']
        session['order_count'] += 1
        session['total_volume'] += order_data.quantity
        if order_data.price:
            session['total_notional'] += order_data.quantity * order_data.price
        session['venues'].add(order_data.venue)
        session['symbols'].add(order_data.symbol)
        session['algorithms'].add(order_data.algorithm)
        session['last_update'] = current_time
    
    def _cleanup_old_data(self):
        """Remove old data beyond retention period"""
        cutoff_time = datetime.now() - timedelta(days=self.max_history_days)
        self.order_flow_data = [
            data for data in self.order_flow_data
            if data.timestamp > cutoff_time
        ]
    
    async def calculate_analytics(self, timeframe: AnalyticsTimeframe, 
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None,
                                symbol: Optional[str] = None,
                                account_id: Optional[str] = None) -> AnalyticsMetrics:
        """Calculate analytics for specified timeframe and filters"""
        
        # Set default time range if not provided
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = self._get_start_time_for_timeframe(timeframe, end_time)
        
        # Filter data
        filtered_data = self._filter_data(start_time, end_time, symbol, account_id)
        
        if not filtered_data:
            return AnalyticsMetrics(
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
        
        # Calculate metrics
        metrics = await self._calculate_metrics(filtered_data, timeframe, start_time, end_time)
        
        # Cache results
        cache_key = f"{timeframe.value}_{start_time.isoformat()}_{end_time.isoformat()}_{symbol}_{account_id}"
        self.cached_analytics[cache_key] = metrics
        
        return metrics
    
    def _get_start_time_for_timeframe(self, timeframe: AnalyticsTimeframe, end_time: datetime) -> datetime:
        """Get start time based on timeframe"""
        if timeframe == AnalyticsTimeframe.MINUTE:
            return end_time - timedelta(minutes=1)
        elif timeframe == AnalyticsTimeframe.FIVE_MINUTES:
            return end_time - timedelta(minutes=5)
        elif timeframe == AnalyticsTimeframe.FIFTEEN_MINUTES:
            return end_time - timedelta(minutes=15)
        elif timeframe == AnalyticsTimeframe.HOUR:
            return end_time - timedelta(hours=1)
        elif timeframe == AnalyticsTimeframe.FOUR_HOURS:
            return end_time - timedelta(hours=4)
        elif timeframe == AnalyticsTimeframe.DAY:
            return end_time - timedelta(days=1)
        elif timeframe == AnalyticsTimeframe.WEEK:
            return end_time - timedelta(weeks=1)
        elif timeframe == AnalyticsTimeframe.MONTH:
            return end_time - timedelta(days=30)
        else:
            return end_time - timedelta(hours=1)  # Default to 1 hour
    
    def _filter_data(self, start_time: datetime, end_time: datetime,
                    symbol: Optional[str] = None, account_id: Optional[str] = None) -> List[OrderFlowData]:
        """Filter order flow data based on criteria"""
        filtered_data = []
        
        for data in self.order_flow_data:
            # Time filter
            if not (start_time <= data.timestamp <= end_time):
                continue
            
            # Symbol filter
            if symbol and data.symbol != symbol:
                continue
            
            # Account filter
            if account_id and data.account_id != account_id:
                continue
            
            filtered_data.append(data)
        
        return filtered_data
    
    async def _calculate_metrics(self, data: List[OrderFlowData], timeframe: AnalyticsTimeframe,
                               start_time: datetime, end_time: datetime) -> AnalyticsMetrics:
        """Calculate comprehensive metrics from filtered data"""
        
        if not data:
            return AnalyticsMetrics(timeframe=timeframe, start_time=start_time, end_time=end_time)
        
        # Basic volume metrics
        total_orders = len(data)
        total_volume = sum(d.quantity for d in data)
        total_notional = sum(d.quantity * (d.price or Decimal('0')) for d in data if d.price)
        average_order_size = total_volume / total_orders if total_orders > 0 else Decimal('0')
        
        # Fill rate calculation
        filled_orders = sum(1 for d in data if d.filled_quantity > 0)
        fill_rate = Decimal(str(filled_orders)) / Decimal(str(total_orders)) if total_orders > 0 else Decimal('0')
        
        # Execution time calculation
        execution_times = [d.execution_time for d in data if d.execution_time]
        average_execution_time = None
        if execution_times:
            total_seconds = sum(et.total_seconds() for et in execution_times)
            average_execution_time = timedelta(seconds=total_seconds / len(execution_times))
        
        # Price improvement and market impact
        price_improvements = [d.market_impact_bps for d in data if d.market_impact_bps is not None]
        average_price_improvement_bps = Decimal('0')
        average_market_impact_bps = Decimal('0')
        
        if price_improvements:
            # Separate positive (improvement) and negative (impact)
            improvements = [pi for pi in price_improvements if pi > 0]
            impacts = [abs(pi) for pi in price_improvements if pi < 0]
            
            if improvements:
                average_price_improvement_bps = sum(improvements) / len(improvements)
            if impacts:
                average_market_impact_bps = sum(impacts) / len(impacts)
        
        # Buy/sell ratio
        buy_orders = sum(1 for d in data if d.side.upper() == 'BUY')
        sell_orders = total_orders - buy_orders
        buy_sell_ratio = Decimal(str(buy_orders)) / Decimal(str(sell_orders)) if sell_orders > 0 else Decimal('0')
        
        # Distribution calculations
        venue_distribution = self._calculate_distribution([d.venue for d in data])
        algorithm_distribution = self._calculate_distribution([d.algorithm for d in data])
        symbol_distribution = self._calculate_distribution([d.symbol for d in data])
        
        # Commission metrics
        total_commission = sum(d.commission for d in data)
        commission_rate_bps = Decimal('0')
        if total_notional > 0:
            commission_rate_bps = (total_commission / total_notional) * 10000
        
        # Execution quality score (simplified)
        execution_quality_score = self._calculate_execution_quality_score(data)
        
        return AnalyticsMetrics(
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            total_orders=total_orders,
            total_volume=total_volume,
            total_notional=total_notional,
            average_order_size=average_order_size,
            fill_rate=fill_rate,
            average_execution_time=average_execution_time,
            average_price_improvement_bps=average_price_improvement_bps,
            average_market_impact_bps=average_market_impact_bps,
            buy_sell_ratio=buy_sell_ratio,
            venue_distribution=venue_distribution,
            algorithm_distribution=algorithm_distribution,
            symbol_distribution=symbol_distribution,
            execution_quality_score=execution_quality_score,
            total_commission=total_commission,
            commission_rate_bps=commission_rate_bps
        )
    
    def _calculate_distribution(self, values: List[str]) -> Dict[str, Decimal]:
        """Calculate percentage distribution of values"""
        if not values:
            return {}
        
        counts = defaultdict(int)
        for value in values:
            counts[value] += 1
        
        total = len(values)
        return {
            key: Decimal(str(count)) / Decimal(str(total)) * 100
            for key, count in counts.items()
        }
    
    def _calculate_execution_quality_score(self, data: List[OrderFlowData]) -> Decimal:
        """Calculate overall execution quality score (0-100)"""
        if not data:
            return Decimal('0')
        
        score_components = []
        
        # Fill rate component (0-30 points)
        filled_orders = sum(1 for d in data if d.filled_quantity > 0)
        fill_rate = filled_orders / len(data)
        score_components.append(fill_rate * 30)
        
        # Speed component (0-25 points)
        execution_times = [d.execution_time.total_seconds() for d in data if d.execution_time]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            # Score inversely related to execution time (faster = better)
            speed_score = max(0, 25 - (avg_time / 60) * 5)  # Penalty for each minute
            score_components.append(speed_score)
        else:
            score_components.append(15)  # Default moderate score
        
        # Cost component (0-25 points)
        market_impacts = [abs(d.market_impact_bps) for d in data if d.market_impact_bps is not None]
        if market_impacts:
            avg_impact = sum(market_impacts) / len(market_impacts)
            # Score inversely related to market impact
            cost_score = max(0, 25 - float(avg_impact) / 2)
            score_components.append(cost_score)
        else:
            score_components.append(15)  # Default moderate score
        
        # Venue diversification component (0-20 points)
        unique_venues = len(set(d.venue for d in data))
        diversification_score = min(20, unique_venues * 5)
        score_components.append(diversification_score)
        
        total_score = sum(score_components)
        return Decimal(str(total_score)).quantize(Decimal('0.01'))
    
    async def generate_report(self, report_type: ReportType, 
                            timeframe: AnalyticsTimeframe = AnalyticsTimeframe.DAY,
                            filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        
        filters = filters or {}
        
        # Calculate analytics
        analytics = await self.calculate_analytics(
            timeframe=timeframe,
            start_time=filters.get('start_time'),
            end_time=filters.get('end_time'),
            symbol=filters.get('symbol'),
            account_id=filters.get('account_id')
        )
        
        # Generate report based on type
        if report_type == ReportType.EXECUTIVE_SUMMARY:
            return self._generate_executive_summary(analytics)
        elif report_type == ReportType.DETAILED_ANALYTICS:
            return self._generate_detailed_analytics(analytics)
        elif report_type == ReportType.VENUE_ANALYSIS:
            return self._generate_venue_analysis(analytics)
        elif report_type == ReportType.ALGORITHM_PERFORMANCE:
            return self._generate_algorithm_performance(analytics)
        elif report_type == ReportType.RISK_ANALYSIS:
            return self._generate_risk_analysis(analytics)
        elif report_type == ReportType.COMPLIANCE_REPORT:
            return self._generate_compliance_report(analytics)
        else:
            return self._generate_detailed_analytics(analytics)
    
    def _generate_executive_summary(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate executive summary report"""
        return {
            'report_type': 'Executive Summary',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'key_metrics': {
                'total_orders': analytics.total_orders,
                'total_volume': str(analytics.total_volume),
                'total_notional': str(analytics.total_notional),
                'fill_rate_percent': str(analytics.fill_rate),
                'execution_quality_score': str(analytics.execution_quality_score),
                'average_execution_time_seconds': analytics.average_execution_time.total_seconds() if analytics.average_execution_time else None
            },
            'performance_highlights': {
                'price_improvement_bps': str(analytics.average_price_improvement_bps),
                'market_impact_bps': str(analytics.average_market_impact_bps),
                'commission_rate_bps': str(analytics.commission_rate_bps)
            },
            'distribution_summary': {
                'top_venue': max(analytics.venue_distribution.items(), key=lambda x: x[1]) if analytics.venue_distribution else None,
                'top_algorithm': max(analytics.algorithm_distribution.items(), key=lambda x: x[1]) if analytics.algorithm_distribution else None,
                'buy_sell_ratio': str(analytics.buy_sell_ratio)
            }
        }
    
    def _generate_detailed_analytics(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate detailed analytics report"""
        return {
            'report_type': 'Detailed Analytics',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'volume_metrics': {
                'total_orders': analytics.total_orders,
                'total_volume': str(analytics.total_volume),
                'total_notional': str(analytics.total_notional),
                'average_order_size': str(analytics.average_order_size)
            },
            'performance_metrics': {
                'fill_rate': str(analytics.fill_rate),
                'average_execution_time_seconds': analytics.average_execution_time.total_seconds() if analytics.average_execution_time else None,
                'price_improvement_bps': str(analytics.average_price_improvement_bps),
                'market_impact_bps': str(analytics.average_market_impact_bps),
                'execution_quality_score': str(analytics.execution_quality_score)
            },
            'cost_metrics': {
                'total_commission': str(analytics.total_commission),
                'commission_rate_bps': str(analytics.commission_rate_bps)
            },
            'distribution_metrics': {
                'buy_sell_ratio': str(analytics.buy_sell_ratio),
                'venue_distribution': {k: str(v) for k, v in analytics.venue_distribution.items()},
                'algorithm_distribution': {k: str(v) for k, v in analytics.algorithm_distribution.items()},
                'symbol_distribution': {k: str(v) for k, v in analytics.symbol_distribution.items()}
            }
        }
    
    def _generate_venue_analysis(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate venue analysis report"""
        return {
            'report_type': 'Venue Analysis',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'venue_distribution': {k: str(v) for k, v in analytics.venue_distribution.items()},
            'venue_performance': {
                # This would include venue-specific performance metrics
                # For now, just show distribution
                'distribution_analysis': analytics.venue_distribution
            },
            'recommendations': self._generate_venue_recommendations(analytics)
        }
    
    def _generate_algorithm_performance(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate algorithm performance report"""
        return {
            'report_type': 'Algorithm Performance',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'algorithm_distribution': {k: str(v) for k, v in analytics.algorithm_distribution.items()},
            'performance_analysis': {
                'overall_quality_score': str(analytics.execution_quality_score),
                'average_market_impact': str(analytics.average_market_impact_bps),
                'price_improvement': str(analytics.average_price_improvement_bps)
            },
            'recommendations': self._generate_algorithm_recommendations(analytics)
        }
    
    def _generate_risk_analysis(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate risk analysis report"""
        return {
            'report_type': 'Risk Analysis',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'risk_metrics': {
                'market_impact_bps': str(analytics.average_market_impact_bps),
                'execution_quality_score': str(analytics.execution_quality_score),
                'venue_concentration': self._calculate_venue_concentration(analytics),
                'fill_rate': str(analytics.fill_rate)
            },
            'risk_alerts': self._generate_risk_alerts(analytics)
        }
    
    def _generate_compliance_report(self, analytics: AnalyticsMetrics) -> Dict[str, Any]:
        """Generate compliance report"""
        return {
            'report_type': 'Compliance Report',
            'period': f"{analytics.start_time.strftime('%Y-%m-%d %H:%M')} to {analytics.end_time.strftime('%Y-%m-%d %H:%M')}",
            'compliance_metrics': {
                'total_orders': analytics.total_orders,
                'fill_rate': str(analytics.fill_rate),
                'venue_distribution': {k: str(v) for k, v in analytics.venue_distribution.items()},
                'execution_quality': str(analytics.execution_quality_score)
            },
            'regulatory_summary': {
                'best_execution_compliance': 'COMPLIANT' if analytics.execution_quality_score > 70 else 'REVIEW_REQUIRED',
                'venue_diversification': 'ADEQUATE' if len(analytics.venue_distribution) >= 2 else 'INSUFFICIENT'
            }
        }
    
    def _generate_venue_recommendations(self, analytics: AnalyticsMetrics) -> List[str]:
        """Generate venue-specific recommendations"""
        recommendations = []
        
        if len(analytics.venue_distribution) < 2:
            recommendations.append("Consider diversifying across more venues to improve execution quality")
        
        # Check for venue concentration
        if analytics.venue_distribution:
            max_venue_percentage = max(analytics.venue_distribution.values())
            if max_venue_percentage > 80:
                recommendations.append("High concentration in single venue - consider rebalancing")
        
        return recommendations
    
    def _generate_algorithm_recommendations(self, analytics: AnalyticsMetrics) -> List[str]:
        """Generate algorithm-specific recommendations"""
        recommendations = []
        
        if analytics.average_market_impact_bps > 10:
            recommendations.append("High market impact detected - consider using stealth algorithms")
        
        if analytics.execution_quality_score < 60:
            recommendations.append("Low execution quality - review algorithm selection criteria")
        
        return recommendations
    
    def _calculate_venue_concentration(self, analytics: AnalyticsMetrics) -> str:
        """Calculate venue concentration risk"""
        if not analytics.venue_distribution:
            return "NO_DATA"
        
        max_percentage = max(analytics.venue_distribution.values())
        
        if max_percentage > 80:
            return "HIGH"
        elif max_percentage > 60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_risk_alerts(self, analytics: AnalyticsMetrics) -> List[str]:
        """Generate risk alerts"""
        alerts = []
        
        if analytics.fill_rate < Decimal('0.9'):
            alerts.append("LOW_FILL_RATE: Fill rate below 90%")
        
        if analytics.average_market_impact_bps > 15:
            alerts.append("HIGH_MARKET_IMPACT: Average market impact exceeds 15 bps")
        
        if analytics.execution_quality_score < 50:
            alerts.append("POOR_EXECUTION_QUALITY: Quality score below 50")
        
        return alerts
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        current_session = self.real_time_metrics.get('current_session', {})
        
        return {
            'session_start': current_session.get('start_time', datetime.now()).isoformat(),
            'last_update': current_session.get('last_update', datetime.now()).isoformat(),
            'order_count': current_session.get('order_count', 0),
            'total_volume': str(current_session.get('total_volume', Decimal('0'))),
            'total_notional': str(current_session.get('total_notional', Decimal('0'))),
            'active_venues': len(current_session.get('venues', set())),
            'active_symbols': len(current_session.get('symbols', set())),
            'active_algorithms': len(current_session.get('algorithms', set())),
            'orders_per_minute': self._calculate_orders_per_minute()
        }
    
    def _calculate_orders_per_minute(self) -> float:
        """Calculate orders per minute for current session"""
        current_session = self.real_time_metrics.get('current_session', {})
        
        if 'start_time' not in current_session:
            return 0.0
        
        duration = datetime.now() - current_session['start_time']
        duration_minutes = duration.total_seconds() / 60
        
        if duration_minutes > 0:
            return current_session.get('order_count', 0) / duration_minutes
        
        return 0.0

async def main():
    """Example usage of Order Flow Analytics"""
    analyzer = OrderFlowAnalyzer()
    
    # Add sample order flow data
    sample_data = OrderFlowData(
        timestamp=datetime.now(),
        order_id='TEST_001',
        symbol='EURUSD',
        side='BUY',
        order_type='MARKET',
        quantity=Decimal('100000'),
        price=Decimal('1.1000'),
        filled_quantity=Decimal('100000'),
        average_fill_price=Decimal('1.1001'),
        venue='ECN_PRIMARY',
        algorithm='DIRECT',
        execution_time=timedelta(seconds=0.5),
        commission=Decimal('20.0'),
        market_impact_bps=Decimal('2.5'),
        account_id='ACCOUNT_001',
        strategy_id='STRATEGY_001',
        status='FILLED'
    )
    
    analyzer.add_order_flow_data(sample_data)
    
    # Calculate analytics
    analytics = await analyzer.calculate_analytics(AnalyticsTimeframe.HOUR)
    
    print("Order Flow Analytics Results:")
    print(f"Total Orders: {analytics.total_orders}")
    print(f"Total Volume: {analytics.total_volume}")
    print(f"Fill Rate: {analytics.fill_rate}%")
    print(f"Execution Quality Score: {analytics.execution_quality_score}")
    
    # Generate reports
    executive_report = await analyzer.generate_report(ReportType.EXECUTIVE_SUMMARY)
    print(f"\\nExecutive Summary: {json.dumps(executive_report, indent=2, default=str)}")
    
    # Get real-time dashboard data
    dashboard_data = analyzer.get_real_time_dashboard_data()
    print(f"\\nReal-time Dashboard: {json.dumps(dashboard_data, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(main())