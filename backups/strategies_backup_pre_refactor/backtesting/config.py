"""Backtesting Configuration

Configuration classes for backtesting framework with comprehensive settings
for simulation parameters, risk controls, and analysis options.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ...indicators.consolidated_indicators import ConsolidatedIndicators



class BacktestMode(Enum):
    """Backtesting modes"""
    VECTORIZED = "vectorized"  # Fast vectorized backtesting
    EVENT_DRIVEN = "event_driven"  # Event-driven simulation
    MONTE_CARLO = "monte_carlo"  # Monte Carlo simulation
    WALK_FORWARD = "walk_forward"  # Walk-forward analysis


class RebalanceFrequency(Enum):
    """Portfolio rebalancing frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class BenchmarkType(Enum):
    """Benchmark types for comparison"""
    SPY = "SPY"  # S&P 500
    QQQ = "QQQ"  # NASDAQ 100
    IWM = "IWM"  # Russell 2000
    VTI = "VTI"  # Total Stock Market
    CUSTOM = "custom"  # Custom benchmark
    RISK_FREE = "risk_free"  # Risk-free rate


@dataclass
class TransactionCosts:
    """Transaction cost configuration"""
    commission_per_share: float = 0.005  # Commission per share
    commission_min: float = 1.0  # Minimum commission
    commission_max: float = 0.5  # Maximum commission as % of trade value
    bid_ask_spread: float = 0.001  # Bid-ask spread as % of price
    market_impact: float = 0.0005  # Market impact as % of trade value
    slippage: float = 0.0001  # Slippage as % of price
    
    # Advanced cost modeling
    volume_impact_factor: float = 0.1  # Volume impact scaling
    volatility_impact_factor: float = 0.05  # Volatility impact scaling
    time_of_day_impact: Dict[str, float] = field(default_factory=lambda: {
        'market_open': 1.5,  # Higher costs at market open
        'market_close': 1.3,  # Higher costs at market close
        'midday': 1.0  # Normal costs during midday
    })


@dataclass
class RiskLimits:
    """Risk management limits"""
    max_position_size: float = 0.1  # Maximum position size as % of portfolio
    max_sector_exposure: float = 0.3  # Maximum sector exposure
    max_drawdown: float = 0.2  # Maximum allowed drawdown
    var_limit: float = 0.05  # VaR limit (95% confidence)
    leverage_limit: float = 1.0  # Maximum leverage
    
    # Concentration limits
    max_single_stock: float = 0.05  # Maximum single stock weight
    max_correlation: float = 0.8  # Maximum correlation between positions
    
    # Dynamic risk controls
    volatility_target: Optional[float] = None  # Target portfolio volatility
    risk_budget: Optional[float] = None  # Risk budget allocation
    max_portfolio_loss: float = 0.15  # Maximum portfolio loss threshold


