#!/usr/bin/env python3
"""
Custom Trading Metrics Exporter for Prometheus

This service exposes trading-specific metrics that are not available
from standard Prometheus exporters.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import psycopg2
import redis
from prometheus_client import (
    start_http_server, 
    Gauge, 
    Counter, 
    Histogram, 
    Info,
    CollectorRegistry,
    generate_latest
)
from flask import Flask, Response
import json
import os
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TradingMetrics:
    """Data class for trading metrics"""
    portfolio_value: float = 0.0
    daily_pnl: float = 0.0
    total_positions: int = 0
    active_orders: int = 0
    executed_trades_today: int = 0
    avg_execution_latency: float = 0.0
    risk_utilization: float = 0.0
    strategy_count: int = 0
    market_data_lag: float = 0.0
    system_health_score: float = 100.0

class TradingMetricsExporter:
    """Custom metrics exporter for trading system"""
    
    def __init__(self):
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # Database connections
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', 5432),
            'database': os.getenv('POSTGRES_DB', 'trading_db'),
            'user': os.getenv('POSTGRES_USER', 'trading_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'trading_pass')
        }
        
        # Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        
        # Initialize Prometheus metrics
        self._init_metrics()
        
        # Flask app for HTTP endpoint
        self.app = Flask(__name__)
        self._setup_routes()
        
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        
        # Portfolio Metrics
        self.portfolio_value = Gauge(
            'trading_portfolio_value_usd',
            'Current portfolio value in USD',
            registry=self.registry
        )
        
        self.daily_pnl = Gauge(
            'trading_daily_pnl_usd',
            'Daily profit and loss in USD',
            registry=self.registry
        )
        
        self.portfolio_positions = Gauge(
            'trading_portfolio_positions_total',
            'Total number of open positions',
            registry=self.registry
        )
        
        # Order Metrics
        self.active_orders = Gauge(
            'trading_active_orders_total',
            'Number of active orders',
            registry=self.registry
        )
        
        self.executed_trades = Counter(
            'trading_executed_trades_total',
            'Total number of executed trades',
            ['strategy', 'symbol', 'side'],
            registry=self.registry
        )
        
        self.order_execution_latency = Histogram(
            'trading_order_execution_latency_seconds',
            'Order execution latency in seconds',
            ['order_type'],
            registry=self.registry
        )
        
        # Risk Metrics
        self.risk_utilization = Gauge(
            'trading_risk_utilization_ratio',
            'Current risk utilization as ratio of maximum allowed',
            registry=self.registry
        )
        
        self.var_1d = Gauge(
            'trading_var_1d_usd',
            'Value at Risk (1 day) in USD',
            registry=self.registry
        )
        
        self.max_drawdown = Gauge(
            'trading_max_drawdown_ratio',
            'Maximum drawdown as ratio',
            registry=self.registry
        )
        
        # Strategy Metrics
        self.active_strategies = Gauge(
            'trading_active_strategies_total',
            'Number of active trading strategies',
            registry=self.registry
        )
        
        self.strategy_performance = Gauge(
            'trading_strategy_performance_ratio',
            'Strategy performance ratio',
            ['strategy_name'],
            registry=self.registry
        )
        
        # Market Data Metrics
        self.market_data_lag = Gauge(
            'trading_market_data_lag_seconds',
            'Market data lag in seconds',
            ['feed_source'],
            registry=self.registry
        )
        
        self.market_data_errors = Counter(
            'trading_market_data_errors_total',
            'Total market data errors',
            ['feed_source', 'error_type'],
            registry=self.registry
        )
        
        # System Health Metrics
        self.system_health_score = Gauge(
            'trading_system_health_score',
            'Overall system health score (0-100)',
            registry=self.registry
        )
        
        self.component_status = Gauge(
            'trading_component_status',
            'Component status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
        # AI/ML Metrics
        self.model_accuracy = Gauge(
            'trading_model_accuracy_ratio',
            'ML model accuracy ratio',
            ['model_name'],
            registry=self.registry
        )
        
        self.prediction_confidence = Gauge(
            'trading_prediction_confidence_ratio',
            'Average prediction confidence',
            ['model_name'],
            registry=self.registry
        )
        
        # Custom Business Metrics
        self.sharpe_ratio = Gauge(
            'trading_sharpe_ratio',
            'Current Sharpe ratio',
            registry=self.registry
        )
        
        self.win_rate = Gauge(
            'trading_win_rate_ratio',
            'Win rate ratio',
            registry=self.registry
        )
        
        self.avg_trade_duration = Gauge(
            'trading_avg_trade_duration_minutes',
            'Average trade duration in minutes',
            registry=self.registry
        )
        
        # System Info
        self.system_info = Info(
            'trading_system_info',
            'Trading system information',
            registry=self.registry
        )
        
        # Set system info
        self.system_info.info({
            'version': '1.0.0',
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'build_date': datetime.now().isoformat(),
            'components': 'trading_engine,portfolio_manager,risk_manager'
        })
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def collect_portfolio_metrics(self) -> Dict[str, Any]:
        """Collect portfolio-related metrics"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Portfolio value
                cursor.execute("""
                    SELECT SUM(market_value) as total_value
                    FROM portfolio_positions 
                    WHERE is_active = true
                """)
                portfolio_value = cursor.fetchone()[0] or 0.0
                
                # Daily P&L
                cursor.execute("""
                    SELECT SUM(unrealized_pnl + realized_pnl) as daily_pnl
                    FROM portfolio_positions 
                    WHERE DATE(updated_at) = CURRENT_DATE
                """)
                daily_pnl = cursor.fetchone()[0] or 0.0
                
                # Position count
                cursor.execute("""
                    SELECT COUNT(*) as position_count
                    FROM portfolio_positions 
                    WHERE is_active = true AND quantity != 0
                """)
                position_count = cursor.fetchone()[0] or 0
                
                return {
                    'portfolio_value': portfolio_value,
                    'daily_pnl': daily_pnl,
                    'position_count': position_count
                }
                
        except Exception as e:
            logger.error(f"Error collecting portfolio metrics: {e}")
            return {'portfolio_value': 0.0, 'daily_pnl': 0.0, 'position_count': 0}
    
    def collect_order_metrics(self) -> Dict[str, Any]:
        """Collect order-related metrics"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Active orders
                cursor.execute("""
                    SELECT COUNT(*) as active_orders
                    FROM orders 
                    WHERE status IN ('PENDING', 'PARTIALLY_FILLED')
                """)
                active_orders = cursor.fetchone()[0] or 0
                
                # Executed trades today
                cursor.execute("""
                    SELECT COUNT(*) as executed_today
                    FROM orders 
                    WHERE status = 'FILLED' AND DATE(filled_at) = CURRENT_DATE
                """)
                executed_today = cursor.fetchone()[0] or 0
                
                # Average execution latency
                cursor.execute("""
                    SELECT AVG(EXTRACT(EPOCH FROM (filled_at - created_at))) as avg_latency
                    FROM orders 
                    WHERE status = 'FILLED' AND DATE(filled_at) = CURRENT_DATE
                """)
                avg_latency = cursor.fetchone()[0] or 0.0
                
                return {
                    'active_orders': active_orders,
                    'executed_today': executed_today,
                    'avg_latency': avg_latency
                }
                
        except Exception as e:
            logger.error(f"Error collecting order metrics: {e}")
            return {'active_orders': 0, 'executed_today': 0, 'avg_latency': 0.0}
    
    def collect_risk_metrics(self) -> Dict[str, Any]:
        """Collect risk-related metrics"""
        try:
            # Get risk metrics from Redis cache
            risk_data = self.redis_client.hgetall('risk_metrics')
            
            return {
                'risk_utilization': float(risk_data.get('risk_utilization', 0.0)),
                'var_1d': float(risk_data.get('var_1d', 0.0)),
                'max_drawdown': float(risk_data.get('max_drawdown', 0.0))
            }
            
        except Exception as e:
            logger.error(f"Error collecting risk metrics: {e}")
            return {'risk_utilization': 0.0, 'var_1d': 0.0, 'max_drawdown': 0.0}
    
    def collect_system_health(self) -> Dict[str, Any]:
        """Collect system health metrics"""
        try:
            # Check component health from Redis
            components = ['trading_engine', 'portfolio_manager', 'risk_manager', 'market_data']
            health_scores = []
            
            for component in components:
                health_key = f'health:{component}'
                health_data = self.redis_client.hgetall(health_key)
                
                if health_data:
                    status = int(health_data.get('status', 0))
                    self.component_status.labels(component=component).set(status)
                    health_scores.append(status * 100)
                else:
                    self.component_status.labels(component=component).set(0)
                    health_scores.append(0)
            
            # Calculate overall health score
            overall_health = sum(health_scores) / len(health_scores) if health_scores else 0
            
            return {'system_health_score': overall_health}
            
        except Exception as e:
            logger.error(f"Error collecting system health: {e}")
            return {'system_health_score': 0.0}
    
    def update_metrics(self):
        """Update all metrics"""
        try:
            # Collect all metrics
            portfolio_metrics = self.collect_portfolio_metrics()
            order_metrics = self.collect_order_metrics()
            risk_metrics = self.collect_risk_metrics()
            health_metrics = self.collect_system_health()
            
            # Update Prometheus metrics
            self.portfolio_value.set(portfolio_metrics['portfolio_value'])
            self.daily_pnl.set(portfolio_metrics['daily_pnl'])
            self.portfolio_positions.set(portfolio_metrics['position_count'])
            
            self.active_orders.set(order_metrics['active_orders'])
            
            self.risk_utilization.set(risk_metrics['risk_utilization'])
            self.var_1d.set(risk_metrics['var_1d'])
            self.max_drawdown.set(risk_metrics['max_drawdown'])
            
            self.system_health_score.set(health_metrics['system_health_score'])
            
            logger.info("Metrics updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/metrics')
        def metrics():
            """Prometheus metrics endpoint"""
            self.update_metrics()
            return Response(
                generate_latest(self.registry),
                mimetype='text/plain; version=0.0.4; charset=utf-8'
            )
        
        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        
        @self.app.route('/trading/metrics')
        def trading_metrics():
            """Custom trading metrics endpoint"""
            self.update_metrics()
            return Response(
                generate_latest(self.registry),
                mimetype='text/plain; version=0.0.4; charset=utf-8'
            )
    
    def run(self, host='0.0.0.0', port=9090):
        """Run the metrics exporter"""
        logger.info(f"Starting Trading Metrics Exporter on {host}:{port}")
        self.app.run(host=host, port=port, debug=False)

def main():
    """Main function"""
    exporter = TradingMetricsExporter()
    
    # Start background metrics collection
    async def metrics_loop():
        while True:
            try:
                exporter.update_metrics()
                await asyncio.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    # Run the exporter
    exporter.run()

if __name__ == '__main__':
    main()