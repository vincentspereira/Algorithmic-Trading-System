"""
Performance Attribution System for Nautilus Trader Engine
Provides comprehensive analysis of portfolio performance attribution.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm

logger = logging.getLogger(__name__)


class AttributionMethod(Enum):
    """Methods for performance attribution."""
    BRINSON = "brinson"  # Brinson attribution
    CARHART = "carhart"  # Carhart 4-factor model
    FAMA_FRENCH = "fama_french"  # Fama-French 5-factor model
    RISK_DECOMPOSITION = "risk_decomposition"
    FACTOR_ATTRIBUTION = "factor_attribution"
    STYLE_ATTRIBUTION = "style_attribution"
    SECTOR_ATTRIBUTION = "sector_attribution"


class AttributionPeriod(Enum):
    """Attribution analysis periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class AttributionResult:
    """Result of performance attribution analysis."""
    method: AttributionMethod
    period: AttributionPeriod
    total_return: float
    attributed_return: float
    unexplained_return: float
    attribution_breakdown: Dict[str, float]
    risk_attribution: Dict[str, float]
    factor_exposures: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]
    statistical_significance: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FactorReturn:
    """Factor return data."""
    factor_name: str
    return_value: float
    volatility: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyAttribution:
    """Attribution for a specific strategy."""
    strategy_name: str
    contribution_to_return: float
    contribution_to_risk: float
    sharpe_attribution: float
    factor_exposures: Dict[str, float]
    sector_allocations: Dict[str, float]
    style_exposures: Dict[str, float]


class FactorModel(ABC):
    """Base class for factor models."""

    @abstractmethod
    def estimate_factor_exposures(self, returns: pd.Series,
                                factor_returns: pd.DataFrame) -> Dict[str, float]:
        """Estimate factor exposures for a return series."""
        pass

    @abstractmethod
    def calculate_factor_contributions(self, exposures: Dict[str, float],
                                     factor_returns: Dict[str, float]) -> Dict[str, float]:
        """Calculate contribution of each factor to total return."""
        pass

    @abstractmethod
    def get_model_factors(self) -> List[str]:
        """Get list of factors in the model."""
        pass


class Carhart4FactorModel(FactorModel):
    """Carhart 4-factor model: Market, Size, Value, Momentum."""

    def get_model_factors(self) -> List[str]:
        return ["market", "size", "value", "momentum"]

    def estimate_factor_exposures(self, returns: pd.Series,
                                factor_returns: pd.DataFrame) -> Dict[str, float]:
        """Estimate factor exposures using regression."""
        try:
            # Prepare data
            y = returns.values.reshape(-1, 1)
            X = factor_returns[self.get_model_factors()].values

            if len(y) != len(X):
                logger.warning("Mismatch in data lengths for factor regression")
                return {factor: 0.0 for factor in self.get_model_factors()}

            # Add intercept
            X = sm.add_constant(X)

            # Fit model
            model = sm.OLS(y, X).fit()

            # Extract coefficients
            exposures = {}
            for i, factor in enumerate(self.get_model_factors()):
                exposures[factor] = model.params[i + 1]  # Skip intercept

            return exposures

        except Exception as e:
            logger.error(f"Error estimating Carhart factor exposures: {e}")
            return {factor: 0.0 for factor in self.get_model_factors()}

    def calculate_factor_contributions(self, exposures: Dict[str, float],
                                     factor_returns: Dict[str, float]) -> Dict[str, float]:
        """Calculate factor contributions."""
        contributions = {}
        for factor in self.get_model_factors():
            exposure = exposures.get(factor, 0.0)
            factor_return = factor_returns.get(factor, 0.0)
            contributions[factor] = exposure * factor_return

        return contributions


