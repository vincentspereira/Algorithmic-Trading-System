"""Module for identifying and ranking trading pairs."""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import coint

from .data_models.data_models import PairStatistics


class PairSelectionModule:
    """Module for identifying and ranking trading pairs."""

    def __init__(self, min_correlation: float = 0.7, max_cointegration_pvalue: float = 0.05):
        self.min_correlation = min_correlation
        self.max_cointegration_pvalue = max_cointegration_pvalue

    def calculate_pair_statistics(
        self, price_a: np.ndarray, price_b: np.ndarray
    ) -> PairStatistics:
        """Calculate comprehensive statistics for a pair."""
        # Correlation
        correlation, _ = pearsonr(price_a, price_b)

        # Cointegration test
        try:
            _, cointegration_pvalue, _ = coint(price_a, price_b)
        except:
            cointegration_pvalue = 1.0

        # Beta and R-squared
        returns_a = np.diff(np.log(price_a + 1e-8))
        returns_b = np.diff(np.log(price_b + 1e-8))

        if len(returns_a) > 0 and len(returns_b) > 0:
            model = LinearRegression().fit(returns_b.reshape(-1, 1), returns_a)
            beta = model.coef_[0]
            r_squared = model.score(returns_b.reshape(-1, 1), returns_a)
            hedge_ratio = np.cov(returns_a, returns_b)[0, 1] / (np.var(returns_b) + 1e-8)
        else:
            beta = 1.0
            r_squared = 0.0
            hedge_ratio = 1.0

        # Half-life of mean reversion
        spread = price_a - beta * price_b
        half_life = self._calculate_half_life(spread)

        # Volatility ratio
        vol_a = np.std(returns_a) if len(returns_a) > 0 else 0
        vol_b = np.std(returns_b) if len(returns_b) > 0 else 0
        volatility_ratio = vol_a / (vol_b + 1e-8)

        is_cointegrated = cointegration_pvalue <= self.max_cointegration_pvalue

        return PairStatistics(
            correlation=correlation,
            cointegration_pvalue=cointegration_pvalue,
            beta=beta,
            r_squared=r_squared,
            half_life=half_life,
            volatility_ratio=volatility_ratio,
            is_cointegrated=is_cointegrated,
            hedge_ratio=hedge_ratio,
        )

    def _calculate_half_life(self, spread: np.ndarray) -> float:
        """Calculate half-life of mean reversion."""
        try:
            lagged = spread[:-1]
            changes = np.diff(spread)

            if len(lagged) > 0 and len(changes) > 0:
                model = LinearRegression().fit(lagged.reshape(-1, 1), changes)
                lambda_coef = model.coef_[0]
                if lambda_coef < 0:
                    return -np.log(2) / lambda_coef
        except:
            pass
        return np.nan

    def rank_pairs(
        self, pairs_data: Dict[str, Tuple[np.ndarray, np.ndarray]]
    ) -> List[Tuple[str, PairStatistics, float]]:
        """Rank pairs by trading attractiveness."""
        ranked_pairs = []

        for pair_name, (price_a, price_b) in pairs_data.items():
            stats = self.calculate_pair_statistics(price_a, price_b)

            # Calculate composite score
            score = self._calculate_pair_score(stats)
            ranked_pairs.append((pair_name, stats, score))

        # Sort by score (higher is better)
        ranked_pairs.sort(key=lambda x: x[2], reverse=True)
        return ranked_pairs

    def _calculate_pair_score(self, stats: PairStatistics) -> float:
        """Calculate composite attractiveness score."""
        score = 0.0

        # Correlation component (higher is better)
        if abs(stats.correlation) >= self.min_correlation:
            score += abs(stats.correlation) * 30

        # Cointegration component (lower p-value is better)
        if stats.is_cointegrated:
            score += (1 - stats.cointegration_pvalue) * 25

        # R-squared component (higher is better)
        score += stats.r_squared * 20

        # Half-life component (reasonable range is better)
        if not np.isnan(stats.half_life) and 5 <= stats.half_life <= 50:
            score += 15

        # Volatility ratio component (closer to 1 is better)
        vol_ratio_score = max(0, 10 - abs(stats.volatility_ratio - 1) * 5)
        score += vol_ratio_score

        return score