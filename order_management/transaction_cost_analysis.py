#!/usr/bin/env python3
"""
Transaction Cost Analysis (TCA) System
Provides comprehensive analysis of order execution quality and transaction costs
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkType(Enum):
    """Types of execution benchmarks"""
    ARRIVAL_PRICE = "ARRIVAL_PRICE"  # Price when order arrived
    DECISION_PRICE = "DECISION_PRICE"  # Price when decision was made
    OPEN_PRICE = "OPEN_PRICE"  # Opening price of the period
    CLOSE_PRICE = "CLOSE_PRICE"  # Closing price of the period
    VWAP = "VWAP"  # Volume Weighted Average Price
    TWAP = "TWAP"  # Time Weighted Average Price
    MID_PRICE = "MID_PRICE"  # Mid price at execution time
    IMPLEMENTATION_SHORTFALL = "IMPLEMENTATION_SHORTFALL"  # IS benchmark

class CostComponent(Enum):
    """Components of transaction costs"""
    SPREAD_COST = "SPREAD_COST"  # Bid-ask spread cost
    MARKET_IMPACT = "MARKET_IMPACT"  # Price impact from order
    TIMING_COST = "TIMING_COST"  # Cost of execution timing
    OPPORTUNITY_COST = "OPPORTUNITY_COST"  # Cost of not executing
    COMMISSION = "COMMISSION"  # Explicit commission costs
    FEES = "FEES"  # Other explicit fees
    SLIPPAGE = "SLIPPAGE"  # Price slippage

class ExecutionQuality(Enum):
    """Execution quality ratings"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    VERY_POOR = "VERY_POOR"

@dataclass
class MarketDataPoint:
    """Market data at a specific point in time"""
    timestamp: datetime
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    mid_price: Decimal
    last_price: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    
    @property
    def spread(self) -> Decimal:
        return self.ask_price - self.bid_price
    
    @property
    def spread_bps(self) -> Decimal:
        """Spread in basis points"""
        if self.mid_price > 0:
            return (self.spread / self.mid_price) * 10000
        return Decimal('0')

@dataclass
class ExecutionData:
    """Execution data for TCA analysis"""
    execution_id: str
    order_id: str
    timestamp: datetime
    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    price: Decimal
    venue: str
    commission: Decimal
    fees: Decimal = Decimal('0')
    liquidity_flag: str = "UNKNOWN"  # MAKER, TAKER, etc.

@dataclass
class OrderData:
    """Order data for TCA analysis"""
    order_id: str
    symbol: str
    side: str
    original_quantity: Decimal
    order_type: str
    limit_price: Optional[Decimal] = None
    arrival_time: Optional[datetime] = None
    decision_time: Optional[datetime] = None
    first_fill_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    strategy_id: Optional[str] = None
    account_id: Optional[str] = None

@dataclass
class TCAMetrics:
    """Transaction Cost Analysis metrics"""
    order_id: str
    symbol: str
    side: str
    total_quantity: Decimal
    average_price: Decimal
    total_commission: Decimal
    total_fees: Decimal
    
    # Benchmark prices
    arrival_price: Optional[Decimal] = None
    decision_price: Optional[Decimal] = None
    vwap_benchmark: Optional[Decimal] = None
    twap_benchmark: Optional[Decimal] = None
    
    # Cost components (in basis points)
    spread_cost_bps: Decimal = Decimal('0')
    market_impact_bps: Decimal = Decimal('0')
    timing_cost_bps: Decimal = Decimal('0')
    opportunity_cost_bps: Decimal = Decimal('0')
    commission_bps: Decimal = Decimal('0')
    total_cost_bps: Decimal = Decimal('0')
    
    # Performance metrics
    price_improvement_bps: Decimal = Decimal('0')
    implementation_shortfall_bps: Decimal = Decimal('0')
    execution_quality: ExecutionQuality = ExecutionQuality.FAIR
    
    # Timing metrics
    execution_duration: Optional[timedelta] = None
    fill_rate: Decimal = Decimal('1.0')  # Percentage filled
    
    # Venue analysis
    venue_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'total_quantity': str(self.total_quantity),
            'average_price': str(self.average_price),
            'total_commission': str(self.total_commission),
            'total_fees': str(self.total_fees),
            'spread_cost_bps': str(self.spread_cost_bps),
            'market_impact_bps': str(self.market_impact_bps),
            'timing_cost_bps': str(self.timing_cost_bps),
            'opportunity_cost_bps': str(self.opportunity_cost_bps),
            'commission_bps': str(self.commission_bps),
            'total_cost_bps': str(self.total_cost_bps),
            'price_improvement_bps': str(self.price_improvement_bps),
            'implementation_shortfall_bps': str(self.implementation_shortfall_bps),
            'execution_quality': self.execution_quality.value,
            'fill_rate': str(self.fill_rate),
            'venue_breakdown': {k: str(v) for k, v in self.venue_breakdown.items()}
        }
        
        if self.arrival_price:
            result['arrival_price'] = str(self.arrival_price)
        if self.decision_price:
            result['decision_price'] = str(self.decision_price)
        if self.vwap_benchmark:
            result['vwap_benchmark'] = str(self.vwap_benchmark)
        if self.twap_benchmark:
            result['twap_benchmark'] = str(self.twap_benchmark)
        if self.execution_duration:
            result['execution_duration_seconds'] = self.execution_duration.total_seconds()
        
        return result