class FamaFrench5FactorModel(FactorModel):
    """Fama-French 5-factor model: Market, Size, Value, Profitability, Investment."""

    def get_model_factors(self) -> List[str]:
        return ["market", "size", "value", "profitability", "investment"]

    def estimate_factor_exposures(self, returns: pd.Series,
                                factor_returns: pd.DataFrame) -> Dict[str, float]:
        """Estimate factor exposures using regression."""
        try:
            y = returns.values.reshape(-1, 1)
            X = factor_returns[self.get_model_factors()].values

            if len(y) != len(X):
                return {factor: 0.0 for factor in self.get_model_factors()}

            X = sm.add_constant(X)
            model = sm.OLS(y, X).fit()

            exposures = {}
            for i, factor in enumerate(self.get_model_factors()):
                exposures[factor] = model.params[i + 1]

            return exposures

        except Exception as e:
            logger.error(f"Error estimating Fama-French factor exposures: {e}")
            return {factor: 0.0 for factor in self.get_model_factors()}

    def calculate_factor_contributions(self, exposures: Dict[str, float],
                                     factor_returns: Dict[str, float]) -> Dict[str, float]:
        """Calculate factor contributions."""
        contributions = {}
        for factor in self.get_model_factors():
            exposure = exposures.get(factor, 0.0)
            factor_return = factor_returns.get(factor, 0.0)
            contributions[factor] = exposure * factor_return

        return contributions


class RiskDecompositionModel:
    """Risk decomposition using factor models."""

    def __init__(self, factor_model: FactorModel):
        self.factor_model = factor_model

    def decompose_risk(self, returns: pd.Series,
                      factor_returns: pd.DataFrame) -> Dict[str, float]:
        """Decompose total risk into factor contributions."""
        try:
            # Estimate factor exposures
            exposures = self.factor_model.estimate_factor_exposures(returns, factor_returns)

            # Calculate factor covariance matrix
            factor_cov = factor_returns[self.factor_model.get_model_factors()].cov()

            # Calculate risk decomposition
            risk_decomposition = {}
            total_factor_risk = 0

            for i, factor1 in enumerate(self.factor_model.get_model_factors()):
                factor_risk = 0
                for j, factor2 in enumerate(self.factor_model.get_model_factors()):
                    factor_risk += exposures[factor1] * exposures[factor2] * factor_cov.iloc[i, j]

                factor_risk = max(0, factor_risk)  # Ensure non-negative
                risk_decomposition[factor1] = np.sqrt(factor_risk)
                total_factor_risk += factor_risk

            # Calculate unexplained risk (idiosyncratic risk)
            total_variance = returns.var()
            unexplained_variance = max(0, total_variance - total_factor_risk)
            risk_decomposition["unexplained"] = np.sqrt(unexplained_variance)

            # Calculate percentages
            total_risk = np.sqrt(total_variance)
            if total_risk > 0:
                for factor in list(risk_decomposition.keys()):  # Create a copy of keys
                    risk_decomposition[f"{factor}_pct"] = (risk_decomposition[factor] / total_risk) * 100

            return risk_decomposition

        except Exception as e:
            logger.error(f"Error in risk decomposition: {e}")
            return {}