@dataclass
class BacktestConfig:
    """Comprehensive backtesting configuration"""
    
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Initial conditions
    initial_capital: float = 100000.0
    currency: str = "USD"
    
    # Backtesting mode and frequency
    mode: BacktestMode = BacktestMode.EVENT_DRIVEN
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.DAILY
    
    # Data configuration
    data_frequency: str = "1D"  # Data frequency (1D, 1H, 15T, etc.)
    warmup_period: int = 252  # Warmup period in bars
    
    # Transaction costs and market simulation
    transaction_costs: TransactionCosts = field(default_factory=TransactionCosts)
    
    # Risk management
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    
    # Benchmark configuration
    benchmark_symbol: str = "SPY"
    benchmark_type: BenchmarkType = BenchmarkType.SPY
    risk_free_rate: float = 0.02  # Annual risk-free rate
    
    # Analysis configuration
    calculate_var: bool = True
    var_confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    stress_test_scenarios: List[str] = field(default_factory=lambda: [
        "2008_financial_crisis",
        "2020_covid_crash",
        "dot_com_bubble"
    ])
    
    # Monte Carlo configuration
    monte_carlo_runs: int = 1000
    monte_carlo_confidence: float = 0.95
    
    # Walk-forward configuration
    walk_forward_window: int = 252  # Training window in days
    walk_forward_step: int = 63  # Step size in days (quarterly)
    
    # Performance attribution
    factor_models: List[str] = field(default_factory=lambda: [
        "fama_french_3",
        "fama_french_5",
        "momentum"
    ])
    
    # Reporting configuration
    generate_plots: bool = True
    save_trades: bool = True
    save_positions: bool = True
    output_directory: Optional[str] = None
    
    # Advanced features
    enable_regime_analysis: bool = True
    enable_factor_attribution: bool = True
    enable_scenario_analysis: bool = True
    enable_optimization: bool = False
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if not 0 < self.risk_limits.max_position_size <= 1:
            raise ValueError("Max position size must be between 0 and 1")
        
        if not 0 < self.risk_limits.max_drawdown <= 1:
            raise ValueError("Max drawdown must be between 0 and 1")
    
    def validate(self) -> bool:
        """Validate the configuration
        
        Returns:
            True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Re-run post_init validation
            self.__post_init__()
            
            # Additional validation checks
            if not isinstance(self.start_date, datetime):
                raise ValueError("start_date must be a datetime object")
            
            if not isinstance(self.end_date, datetime):
                raise ValueError("end_date must be a datetime object")
            
            if self.currency not in ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF']:
                raise ValueError(f"Unsupported currency: {self.currency}")
            
            if self.risk_free_rate < 0 or self.risk_free_rate > 1:
                raise ValueError("risk_free_rate must be between 0 and 1")
            
            # Validate var confidence levels
            for level in self.var_confidence_levels:
                if not 0 < level < 1:
                    raise ValueError(f"VaR confidence level {level} must be between 0 and 1")
            
            return True
            
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {str(e)}")
    
    @classmethod
    def create_default(cls, start_date: datetime, end_date: datetime) -> 'BacktestConfig':
        """Create default configuration"""
        return cls(
            start_date=start_date,
            end_date=end_date
        )
    
    @classmethod
    def create_fast_backtest(cls, start_date: datetime, end_date: datetime) -> 'BacktestConfig':
        """Create configuration for fast backtesting"""
        return cls(
            start_date=start_date,
            end_date=end_date,
            mode=BacktestMode.VECTORIZED,
            calculate_var=False,
            generate_plots=False,
            enable_regime_analysis=False,
            enable_factor_attribution=False,
            enable_scenario_analysis=False
        )
    
    @classmethod
    def create_institutional(cls, start_date: datetime, end_date: datetime) -> 'BacktestConfig':
        """Create configuration for institutional-grade analysis"""
        return cls(
            start_date=start_date,
            end_date=end_date,
            mode=BacktestMode.EVENT_DRIVEN,
            calculate_var=True,
            var_confidence_levels=[0.95, 0.99, 0.999],
            monte_carlo_runs=10000,
            enable_regime_analysis=True,
            enable_factor_attribution=True,
            enable_scenario_analysis=True,
            enable_optimization=True,
            factor_models=[
                "fama_french_3",
                "fama_french_5",
                "momentum",
                "quality",
                "low_volatility"
            ]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'currency': self.currency,
            'mode': self.mode.value,
            'rebalance_frequency': self.rebalance_frequency.value,
            'data_frequency': self.data_frequency,
            'warmup_period': self.warmup_period,
            'benchmark_symbol': self.benchmark_symbol,
            'risk_free_rate': self.risk_free_rate,
            'transaction_costs': self.transaction_costs.__dict__,
            'risk_limits': self.risk_limits.__dict__,
            'custom_params': self.custom_params
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """Create configuration from dictionary"""
        config_dict = config_dict.copy()
        
        # Convert date strings back to datetime objects
        config_dict['start_date'] = datetime.fromisoformat(config_dict['start_date'])
        config_dict['end_date'] = datetime.fromisoformat(config_dict['end_date'])
        
        # Convert enum strings back to enums
        config_dict['mode'] = BacktestMode(config_dict['mode'])
        config_dict['rebalance_frequency'] = RebalanceFrequency(config_dict['rebalance_frequency'])
        
        # Reconstruct nested objects
        if 'transaction_costs' in config_dict:
            config_dict['transaction_costs'] = TransactionCosts(**config_dict['transaction_costs'])
        
        if 'risk_limits' in config_dict:
            config_dict['risk_limits'] = RiskLimits(**config_dict['risk_limits'])
        
        return cls(**config_dict)