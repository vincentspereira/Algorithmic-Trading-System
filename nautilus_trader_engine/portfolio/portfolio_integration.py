"""
Portfolio Integration System
Integration between portfolio optimization, observability, and Nautilus Trader portfolio system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from nautilus_trader.portfolio.portfolio import Portfolio
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import Logger
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.core.message import Event

# Import our portfolio modules
from portfolio_optimization import (
    PortfolioOptimizer, 
    NautilusPortfolioOptimizer, 
    PortfolioOptimizationConfig,
    OptimizationMethod,
    RiskMeasure,
    OptimizationResult
)
from portfolio_observability import (
    PortfolioObservability, 
    PortfolioAlertManager,
    PortfolioMetrics,
    RiskMetrics
)

# Import monitoring system
try:
    from nautilus_trader_engine.monitoring.metrics_collection import MetricsCollectionSystem
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logging.warning("Monitoring system not available")
    # Define placeholder class for when monitoring is not available
    class MetricsCollectionSystem:
        pass


class IntegratedPortfolioSystem:
    """
    Integrated portfolio management system that combines optimization, 
    observability, and Nautilus Trader portfolio functionality.
    """
    
    def __init__(self, 
                 portfolio: Portfolio, 
                 cache: Cache,
                 metrics_system: MetricsCollectionSystem = None,
                 optimization_config: PortfolioOptimizationConfig = None):
        self.portfolio = portfolio
        self.cache = cache
        self.metrics_system = metrics_system
        self.optimization_config = optimization_config or PortfolioOptimizationConfig()
        
        self.logger = Logger(name=type(self).__name__)
        
        # Initialize subsystems
        self.optimizer = NautilusPortfolioOptimizer(
            portfolio=portfolio,
            cache=cache,
            config=self.optimization_config
        )
        
        self.observability = PortfolioObservability(
            portfolio=portfolio,
            metrics_system=metrics_system
        )
        
        self.alert_manager = PortfolioAlertManager(self.observability)
        
        # System state
        self._is_running = False
        self._last_optimization = None
        self._optimization_frequency = timedelta(hours=24)  # Daily optimization
        self._market_data_buffer = {}
        
        # Register for portfolio events
        self._register_event_handlers()
        
    def _register_event_handlers(self):
        """Register handlers for portfolio events"""
        # In a real implementation, this would register with the message bus
        # For now, we'll just log that we're setting up event handling
        self.logger.info("Registered for portfolio event handling")
        
    async def start(self):
        """Start the integrated portfolio system"""
        if self._is_running:
            self.logger.warning("Integrated portfolio system already running")
            return
            
        self._is_running = True
        
        # Start observability system
        await self.observability.start()
        
        # Start alert manager
        await self.alert_manager.start_monitoring()
        
        # Set up alert rules
        self._setup_alert_rules()
        
        # Start periodic tasks
        self._start_periodic_tasks()
        
        self.logger.info("Integrated portfolio system started")
        
    async def stop(self):
        """Stop the integrated portfolio system"""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # Stop subsystems
        await self.observability.stop()
        await self.alert_manager.stop_monitoring()
        
        self.logger.info("Integrated portfolio system stopped")
        
    def _setup_alert_rules(self):
        """Set up default alert rules"""
        # High volatility alert
        self.alert_manager.add_alert_rule(
            name="high_volatility",
            condition=lambda metrics: metrics.volatility > 0.25,
            message="Portfolio volatility exceeded 25%",
            severity="warning"
        )
        
        # Large drawdown alert
        self.alert_manager.add_alert_rule(
            name="large_drawdown",
            condition=lambda metrics: metrics.max_drawdown > 0.10,
            message="Portfolio drawdown exceeded 10%",
            severity="critical"
        )
        
        # Low Sharpe ratio alert
        self.alert_manager.add_alert_rule(
            name="low_sharpe_ratio",
            condition=lambda metrics: metrics.sharpe_ratio < 0.5,
            message="Portfolio Sharpe ratio fell below 0.5",
            severity="warning"
        )
        
        # High turnover alert
        self.alert_manager.add_alert_rule(
            name="high_turnover",
            condition=lambda metrics: metrics.turnover > 0.10,
            message="Portfolio turnover exceeded 10%",
            severity="warning"
        )
        
    def _start_periodic_tasks(self):
        """Start periodic system tasks"""
        # This would typically use asyncio.create_task() to run periodic functions
        # For now, we'll just log that we're setting up periodic tasks
        self.logger.info("Set up periodic portfolio monitoring tasks")
        
    async def optimize_portfolio(self, 
                               market_data: pd.DataFrame,
                               market_caps: Optional[pd.Series] = None,
                               views: Optional[Dict[str, float]] = None,
                               confidence: Optional[pd.DataFrame] = None) -> OptimizationResult:
        """
        Optimize the portfolio using current market data.
        
        Parameters
        ----------
        market_data : pd.DataFrame
            Market data for optimization (prices or returns)
        market_caps : pd.Series, optional
            Market capitalization data for Black-Litterman model
        views : Dict[str, float], optional
            Investor views for Black-Litterman model
        confidence : pd.DataFrame, optional
            Confidence matrix for views
            
        Returns
        -------
        OptimizationResult
            The optimization results
        """
        try:
            self.logger.info("Starting portfolio optimization...")
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.optimizer.optimize_current_portfolio,
                market_data,
                market_caps,
                views,
                confidence
            )
            
            self._last_optimization = datetime.now()
            
            # Generate rebalancing signals
            signals = self.optimizer.generate_rebalancing_signals(result)
            if signals:
                self.logger.info(f"Generated {len(signals)} rebalancing signals")
                for signal in signals[:5]:  # Log first 5 signals
                    self.logger.info(f"  {signal['asset']}: {signal['action']} "
                                   f"(target: {signal['target_weight']:.2%})")
            
            # Add alert for significant changes
            if result.turnover and result.turnover > 0.05:
                self.observability.add_alert(
                    "high_turnover_optimization",
                    f"Portfolio optimization resulted in {result.turnover:.1%} turnover",
                    "warning"
                )
                
            self.logger.info(f"Portfolio optimization completed - "
                           f"Expected Return: {result.expected_return:.2%}, "
                           f"Risk: {result.risk:.2%}, "
                           f"Sharpe: {result.sharpe_ratio:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Portfolio optimization failed: {e}")
            raise
            
    async def collect_market_data(self, 
                                instrument_ids: List[InstrumentId],
                                lookback_period: int = 252) -> pd.DataFrame:
        """
        Collect market data for portfolio optimization.
        
        Parameters
        ----------
        instrument_ids : List[InstrumentId]
            List of instrument IDs to collect data for
        lookback_period : int
            Number of days of historical data to collect
            
        Returns
        -------
        pd.DataFrame
            Market data for optimization
        """
        try:
            # In a real implementation, this would fetch data from the cache
            # or external data sources
            self.logger.info(f"Collecting market data for {len(instrument_ids)} instruments")
            
            # For this example, we'll create mock data
            dates = pd.date_range(
                end=datetime.now(), 
                periods=lookback_period, 
                freq='D'
            )
            
            data = {}
            for instrument_id in instrument_ids:
                # Generate mock returns
                np.random.seed(hash(str(instrument_id)) % (2**32))
                returns = np.random.randn(lookback_period) * 0.02
                data[str(instrument_id)] = returns
                
            df = pd.DataFrame(data, index=dates)
            self._market_data_buffer = df.copy()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to collect market data: {e}")
            raise
            
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive portfolio summary.
        
        Returns
        -------
        Dict[str, Any]
            Portfolio summary including performance, risk, and optimization metrics
        """
        try:
            # Get current metrics
            current_metrics = self.observability._calculate_portfolio_metrics()
            
            # Get risk metrics
            # In a real implementation, this would use actual return data
            risk_metrics = self.observability.calculate_risk_metrics()
            
            # Get optimization history
            optimization_history = self.optimizer.optimizer.get_optimization_history()
            
            summary = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_value": current_metrics.total_value,
                "performance": {
                    "total_pnl": current_metrics.total_pnl,
                    "total_pnl_percentage": (current_metrics.total_pnl / 
                                           (current_metrics.total_value - current_metrics.total_pnl)) * 100,
                    "realized_pnl": current_metrics.realized_pnl,
                    "unrealized_pnl": current_metrics.unrealized_pnl,
                    "sharpe_ratio": current_metrics.sharpe_ratio,
                    "volatility": current_metrics.volatility,
                    "max_drawdown": current_metrics.max_drawdown
                },
                "risk_metrics": {
                    "value_at_risk_95": risk_metrics.value_at_risk,
                    "conditional_var_99": risk_metrics.conditional_var,
                    "max_drawdown": risk_metrics.max_drawdown,
                    "beta": risk_metrics.beta
                },
                "optimization": {
                    "last_optimization": self._last_optimization.isoformat() if self._last_optimization else None,
                    "optimization_count": len(optimization_history),
                    "latest_optimization": optimization_history[-1] if optimization_history else None
                },
                "diversification": {
                    "effective_assets": current_metrics.effective_assets,
                    "diversification_ratio": current_metrics.diversification_ratio
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate portfolio summary: {e}")
            return {"error": str(e)}
            
    async def generate_portfolio_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive portfolio report.
        
        Returns
        -------
        Dict[str, Any]
            Detailed portfolio report
        """
        try:
            self.logger.info("Generating comprehensive portfolio report...")
            
            # Get observability report
            report = self.observability.generate_portfolio_report()
            
            # Add optimization information
            optimization_history = self.optimizer.optimizer.get_optimization_history()
            report["optimization_history"] = [
                {
                    "timestamp": opt.timestamp.isoformat(),
                    "method": opt.method,
                    "risk_measure": opt.risk_measure,
                    "expected_return": opt.expected_return,
                    "risk": opt.risk,
                    "sharpe_ratio": opt.sharpe_ratio,
                    "turnover": opt.turnover
                }
                for opt in optimization_history[-10:]  # Last 10 optimizations
            ]
            
            # Add current positions (mock data for now)
            report["current_positions"] = {
                "AAPL": {"weight": 0.25, "value": 250000},
                "GOOGL": {"weight": 0.20, "value": 200000},
                "MSFT": {"weight": 0.15, "value": 150000},
                "AMZN": {"weight": 0.15, "value": 150000},
                "TSLA": {"weight": 0.10, "value": 100000},
                "Other": {"weight": 0.15, "value": 150000}
            }
            
            self.logger.info("Portfolio report generated successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate portfolio report: {e}")
            raise
            
    def get_instrument_exposure(self, instrument_id: InstrumentId) -> Dict[str, Any]:
        """
        Get exposure metrics for a specific instrument.
        
        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument to get exposure for
            
        Returns
        -------
        Dict[str, Any]
            Exposure metrics for the instrument
        """
        try:
            # In a real implementation, this would query the actual portfolio
            # For now, we'll return mock data
            exposure_data = {
                "instrument_id": str(instrument_id),
                "position_size": 1000,  # Mock position size
                "position_value": 150000,  # Mock position value
                "weight": 0.15,  # 15% of portfolio
                "unrealized_pnl": 5000,  # Mock P&L
                "risk_contribution": 0.12,  # Mock risk contribution
                "last_updated": datetime.now().isoformat()
            }
            
            return exposure_data
            
        except Exception as e:
            self.logger.error(f"Failed to get instrument exposure for {instrument_id}: {e}")
            return {"error": str(e)}
            
    async def rebalance_portfolio(self, target_weights: Dict[str, float]):
        """
        Rebalance the portfolio to target weights.
        
        Parameters
        ----------
        target_weights : Dict[str, float]
            Target weights for portfolio assets
        """
        try:
            self.logger.info("Initiating portfolio rebalancing...")
            
            # In a real implementation, this would:
            # 1. Calculate required trades
            # 2. Check risk limits
            # 3. Generate trade orders
            # 4. Execute trades through the trading system
            
            current_weights = self.get_portfolio_summary()["current_positions"]
            
            trades_needed = []
            for asset, target_weight in target_weights.items():
                current_weight = current_weights.get(asset, {}).get("weight", 0)
                weight_diff = target_weight - current_weight
                
                if abs(weight_diff) > 0.01:  # 1% threshold
                    trades_needed.append({
                        "asset": asset,
                        "current_weight": current_weight,
                        "target_weight": target_weight,
                        "weight_difference": weight_diff,
                        "action": "BUY" if weight_diff > 0 else "SELL"
                    })
                    
            if trades_needed:
                self.logger.info(f"Rebalancing requires {len(trades_needed)} trades:")
                for trade in trades_needed:
                    self.logger.info(f"  {trade['asset']}: {trade['action']} "
                                   f"({trade['weight_difference']:.1%})")
                    
                # Add alert for rebalancing
                self.observability.add_alert(
                    "portfolio_rebalancing",
                    f"Portfolio rebalancing initiated with {len(trades_needed)} trades",
                    "info"
                )
            else:
                self.logger.info("No significant rebalancing needed")
                
        except Exception as e:
            self.logger.error(f"Portfolio rebalancing failed: {e}")
            raise


# Example usage and testing
async def example_usage():
    """Example usage of the integrated portfolio system"""
    
    # Create mock Nautilus Trader components
    class MockPortfolio:
        def __init__(self):
            pass
            
    class MockCache:
        def __init__(self):
            pass
            
    portfolio = MockPortfolio()
    cache = MockCache()
    
    # Create metrics system if available
    if MONITORING_AVAILABLE:
        metrics_system = MetricsCollectionSystem()
        await metrics_system.start()
    else:
        metrics_system = None
        
    # Create integrated system
    config = PortfolioOptimizationConfig(
        method=OptimizationMethod.MAXIMUM_SHARPE,
        risk_free_rate=0.02,
        allow_short=False
    )
    
    integrated_system = IntegratedPortfolioSystem(
        portfolio=portfolio,
        cache=cache,
        metrics_system=metrics_system,
        optimization_config=config
    )
    
    print("Starting integrated portfolio system...")
    await integrated_system.start()
    
    # Collect market data
    print("Collecting market data...")
    instrument_ids = [
        InstrumentId.from_str("AAPL.NASDAQ"),
        InstrumentId.from_str("GOOGL.NASDAQ"),
        InstrumentId.from_str("MSFT.NASDAQ")
    ]
    
    market_data = await integrated_system.collect_market_data(instrument_ids, lookback_period=30)
    print(f"Collected market data for {len(market_data.columns)} assets")
    
    # Optimize portfolio
    print("Optimizing portfolio...")
    optimization_result = await integrated_system.optimize_portfolio(market_data)
    print(f"Optimization completed - Sharpe Ratio: {optimization_result.sharpe_ratio:.2f}")
    
    # Get portfolio summary
    print("Generating portfolio summary...")
    summary = integrated_system.get_portfolio_summary()
    print(f"Portfolio Value: ${summary['portfolio_value']:,.2f}")
    print(f"Sharpe Ratio: {summary['performance']['sharpe_ratio']:.2f}")
    
    # Generate detailed report
    print("Generating detailed portfolio report...")
    report = await integrated_system.generate_portfolio_report()
    print(f"Report generated with {len(report.get('performance_attribution', {}).get('asset_contributions', {}))} asset contributions")
    
    # Get instrument exposure
    exposure = integrated_system.get_instrument_exposure(InstrumentId.from_str("AAPL.NASDAQ"))
    print(f"AAPL Exposure: {exposure.get('weight', 0):.1%} of portfolio")
    
    # Rebalance portfolio
    target_weights = {
        "AAPL": 0.30,
        "GOOGL": 0.25,
        "MSFT": 0.20,
        "AMZN": 0.15,
        "TSLA": 0.10
    }
    await integrated_system.rebalance_portfolio(target_weights)
    
    # Stop the system
    print("Stopping integrated portfolio system...")
    await integrated_system.stop()
    
    if metrics_system:
        await metrics_system.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())