class BrinsonAttribution:
    """Brinson performance attribution model."""

    def __init__(self):
        self.benchmark_weights = {}
        self.portfolio_weights = {}

    def set_benchmark_weights(self, weights: Dict[str, float]) -> None:
        """Set benchmark weights."""
        self.benchmark_weights = weights.copy()

    def set_portfolio_weights(self, weights: Dict[str, float]) -> None:
        """Set portfolio weights."""
        self.portfolio_weights = weights.copy()

    def calculate_attribution(self, asset_returns: Dict[str, float]) -> Dict[str, float]:
        """Calculate Brinson attribution effects."""
        try:
            # Allocation effect: (portfolio_weight - benchmark_weight) * benchmark_return
            allocation_effect = {}
            benchmark_return = sum(
                self.benchmark_weights.get(asset, 0) * asset_returns.get(asset, 0)
                for asset in set(self.benchmark_weights) | set(asset_returns)
            )

            for asset in set(self.portfolio_weights) | set(self.benchmark_weights):
                port_weight = self.portfolio_weights.get(asset, 0)
                bench_weight = self.benchmark_weights.get(asset, 0)
                allocation_effect[asset] = (port_weight - bench_weight) * benchmark_return

            # Selection effect: benchmark_weight * (portfolio_return - benchmark_return)
            selection_effect = {}
            for asset in set(self.portfolio_weights) | set(self.benchmark_weights):
                bench_weight = self.benchmark_weights.get(asset, 0)
                port_return = asset_returns.get(asset, 0)
                asset_bench_return = benchmark_return  # Simplified
                selection_effect[asset] = bench_weight * (port_return - asset_bench_return)

            # Interaction effect: (portfolio_weight - benchmark_weight) * (portfolio_return - benchmark_return)
            interaction_effect = {}
            for asset in set(self.portfolio_weights) | set(self.benchmark_weights):
                port_weight = self.portfolio_weights.get(asset, 0)
                bench_weight = self.benchmark_weights.get(asset, 0)
                port_return = asset_returns.get(asset, 0)
                asset_bench_return = benchmark_return  # Simplified
                interaction_effect[asset] = (port_weight - bench_weight) * (port_return - asset_bench_return)

            return {
                "allocation_effect": sum(allocation_effect.values()),
                "selection_effect": sum(selection_effect.values()),
                "interaction_effect": sum(interaction_effect.values()),
                "total_attribution": sum(allocation_effect.values()) + sum(selection_effect.values()) + sum(interaction_effect.values()),
                "allocation_by_asset": allocation_effect,
                "selection_by_asset": selection_effect,
                "interaction_by_asset": interaction_effect
            }

        except Exception as e:
            logger.error(f"Error in Brinson attribution: {e}")
            return {}