class TransactionCostAnalyzer:
    """Main TCA analysis engine"""
    
    def __init__(self):
        self.market_data_cache: Dict[str, List[MarketDataPoint]] = defaultdict(list)
        self.execution_cache: Dict[str, List[ExecutionData]] = defaultdict(list)
        self.order_cache: Dict[str, OrderData] = {}
        self.tca_results: Dict[str, TCAMetrics] = {}
        self.benchmark_cache: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
        
        logger.info("Transaction Cost Analyzer initialized")
    
    def add_market_data(self, market_data: MarketDataPoint):
        """Add market data point for analysis"""
        self.market_data_cache[market_data.symbol].append(market_data)
        
        # Keep only recent data (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.market_data_cache[market_data.symbol] = [
            md for md in self.market_data_cache[market_data.symbol]
            if md.timestamp > cutoff_time
        ]
    
    def add_order_data(self, order_data: OrderData):
        """Add order data for analysis"""
        self.order_cache[order_data.order_id] = order_data
    
    def add_execution_data(self, execution_data: ExecutionData):
        """Add execution data for analysis"""
        self.execution_cache[execution_data.order_id].append(execution_data)
    
    async def analyze_order(self, order_id: str) -> Optional[TCAMetrics]:
        """Perform comprehensive TCA analysis for an order"""
        if order_id not in self.order_cache:
            logger.warning(f"Order data not found for {order_id}")
            return None
        
        if order_id not in self.execution_cache or not self.execution_cache[order_id]:
            logger.warning(f"No execution data found for {order_id}")
            return None
        
        order_data = self.order_cache[order_id]
        executions = self.execution_cache[order_id]
        
        # Calculate basic metrics
        total_quantity = sum(exec_data.quantity for exec_data in executions)
        total_value = sum(exec_data.quantity * exec_data.price for exec_data in executions)
        average_price = total_value / total_quantity if total_quantity > 0 else Decimal('0')
        total_commission = sum(exec_data.commission for exec_data in executions)
        total_fees = sum(exec_data.fees for exec_data in executions)
        
        # Calculate venue breakdown
        venue_breakdown = defaultdict(Decimal)
        for exec_data in executions:
            venue_breakdown[exec_data.venue] += exec_data.quantity
        
        # Convert to percentages
        venue_breakdown = {
            venue: (quantity / total_quantity * 100) if total_quantity > 0 else Decimal('0')
            for venue, quantity in venue_breakdown.items()
        }
        
        # Get benchmark prices
        benchmarks = await self._calculate_benchmarks(order_data, executions)
        
        # Calculate cost components
        cost_components = await self._calculate_cost_components(
            order_data, executions, average_price, benchmarks
        )
        
        # Calculate performance metrics
        performance_metrics = await self._calculate_performance_metrics(
            order_data, executions, average_price, benchmarks
        )
        
        # Calculate timing metrics
        timing_metrics = self._calculate_timing_metrics(order_data, executions)
        
        # Determine execution quality
        execution_quality = self._determine_execution_quality(cost_components, performance_metrics)
        
        # Create TCA metrics
        tca_metrics = TCAMetrics(
            order_id=order_id,
            symbol=order_data.symbol,
            side=order_data.side,
            total_quantity=total_quantity,
            average_price=average_price,
            total_commission=total_commission,
            total_fees=total_fees,
            arrival_price=benchmarks.get('arrival_price'),
            decision_price=benchmarks.get('decision_price'),
            vwap_benchmark=benchmarks.get('vwap'),
            twap_benchmark=benchmarks.get('twap'),
            spread_cost_bps=cost_components['spread_cost'],
            market_impact_bps=cost_components['market_impact'],
            timing_cost_bps=cost_components['timing_cost'],
            opportunity_cost_bps=cost_components['opportunity_cost'],
            commission_bps=cost_components['commission'],
            total_cost_bps=cost_components['total_cost'],
            price_improvement_bps=performance_metrics['price_improvement'],
            implementation_shortfall_bps=performance_metrics['implementation_shortfall'],
            execution_quality=execution_quality,
            execution_duration=timing_metrics['duration'],
            fill_rate=timing_metrics['fill_rate'],
            venue_breakdown=venue_breakdown
        )
        
        # Cache results
        self.tca_results[order_id] = tca_metrics
        
        logger.info(f"TCA analysis completed for order {order_id}")
        return tca_metrics
    
    async def _calculate_benchmarks(self, order_data: OrderData, executions: List[ExecutionData]) -> Dict[str, Decimal]:
        """Calculate benchmark prices"""
        benchmarks = {}
        symbol = order_data.symbol
        
        # Get market data for the symbol
        market_data = self.market_data_cache.get(symbol, [])
        if not market_data:
            logger.warning(f"No market data available for {symbol}")
            return benchmarks
        
        # Sort market data by timestamp
        market_data.sort(key=lambda x: x.timestamp)
        
        # Arrival price benchmark
        if order_data.arrival_time:
            arrival_md = self._get_market_data_at_time(market_data, order_data.arrival_time)
            if arrival_md:
                benchmarks['arrival_price'] = arrival_md.mid_price
        
        # Decision price benchmark
        if order_data.decision_time:
            decision_md = self._get_market_data_at_time(market_data, order_data.decision_time)
            if decision_md:
                benchmarks['decision_price'] = decision_md.mid_price
        
        # VWAP benchmark (simplified - would use actual market volume data)
        if executions:
            start_time = min(exec_data.timestamp for exec_data in executions)
            end_time = max(exec_data.timestamp for exec_data in executions)
            
            relevant_data = [
                md for md in market_data
                if start_time <= md.timestamp <= end_time
            ]
            
            if relevant_data:
                # Simplified VWAP calculation using mid prices
                total_volume = sum(md.volume or Decimal('1') for md in relevant_data)
                if total_volume > 0:
                    vwap = sum(
                        md.mid_price * (md.volume or Decimal('1'))
                        for md in relevant_data
                    ) / total_volume
                    benchmarks['vwap'] = vwap
                
                # TWAP calculation
                twap = sum(md.mid_price for md in relevant_data) / len(relevant_data)
                benchmarks['twap'] = twap
        
        return benchmarks
    
    def _get_market_data_at_time(self, market_data: List[MarketDataPoint], target_time: datetime) -> Optional[MarketDataPoint]:
        """Get market data closest to target time"""
        if not market_data:
            return None
        
        # Find closest market data point
        closest_md = min(
            market_data,
            key=lambda md: abs((md.timestamp - target_time).total_seconds())
        )
        
        # Only return if within reasonable time window (5 minutes)
        if abs((closest_md.timestamp - target_time).total_seconds()) <= 300:
            return closest_md
        
        return None
    
    async def _calculate_cost_components(self, order_data: OrderData, executions: List[ExecutionData], 
                                       average_price: Decimal, benchmarks: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Calculate various cost components in basis points"""
        costs = {
            'spread_cost': Decimal('0'),
            'market_impact': Decimal('0'),
            'timing_cost': Decimal('0'),
            'opportunity_cost': Decimal('0'),
            'commission': Decimal('0'),
            'total_cost': Decimal('0')
        }
        
        if not benchmarks or average_price == 0:
            return costs
        
        # Commission cost in basis points
        total_commission = sum(exec_data.commission for exec_data in executions)
        total_value = sum(exec_data.quantity * exec_data.price for exec_data in executions)
        if total_value > 0:
            costs['commission'] = (total_commission / total_value) * 10000
        
        # Spread cost (half spread for market orders)
        symbol = order_data.symbol
        market_data = self.market_data_cache.get(symbol, [])
        if market_data:
            # Get average spread during execution period
            execution_times = [exec_data.timestamp for exec_data in executions]
            if execution_times:
                start_time = min(execution_times)
                end_time = max(execution_times)
                
                relevant_data = [
                    md for md in market_data
                    if start_time <= md.timestamp <= end_time
                ]
                
                if relevant_data:
                    avg_spread_bps = sum(md.spread_bps for md in relevant_data) / len(relevant_data)
                    # For market orders, assume half spread cost
                    costs['spread_cost'] = avg_spread_bps / 2
        
        # Market impact (difference from arrival price)
        if 'arrival_price' in benchmarks:
            arrival_price = benchmarks['arrival_price']
            price_diff = average_price - arrival_price
            
            # Adjust sign based on order side
            if order_data.side == 'SELL':
                price_diff = -price_diff
            
            if arrival_price > 0:
                costs['market_impact'] = (price_diff / arrival_price) * 10000
        
        # Timing cost (difference between decision and arrival)
        if 'decision_price' in benchmarks and 'arrival_price' in benchmarks:
            decision_price = benchmarks['decision_price']
            arrival_price = benchmarks['arrival_price']
            timing_diff = arrival_price - decision_price
            
            # Adjust sign based on order side
            if order_data.side == 'SELL':
                timing_diff = -timing_diff
            
            if decision_price > 0:
                costs['timing_cost'] = (timing_diff / decision_price) * 10000
        
        # Total cost
        costs['total_cost'] = (
            costs['spread_cost'] + 
            costs['market_impact'] + 
            costs['timing_cost'] + 
            costs['commission']
        )
        
        return costs
    
    async def _calculate_performance_metrics(self, order_data: OrderData, executions: List[ExecutionData],
                                           average_price: Decimal, benchmarks: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Calculate performance metrics"""
        metrics = {
            'price_improvement': Decimal('0'),
            'implementation_shortfall': Decimal('0')
        }
        
        if not benchmarks or average_price == 0:
            return metrics
        
        # Price improvement vs VWAP
        if 'vwap' in benchmarks:
            vwap = benchmarks['vwap']
            price_diff = average_price - vwap
            
            # Adjust sign based on order side (better execution = positive improvement)
            if order_data.side == 'BUY':
                price_diff = -price_diff  # Lower price is better for buy
            
            if vwap > 0:
                metrics['price_improvement'] = (price_diff / vwap) * 10000
        
        # Implementation Shortfall
        if 'decision_price' in benchmarks:
            decision_price = benchmarks['decision_price']
            
            # Calculate total cost including opportunity cost
            total_quantity = order_data.original_quantity
            executed_quantity = sum(exec_data.quantity for exec_data in executions)
            
            # Executed portion cost
            executed_cost = Decimal('0')
            if executed_quantity > 0 and decision_price > 0:
                price_diff = average_price - decision_price
                if order_data.side == 'SELL':
                    price_diff = -price_diff
                executed_cost = (price_diff / decision_price) * 10000
            
            # Opportunity cost for unexecuted portion
            opportunity_cost = Decimal('0')
            unexecuted_quantity = total_quantity - executed_quantity
            if unexecuted_quantity > 0:
                # Simplified opportunity cost calculation
                opportunity_cost = Decimal('50')  # 50 bps penalty for non-execution
            
            # Weighted implementation shortfall
            if total_quantity > 0:
                executed_weight = executed_quantity / total_quantity
                unexecuted_weight = unexecuted_quantity / total_quantity
                
                metrics['implementation_shortfall'] = (
                    executed_cost * executed_weight + 
                    opportunity_cost * unexecuted_weight
                )
        
        return metrics
    
    def _calculate_timing_metrics(self, order_data: OrderData, executions: List[ExecutionData]) -> Dict[str, Any]:
        """Calculate timing-related metrics"""
        metrics = {
            'duration': None,
            'fill_rate': Decimal('1.0')
        }
        
        # Execution duration
        if order_data.arrival_time and executions:
            last_execution = max(executions, key=lambda x: x.timestamp)
            metrics['duration'] = last_execution.timestamp - order_data.arrival_time
        
        # Fill rate
        executed_quantity = sum(exec_data.quantity for exec_data in executions)
        if order_data.original_quantity > 0:
            metrics['fill_rate'] = executed_quantity / order_data.original_quantity
        
        return metrics
    
    def _determine_execution_quality(self, cost_components: Dict[str, Decimal], 
                                   performance_metrics: Dict[str, Decimal]) -> ExecutionQuality:
        """Determine overall execution quality rating"""
        total_cost = cost_components.get('total_cost', Decimal('0'))
        price_improvement = performance_metrics.get('price_improvement', Decimal('0'))
        
        # Simple quality scoring based on total cost and price improvement
        net_performance = price_improvement - total_cost
        
        if net_performance >= 10:  # 10+ bps net positive
            return ExecutionQuality.EXCELLENT
        elif net_performance >= 0:  # 0-10 bps net positive
            return ExecutionQuality.GOOD
        elif net_performance >= -10:  # 0-10 bps net negative
            return ExecutionQuality.FAIR
        elif net_performance >= -25:  # 10-25 bps net negative
            return ExecutionQuality.POOR
        else:  # >25 bps net negative
            return ExecutionQuality.VERY_POOR
    
    def get_tca_results(self, order_id: str) -> Optional[TCAMetrics]:
        """Get TCA results for an order"""
        return self.tca_results.get(order_id)
    
    def get_aggregate_statistics(self, symbol: Optional[str] = None, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get aggregate TCA statistics"""
        # Filter results based on criteria
        filtered_results = []
        for tca_result in self.tca_results.values():
            if symbol and tca_result.symbol != symbol:
                continue
            # Add date filtering logic here if needed
            filtered_results.append(tca_result)
        
        if not filtered_results:
            return {}
        
        # Calculate aggregate statistics
        total_cost_bps = [result.total_cost_bps for result in filtered_results]
        market_impact_bps = [result.market_impact_bps for result in filtered_results]
        price_improvement_bps = [result.price_improvement_bps for result in filtered_results]
        
        # Quality distribution
        quality_counts = defaultdict(int)
        for result in filtered_results:
            quality_counts[result.execution_quality.value] += 1
        
        # Venue analysis
        venue_stats = defaultdict(list)
        for result in filtered_results:
            for venue, percentage in result.venue_breakdown.items():
                venue_stats[venue].append(percentage)
        
        return {
            'total_orders_analyzed': len(filtered_results),
            'average_total_cost_bps': statistics.mean(total_cost_bps) if total_cost_bps else 0,
            'median_total_cost_bps': statistics.median(total_cost_bps) if total_cost_bps else 0,
            'average_market_impact_bps': statistics.mean(market_impact_bps) if market_impact_bps else 0,
            'average_price_improvement_bps': statistics.mean(price_improvement_bps) if price_improvement_bps else 0,
            'quality_distribution': dict(quality_counts),
            'venue_usage': {
                venue: {
                    'average_percentage': statistics.mean(percentages) if percentages else 0,
                    'orders_count': len(percentages)
                }
                for venue, percentages in venue_stats.items()
            }
        }
    
    def export_tca_report(self, order_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export comprehensive TCA report"""
        if order_ids:
            results = {oid: self.tca_results[oid] for oid in order_ids if oid in self.tca_results}
        else:
            results = self.tca_results
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_orders': len(results),
            'individual_results': {
                order_id: tca_metrics.to_dict()
                for order_id, tca_metrics in results.items()
            },
            'aggregate_statistics': self.get_aggregate_statistics()
        }
        
        return report

async def main():
    """Example usage of TCA system"""
    tca = TransactionCostAnalyzer()
    
    # Add sample market data
    market_data = MarketDataPoint(
        timestamp=datetime.now(),
        symbol='EURUSD',
        bid_price=Decimal('1.0999'),
        ask_price=Decimal('1.1001'),
        mid_price=Decimal('1.1000'),
        volume=Decimal('1000000')
    )
    tca.add_market_data(market_data)
    
    # Add sample order data
    order_data = OrderData(
        order_id='TEST_001',
        symbol='EURUSD',
        side='BUY',
        original_quantity=Decimal('100000'),
        order_type='MARKET',
        arrival_time=datetime.now() - timedelta(minutes=5),
        decision_time=datetime.now() - timedelta(minutes=6)
    )
    tca.add_order_data(order_data)
    
    # Add sample execution data
    execution_data = ExecutionData(
        execution_id='EXEC_001',
        order_id='TEST_001',
        timestamp=datetime.now(),
        symbol='EURUSD',
        side='BUY',
        quantity=Decimal('100000'),
        price=Decimal('1.1002'),
        venue='ECN_PRIMARY',
        commission=Decimal('20.0')
    )
    tca.add_execution_data(execution_data)
    
    # Perform TCA analysis
    tca_result = await tca.analyze_order('TEST_001')
    
    if tca_result:
        print("TCA Analysis Results:")
        print(f"Order ID: {tca_result.order_id}")
        print(f"Total Cost: {tca_result.total_cost_bps:.2f} bps")
        print(f"Market Impact: {tca_result.market_impact_bps:.2f} bps")
        print(f"Execution Quality: {tca_result.execution_quality.value}")
        print(f"Price Improvement: {tca_result.price_improvement_bps:.2f} bps")
        
        # Export report
        report = tca.export_tca_report(['TEST_001'])
        print(f"\\nFull Report: {json.dumps(report, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(main())