class PerformanceAttributionEngine:
    """
    Main engine for performance attribution analysis.
    """

    def __init__(self):
        self.factor_models = {
            AttributionMethod.CARHART: Carhart4FactorModel(),
            AttributionMethod.FAMA_FRENCH: FamaFrench5FactorModel()
        }
        self.risk_decomposition = RiskDecompositionModel(Carhart4FactorModel())
        self.brinson_model = BrinsonAttribution()
        self.attribution_history: List[AttributionResult] = []

    def analyze_performance_attribution(self, portfolio_returns: pd.Series,
                                      benchmark_returns: Optional[pd.Series] = None,
                                      factor_returns: Optional[pd.DataFrame] = None,
                                      method: AttributionMethod = AttributionMethod.CARHART,
                                      period: AttributionPeriod = AttributionPeriod.MONTHLY) -> AttributionResult:
        """Perform comprehensive performance attribution analysis."""
        try:
            # Calculate total return
            total_return = (portfolio_returns + 1).prod() - 1

            # Get factor model
            factor_model = self.factor_models.get(method)
            if not factor_model:
                factor_model = self.factor_models[AttributionMethod.CARHART]

            attribution_breakdown = {}
            factor_exposures = {}
            risk_attribution = {}

            if factor_returns is not None and not factor_returns.empty:
                # Estimate factor exposures
                factor_exposures = factor_model.estimate_factor_exposures(portfolio_returns, factor_returns)

                # Calculate factor contributions
                latest_factor_returns = factor_returns.iloc[-1].to_dict()
                attribution_breakdown = factor_model.calculate_factor_contributions(
                    factor_exposures, latest_factor_returns
                )

                # Risk decomposition
                risk_attribution = self.risk_decomposition.decompose_risk(portfolio_returns, factor_returns)

            # Calculate unexplained return
            attributed_return = sum(attribution_breakdown.values())
            unexplained_return = total_return - attributed_return

            # Calculate confidence intervals (simplified)
            confidence_intervals = {}
            for factor, contribution in attribution_breakdown.items():
                # Simple confidence interval based on historical volatility
                std_contribution = abs(contribution) * 0.1  # Assume 10% standard deviation
                confidence_intervals[factor] = (
                    contribution - 1.96 * std_contribution,
                    contribution + 1.96 * std_contribution
                )

            # Statistical significance (simplified t-test)
            statistical_significance = {}
            for factor, contribution in attribution_breakdown.items():
                if contribution != 0:
                    # Simplified significance test
                    t_stat = contribution / (abs(contribution) * 0.1)
                    statistical_significance[factor] = 2 * (1 - stats.t.cdf(abs(t_stat), len(portfolio_returns) - 1))

            result = AttributionResult(
                method=method,
                period=period,
                total_return=total_return,
                attributed_return=attributed_return,
                unexplained_return=unexplained_return,
                attribution_breakdown=attribution_breakdown,
                risk_attribution=risk_attribution,
                factor_exposures=factor_exposures,
                confidence_intervals=confidence_intervals,
                statistical_significance=statistical_significance
            )

            self.attribution_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Error in performance attribution analysis: {e}")
            return AttributionResult(
                method=method,
                period=period,
                total_return=0.0,
                attributed_return=0.0,
                unexplained_return=0.0,
                attribution_breakdown={},
                risk_attribution={},
                factor_exposures={},
                confidence_intervals={},
                statistical_significance={}
            )

    def analyze_strategy_attribution(self, strategy_returns: Dict[str, pd.Series],
                                   portfolio_weights: Dict[str, float],
                                   benchmark_returns: Optional[pd.Series] = None) -> Dict[str, StrategyAttribution]:
        """Analyze attribution for individual strategies."""
        try:
            strategy_attributions = {}

            for strategy_name, returns in strategy_returns.items():
                weight = portfolio_weights.get(strategy_name, 0)

                if weight == 0 or returns.empty:
                    continue

                # Calculate strategy metrics
                strategy_return = (returns + 1).prod() - 1
                strategy_volatility = returns.std() * np.sqrt(252)  # Annualized

                # Contribution to portfolio return
                contribution_to_return = weight * strategy_return

                # Contribution to portfolio risk (simplified)
                contribution_to_risk = weight * strategy_volatility

                # Sharpe attribution (simplified)
                risk_free_rate = 0.02
                strategy_sharpe = (strategy_return - risk_free_rate) / strategy_volatility if strategy_volatility > 0 else 0
                sharpe_attribution = weight * strategy_sharpe

                # Factor exposures (simplified - would need factor model)
                factor_exposures = {
                    "market": 1.0,  # Assume beta of 1
                    "size": 0.0,
                    "value": 0.0,
                    "momentum": 0.0
                }

                # Sector allocations (simplified)
                sector_allocations = {
                    "technology": 0.3,
                    "healthcare": 0.2,
                    "financials": 0.2,
                    "consumer": 0.15,
                    "industrials": 0.15
                }

                # Style exposures (simplified)
                style_exposures = {
                    "growth": 0.4,
                    "value": 0.3,
                    "blend": 0.3
                }

                attribution = StrategyAttribution(
                    strategy_name=strategy_name,
                    contribution_to_return=contribution_to_return,
                    contribution_to_risk=contribution_to_risk,
                    sharpe_attribution=sharpe_attribution,
                    factor_exposures=factor_exposures,
                    sector_allocations=sector_allocations,
                    style_exposures=style_exposures
                )

                strategy_attributions[strategy_name] = attribution

            return strategy_attributions

        except Exception as e:
            logger.error(f"Error in strategy attribution analysis: {e}")
            return {}

    def get_attribution_summary(self, periods: Optional[List[AttributionPeriod]] = None) -> Dict[str, Any]:
        """Get summary of attribution analysis."""
        if not self.attribution_history:
            return {}

        periods = periods or [AttributionPeriod.MONTHLY]

        summary = {}
        for period in periods:
            period_results = [r for r in self.attribution_history if r.period == period]

            if period_results:
                avg_total_return = np.mean([r.total_return for r in period_results])
                avg_attributed_return = np.mean([r.attributed_return for r in period_results])
                avg_unexplained_return = np.mean([r.unexplained_return for r in period_results])

                # Average attribution breakdown
                all_factors = set()
                for result in period_results:
                    all_factors.update(result.attribution_breakdown.keys())

                avg_attribution = {}
                for factor in all_factors:
                    values = [r.attribution_breakdown.get(factor, 0) for r in period_results]
                    avg_attribution[factor] = np.mean(values)

                summary[period.value] = {
                    "avg_total_return": avg_total_return,
                    "avg_attributed_return": avg_attributed_return,
                    "avg_unexplained_return": avg_unexplained_return,
                    "avg_attribution_breakdown": avg_attribution,
                    "num_analyses": len(period_results)
                }

        return summary

    def export_attribution_report(self, filepath: str, format: str = "json") -> None:
        """Export attribution analysis to file."""
        try:
            if format == "json":
                import json
                data = {
                    "attribution_history": [
                        {
                            "method": result.method.value,
                            "period": result.period.value,
                            "total_return": result.total_return,
                            "attributed_return": result.attributed_return,
                            "unexplained_return": result.unexplained_return,
                            "attribution_breakdown": result.attribution_breakdown,
                            "timestamp": result.timestamp.isoformat()
                        }
                        for result in self.attribution_history
                    ]
                }

                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)

            elif format == "csv":
                if self.attribution_history:
                    df = pd.DataFrame([
                        {
                            "method": result.method.value,
                            "period": result.period.value,
                            "total_return": result.total_return,
                            "attributed_return": result.attributed_return,
                            "unexplained_return": result.unexplained_return,
                            "timestamp": result.timestamp.isoformat(),
                            **result.attribution_breakdown
                        }
                        for result in self.attribution_history
                    ])
                    df.to_csv(filepath, index=False)

            logger.info(f"Exported attribution report to {filepath}")

        except Exception as e:
            logger.error(f"Error exporting attribution report: {e}")


# Global attribution engine instance
_attribution_engine = PerformanceAttributionEngine()


def get_attribution_engine() -> PerformanceAttributionEngine:
    """Get the global attribution engine."""
    return _attribution_engine


# Convenience functions
def analyze_performance_attribution(portfolio_returns: pd.Series,
                                  benchmark_returns: Optional[pd.Series] = None,
                                  factor_returns: Optional[pd.DataFrame] = None,
                                  method: AttributionMethod = AttributionMethod.CARHART,
                                  period: AttributionPeriod = AttributionPeriod.MONTHLY) -> AttributionResult:
    """Analyze performance attribution globally."""
    return _attribution_engine.analyze_performance_attribution(
        portfolio_returns, benchmark_returns, factor_returns, method, period
    )


def analyze_strategy_attribution(strategy_returns: Dict[str, pd.Series],
                               portfolio_weights: Dict[str, float],
                               benchmark_returns: Optional[pd.Series] = None) -> Dict[str, StrategyAttribution]:
    """Analyze strategy attribution globally."""
    return _attribution_engine.analyze_strategy_attribution(
        strategy_returns, portfolio_weights, benchmark_returns
    )


if __name__ == "__main__":
    # Example usage
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta

    # Create sample data
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)

    # Create sample factor returns
    factor_returns = pd.DataFrame({
        'market': np.random.normal(0.0008, 0.015, 100),
        'size': np.random.normal(0.0002, 0.008, 100),
        'value': np.random.normal(0.0003, 0.012, 100),
        'momentum': np.random.normal(0.0005, 0.018, 100)
    }, index=dates)

    # Analyze attribution
    result = analyze_performance_attribution(
        portfolio_returns,
        factor_returns=factor_returns,
        method=AttributionMethod.CARHART,
        period=AttributionPeriod.DAILY
    )

    print(f"Total Return: {result.total_return:.4f}")
    print(f"Attributed Return: {result.attributed_return:.4f}")
    print(f"Unexplained Return: {result.unexplained_return:.4f}")
    print(f"Attribution Breakdown: {result.attribution_breakdown}")
    print(f"Factor Exposures: {result.factor_exposures}")

    # Get summary
    summary = _attribution_engine.get_attribution_summary()
    print(f"Attribution Summary: {summary}")