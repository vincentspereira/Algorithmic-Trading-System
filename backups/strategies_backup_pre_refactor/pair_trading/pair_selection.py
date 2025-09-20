#!/usr/bin/env python3
"""
Pair Selection Engine

Advanced statistical pair selection and screening system for pairs trading.
Provides comprehensive analysis of potential trading pairs including correlation,
cointegration, distance metrics, and fundamental screening.

Key Features:
- Multi-factor pair screening
- Statistical significance testing
- Sector and industry filtering
- Market cap and liquidity constraints
- Historical performance analysis
- Dynamic pair ranking and scoring
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple, Union
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from scipy import stats
from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PairSelectionMethod(Enum):
    """Methods for pair selection."""
    CORRELATION = "correlation"
    COINTEGRATION = "cointegration"
    DISTANCE = "distance"
    FUNDAMENTAL = "fundamental"
    HYBRID = "hybrid"


class SectorFilter(Enum):
    """Sector filtering options."""
    SAME_SECTOR = "same_sector"
    DIFFERENT_SECTOR = "different_sector"
    NO_FILTER = "no_filter"


@dataclass
class PairMetrics:
    """Comprehensive metrics for a trading pair."""
    symbol1: str
    symbol2: str
    correlation: float
    correlation_pvalue: float
    cointegration_score: float
    cointegration_pvalue: float
    distance_score: float
    spread_volatility: float
    spread_mean_reversion_speed: float
    trading_volume_ratio: float
    market_cap_ratio: float
    sector1: Optional[str] = None
    sector2: Optional[str] = None
    industry1: Optional[str] = None
    industry2: Optional[str] = None
    beta_similarity: Optional[float] = None
    liquidity_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    composite_score: float = 0.0
    rank: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class PairSelectionConfig:
    """Configuration for pair selection."""
    # Correlation parameters
    min_correlation: float = 0.7
    max_correlation: float = 0.95
    correlation_lookback: int = 252  # Trading days
    
    # Cointegration parameters
    cointegration_confidence: float = 0.05
    cointegration_lookback: int = 252
    
    # Distance parameters
    distance_method: str = "euclidean"  # euclidean, manhattan, cosine
    normalize_prices: bool = True
    
    # Volume and liquidity filters
    min_avg_volume: float = 1000000  # Minimum average daily volume
    min_market_cap: float = 1000000000  # Minimum market cap ($1B)
    max_market_cap_ratio: float = 10.0  # Max ratio between market caps
    
    # Sector filtering
    sector_filter: SectorFilter = SectorFilter.NO_FILTER
    allowed_sectors: Optional[List[str]] = None
    excluded_sectors: Optional[List[str]] = None
    
    # Selection parameters
    max_pairs: int = 50
    selection_method: PairSelectionMethod = PairSelectionMethod.HYBRID
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly, quarterly
    
    # Risk parameters
    max_beta_difference: float = 0.5
    min_trading_days: int = 252
    max_spread_volatility: float = 0.3
    
    # Performance parameters
    enable_parallel_processing: bool = True
    max_workers: int = 4


class StatisticalPairAnalyzer:
    """Statistical analysis for pair relationships."""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def calculate_correlation(self, 
                            prices1: pd.Series, 
                            prices2: pd.Series,
                            method: str = "pearson") -> Tuple[float, float]:
        """Calculate correlation between two price series.
        
        Args:
            prices1: First price series
            prices2: Second price series
            method: Correlation method (pearson, spearman)
            
        Returns:
            Tuple of (correlation, p-value)
        """
        try:
            # Align series and remove NaN values
            aligned_data = pd.concat([prices1, prices2], axis=1).dropna()
            if len(aligned_data) < 30:  # Minimum observations
                return 0.0, 1.0
            
            if method == "pearson":
                corr, pval = pearsonr(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])
            elif method == "spearman":
                corr, pval = spearmanr(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])
            else:
                raise ValueError(f"Unknown correlation method: {method}")
            
            return float(corr), float(pval)
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            return 0.0, 1.0
    
    def test_cointegration(self, 
                          prices1: pd.Series, 
                          prices2: pd.Series) -> Tuple[float, float]:
        """Test for cointegration using Engle-Granger test.
        
        Args:
            prices1: First price series
            prices2: Second price series
            
        Returns:
            Tuple of (test_statistic, p-value)
        """
        try:
            from statsmodels.tsa.stattools import coint
            
            # Align series and remove NaN values
            aligned_data = pd.concat([prices1, prices2], axis=1).dropna()
            if len(aligned_data) < 50:  # Minimum observations for cointegration
                return 0.0, 1.0
            
            # Perform cointegration test
            score, pvalue, _ = coint(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])
            return float(score), float(pvalue)
        except ImportError:
            logger.warning("statsmodels not available for cointegration testing")
            return 0.0, 1.0
        except Exception as e:
            logger.warning(f"Error in cointegration test: {e}")
            return 0.0, 1.0
    
    def calculate_distance_score(self, 
                               prices1: pd.Series, 
                               prices2: pd.Series,
                               method: str = "euclidean") -> float:
        """Calculate distance-based similarity score.
        
        Args:
            prices1: First price series
            prices2: Second price series
            method: Distance method (euclidean, manhattan, cosine)
            
        Returns:
            Distance score (lower is more similar)
        """
        try:
            # Align and normalize prices
            aligned_data = pd.concat([prices1, prices2], axis=1).dropna()
            if len(aligned_data) < 30:
                return float('inf')
            
            # Normalize prices to same scale
            normalized_data = self.scaler.fit_transform(aligned_data)
            
            if method == "euclidean":
                distance = np.sqrt(np.sum((normalized_data[:, 0] - normalized_data[:, 1]) ** 2))
            elif method == "manhattan":
                distance = np.sum(np.abs(normalized_data[:, 0] - normalized_data[:, 1]))
            elif method == "cosine":
                dot_product = np.dot(normalized_data[:, 0], normalized_data[:, 1])
                norms = np.linalg.norm(normalized_data[:, 0]) * np.linalg.norm(normalized_data[:, 1])
                distance = 1 - (dot_product / norms) if norms > 0 else 1.0
            else:
                raise ValueError(f"Unknown distance method: {method}")
            
            return float(distance)
        except Exception as e:
            logger.warning(f"Error calculating distance score: {e}")
            return float('inf')
    
    def calculate_spread_statistics(self, 
                                  prices1: pd.Series, 
                                  prices2: pd.Series) -> Dict[str, float]:
        """Calculate spread statistics for pair analysis.
        
        Args:
            prices1: First price series
            prices2: Second price series
            
        Returns:
            Dictionary of spread statistics
        """
        try:
            # Align series
            aligned_data = pd.concat([prices1, prices2], axis=1).dropna()
            if len(aligned_data) < 30:
                return {}
            
            # Calculate spread
            spread = aligned_data.iloc[:, 0] - aligned_data.iloc[:, 1]
            
            # Calculate statistics
            stats_dict = {
                'spread_mean': float(spread.mean()),
                'spread_std': float(spread.std()),
                'spread_volatility': float(spread.std() / abs(spread.mean())) if spread.mean() != 0 else float('inf'),
                'spread_skewness': float(spread.skew()),
                'spread_kurtosis': float(spread.kurtosis()),
                'spread_min': float(spread.min()),
                'spread_max': float(spread.max()),
                'spread_range': float(spread.max() - spread.min())
            }
            
            # Calculate mean reversion speed (half-life)
            try:
                from statsmodels.tsa.stattools import adfuller
                adf_result = adfuller(spread.dropna())
                stats_dict['adf_statistic'] = float(adf_result[0])
                stats_dict['adf_pvalue'] = float(adf_result[1])
                
                # Estimate half-life using AR(1) model
                spread_lag = spread.shift(1).dropna()
                spread_current = spread[1:]
                if len(spread_current) > 10:
                    slope, _, _, _, _ = stats.linregress(spread_lag, spread_current)
                    half_life = -np.log(2) / np.log(abs(slope)) if abs(slope) < 1 and slope != 0 else float('inf')
                    stats_dict['mean_reversion_speed'] = float(half_life)
                else:
                    stats_dict['mean_reversion_speed'] = float('inf')
            except ImportError:
                stats_dict['adf_statistic'] = 0.0
                stats_dict['adf_pvalue'] = 1.0
                stats_dict['mean_reversion_speed'] = float('inf')
            
            return stats_dict
        except Exception as e:
            logger.warning(f"Error calculating spread statistics: {e}")
            return {}


class PairScreener:
    """Screen and filter potential trading pairs."""
    
    def __init__(self, config: PairSelectionConfig):
        self.config = config
        self.analyzer = StatisticalPairAnalyzer()
    
    def screen_universe(self, 
                       price_data: Dict[str, pd.Series],
                       fundamental_data: Optional[Dict[str, Dict]] = None) -> List[Tuple[str, str]]:
        """Screen universe of stocks for potential pairs.
        
        Args:
            price_data: Dictionary of symbol -> price series
            fundamental_data: Optional fundamental data for filtering
            
        Returns:
            List of potential pairs (symbol1, symbol2)
        """
        symbols = list(price_data.keys())
        potential_pairs = []
        
        # Generate all possible pairs
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols[i+1:], i+1):
                if self._passes_initial_screening(symbol1, symbol2, price_data, fundamental_data):
                    potential_pairs.append((symbol1, symbol2))
        
        logger.info(f"Initial screening found {len(potential_pairs)} potential pairs")
        return potential_pairs
    
    def _passes_initial_screening(self, 
                                symbol1: str, 
                                symbol2: str,
                                price_data: Dict[str, pd.Series],
                                fundamental_data: Optional[Dict[str, Dict]] = None) -> bool:
        """Check if pair passes initial screening criteria."""
        try:
            # Check data availability
            if symbol1 not in price_data or symbol2 not in price_data:
                return False
            
            prices1 = price_data[symbol1]
            prices2 = price_data[symbol2]
            
            # Check minimum trading days
            aligned_data = pd.concat([prices1, prices2], axis=1).dropna()
            if len(aligned_data) < self.config.min_trading_days:
                return False
            
            # Check sector filtering if fundamental data available
            if fundamental_data and self.config.sector_filter != SectorFilter.NO_FILTER:
                sector1 = fundamental_data.get(symbol1, {}).get('sector')
                sector2 = fundamental_data.get(symbol2, {}).get('sector')
                
                if self.config.sector_filter == SectorFilter.SAME_SECTOR:
                    if sector1 != sector2 or not sector1:
                        return False
                elif self.config.sector_filter == SectorFilter.DIFFERENT_SECTOR:
                    if sector1 == sector2 or not sector1 or not sector2:
                        return False
            
            # Check allowed/excluded sectors
            if fundamental_data:
                if self.config.allowed_sectors:
                    sector1 = fundamental_data.get(symbol1, {}).get('sector')
                    sector2 = fundamental_data.get(symbol2, {}).get('sector')
                    if sector1 not in self.config.allowed_sectors or sector2 not in self.config.allowed_sectors:
                        return False
                
                if self.config.excluded_sectors:
                    sector1 = fundamental_data.get(symbol1, {}).get('sector')
                    sector2 = fundamental_data.get(symbol2, {}).get('sector')
                    if sector1 in self.config.excluded_sectors or sector2 in self.config.excluded_sectors:
                        return False
            
            return True
        except Exception as e:
            logger.warning(f"Error in initial screening for {symbol1}-{symbol2}: {e}")
            return False


class PairRanking:
    """Rank and score pairs based on multiple criteria."""
    
    def __init__(self, config: PairSelectionConfig):
        self.config = config
        self.analyzer = StatisticalPairAnalyzer()
    
    def calculate_composite_score(self, metrics: PairMetrics) -> float:
        """Calculate composite score for pair ranking.
        
        Args:
            metrics: Pair metrics
            
        Returns:
            Composite score (higher is better)
        """
        try:
            score = 0.0
            
            # Correlation component (30% weight)
            if self.config.min_correlation <= abs(metrics.correlation) <= self.config.max_correlation:
                corr_score = (abs(metrics.correlation) - self.config.min_correlation) / \
                           (self.config.max_correlation - self.config.min_correlation)
                score += 0.3 * corr_score
            
            # Cointegration component (25% weight)
            if metrics.cointegration_pvalue <= self.config.cointegration_confidence:
                coint_score = 1.0 - metrics.cointegration_pvalue / self.config.cointegration_confidence
                score += 0.25 * coint_score
            
            # Distance component (20% weight) - lower distance is better
            if metrics.distance_score < float('inf'):
                # Normalize distance score (assuming max reasonable distance is 10)
                distance_score = max(0, 1.0 - metrics.distance_score / 10.0)
                score += 0.2 * distance_score
            
            # Mean reversion speed (15% weight) - faster is better
            if metrics.spread_mean_reversion_speed < float('inf'):
                # Normalize mean reversion speed (assuming max reasonable half-life is 50 days)
                mr_score = max(0, 1.0 - metrics.spread_mean_reversion_speed / 50.0)
                score += 0.15 * mr_score
            
            # Liquidity component (10% weight)
            if metrics.liquidity_score is not None:
                score += 0.1 * metrics.liquidity_score
            
            return float(score)
        except Exception as e:
            logger.warning(f"Error calculating composite score: {e}")
            return 0.0
    
    def rank_pairs(self, pairs_metrics: List[PairMetrics]) -> List[PairMetrics]:
        """Rank pairs by composite score.
        
        Args:
            pairs_metrics: List of pair metrics
            
        Returns:
            Ranked list of pair metrics
        """
        try:
            # Calculate composite scores
            for metrics in pairs_metrics:
                metrics.composite_score = self.calculate_composite_score(metrics)
            
            # Sort by composite score (descending)
            ranked_pairs = sorted(pairs_metrics, key=lambda x: x.composite_score, reverse=True)
            
            # Assign ranks
            for i, metrics in enumerate(ranked_pairs):
                metrics.rank = i + 1
            
            # Return top pairs
            return ranked_pairs[:self.config.max_pairs]
        except Exception as e:
            logger.error(f"Error ranking pairs: {e}")
            return pairs_metrics


class PairSelectionEngine:
    """Main engine for pair selection and analysis."""
    
    def __init__(self, config: PairSelectionConfig):
        self.config = config
        self.screener = PairScreener(config)
        self.analyzer = StatisticalPairAnalyzer()
        self.ranker = PairRanking(config)
        self.selected_pairs: List[PairMetrics] = []
        self.last_selection_date: Optional[datetime] = None
    
    def select_pairs(self, 
                    price_data: Dict[str, pd.Series],
                    fundamental_data: Optional[Dict[str, Dict]] = None,
                    force_update: bool = False) -> List[PairMetrics]:
        """Select and rank trading pairs.
        
        Args:
            price_data: Dictionary of symbol -> price series
            fundamental_data: Optional fundamental data
            force_update: Force pair selection update
            
        Returns:
            List of selected and ranked pairs
        """
        try:
            # Check if update is needed
            if not force_update and self._should_skip_update():
                return self.selected_pairs
            
            logger.info("Starting pair selection process...")
            
            # Screen potential pairs
            potential_pairs = self.screener.screen_universe(price_data, fundamental_data)
            
            if not potential_pairs:
                logger.warning("No potential pairs found after screening")
                return []
            
            # Analyze pairs
            if self.config.enable_parallel_processing:
                pairs_metrics = self._analyze_pairs_parallel(potential_pairs, price_data, fundamental_data)
            else:
                pairs_metrics = self._analyze_pairs_sequential(potential_pairs, price_data, fundamental_data)
            
            # Filter pairs that meet criteria
            filtered_pairs = self._filter_pairs(pairs_metrics)
            
            # Rank pairs
            self.selected_pairs = self.ranker.rank_pairs(filtered_pairs)
            self.last_selection_date = datetime.now()
            
            logger.info(f"Selected {len(self.selected_pairs)} pairs for trading")
            return self.selected_pairs
        
        except Exception as e:
            logger.error(f"Error in pair selection: {e}")
            return []
    
    def _should_skip_update(self) -> bool:
        """Check if pair selection update should be skipped."""
        if not self.last_selection_date or not self.selected_pairs:
            return False
        
        # Check rebalance frequency
        now = datetime.now()
        if self.config.rebalance_frequency == "daily":
            return (now - self.last_selection_date).days < 1
        elif self.config.rebalance_frequency == "weekly":
            return (now - self.last_selection_date).days < 7
        elif self.config.rebalance_frequency == "monthly":
            return (now - self.last_selection_date).days < 30
        elif self.config.rebalance_frequency == "quarterly":
            return (now - self.last_selection_date).days < 90
        
        return False
    
    def _analyze_pairs_parallel(self, 
                              potential_pairs: List[Tuple[str, str]],
                              price_data: Dict[str, pd.Series],
                              fundamental_data: Optional[Dict[str, Dict]]) -> List[PairMetrics]:
        """Analyze pairs using parallel processing."""
        pairs_metrics = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit analysis tasks
            future_to_pair = {
                executor.submit(self._analyze_single_pair, pair, price_data, fundamental_data): pair
                for pair in potential_pairs
            }
            
            # Collect results
            for future in as_completed(future_to_pair):
                try:
                    metrics = future.result()
                    if metrics:
                        pairs_metrics.append(metrics)
                except Exception as e:
                    pair = future_to_pair[future]
                    logger.warning(f"Error analyzing pair {pair}: {e}")
        
        return pairs_metrics
    
    def _analyze_pairs_sequential(self, 
                                potential_pairs: List[Tuple[str, str]],
                                price_data: Dict[str, pd.Series],
                                fundamental_data: Optional[Dict[str, Dict]]) -> List[PairMetrics]:
        """Analyze pairs sequentially."""
        pairs_metrics = []
        
        for pair in potential_pairs:
            try:
                metrics = self._analyze_single_pair(pair, price_data, fundamental_data)
                if metrics:
                    pairs_metrics.append(metrics)
            except Exception as e:
                logger.warning(f"Error analyzing pair {pair}: {e}")
        
        return pairs_metrics
    
    def _analyze_single_pair(self, 
                           pair: Tuple[str, str],
                           price_data: Dict[str, pd.Series],
                           fundamental_data: Optional[Dict[str, Dict]]) -> Optional[PairMetrics]:
        """Analyze a single pair."""
        try:
            symbol1, symbol2 = pair
            prices1 = price_data[symbol1]
            prices2 = price_data[symbol2]
            
            # Calculate correlation
            correlation, corr_pvalue = self.analyzer.calculate_correlation(prices1, prices2)
            
            # Test cointegration
            coint_score, coint_pvalue = self.analyzer.test_cointegration(prices1, prices2)
            
            # Calculate distance score
            distance_score = self.analyzer.calculate_distance_score(
                prices1, prices2, self.config.distance_method
            )
            
            # Calculate spread statistics
            spread_stats = self.analyzer.calculate_spread_statistics(prices1, prices2)
            
            # Extract fundamental data if available
            fund1 = fundamental_data.get(symbol1, {}) if fundamental_data else {}
            fund2 = fundamental_data.get(symbol2, {}) if fundamental_data else {}
            
            # Create metrics object
            metrics = PairMetrics(
                symbol1=symbol1,
                symbol2=symbol2,
                correlation=correlation,
                correlation_pvalue=corr_pvalue,
                cointegration_score=coint_score,
                cointegration_pvalue=coint_pvalue,
                distance_score=distance_score,
                spread_volatility=spread_stats.get('spread_volatility', float('inf')),
                spread_mean_reversion_speed=spread_stats.get('mean_reversion_speed', float('inf')),
                trading_volume_ratio=self._calculate_volume_ratio(fund1, fund2),
                market_cap_ratio=self._calculate_market_cap_ratio(fund1, fund2),
                sector1=fund1.get('sector'),
                sector2=fund2.get('sector'),
                industry1=fund1.get('industry'),
                industry2=fund2.get('industry'),
                beta_similarity=self._calculate_beta_similarity(fund1, fund2),
                liquidity_score=self._calculate_liquidity_score(fund1, fund2)
            )
            
            return metrics
        
        except Exception as e:
            logger.warning(f"Error analyzing pair {pair}: {e}")
            return None
    
    def _calculate_volume_ratio(self, fund1: Dict, fund2: Dict) -> float:
        """Calculate trading volume ratio."""
        try:
            vol1 = fund1.get('avg_volume', 0)
            vol2 = fund2.get('avg_volume', 0)
            if vol1 > 0 and vol2 > 0:
                return max(vol1, vol2) / min(vol1, vol2)
            return float('inf')
        except:
            return float('inf')
    
    def _calculate_market_cap_ratio(self, fund1: Dict, fund2: Dict) -> float:
        """Calculate market cap ratio."""
        try:
            cap1 = fund1.get('market_cap', 0)
            cap2 = fund2.get('market_cap', 0)
            if cap1 > 0 and cap2 > 0:
                return max(cap1, cap2) / min(cap1, cap2)
            return float('inf')
        except:
            return float('inf')
    
    def _calculate_beta_similarity(self, fund1: Dict, fund2: Dict) -> Optional[float]:
        """Calculate beta similarity score."""
        try:
            beta1 = fund1.get('beta')
            beta2 = fund2.get('beta')
            if beta1 is not None and beta2 is not None:
                return 1.0 - abs(beta1 - beta2) / max(abs(beta1), abs(beta2), 1.0)
            return None
        except:
            return None
    
    def _calculate_liquidity_score(self, fund1: Dict, fund2: Dict) -> Optional[float]:
        """Calculate liquidity score."""
        try:
            vol1 = fund1.get('avg_volume', 0)
            vol2 = fund2.get('avg_volume', 0)
            
            if vol1 >= self.config.min_avg_volume and vol2 >= self.config.min_avg_volume:
                # Normalize to 0-1 scale
                min_vol = min(vol1, vol2)
                score = min(1.0, min_vol / (self.config.min_avg_volume * 10))
                return score
            return 0.0
        except:
            return 0.0
    
    def _filter_pairs(self, pairs_metrics: List[PairMetrics]) -> List[PairMetrics]:
        """Filter pairs based on selection criteria."""
        filtered_pairs = []
        
        for metrics in pairs_metrics:
            try:
                # Correlation filter
                if not (self.config.min_correlation <= abs(metrics.correlation) <= self.config.max_correlation):
                    continue
                
                # Cointegration filter
                if metrics.cointegration_pvalue > self.config.cointegration_confidence:
                    continue
                
                # Market cap ratio filter
                if metrics.market_cap_ratio > self.config.max_market_cap_ratio:
                    continue
                
                # Spread volatility filter
                if metrics.spread_volatility > self.config.max_spread_volatility:
                    continue
                
                # Beta similarity filter
                if (metrics.beta_similarity is not None and 
                    metrics.beta_similarity < (1.0 - self.config.max_beta_difference)):
                    continue
                
                filtered_pairs.append(metrics)
            
            except Exception as e:
                logger.warning(f"Error filtering pair {metrics.symbol1}-{metrics.symbol2}: {e}")
        
        return filtered_pairs
    
    def get_pair_details(self, symbol1: str, symbol2: str) -> Optional[PairMetrics]:
        """Get detailed metrics for a specific pair."""
        for metrics in self.selected_pairs:
            if (metrics.symbol1 == symbol1 and metrics.symbol2 == symbol2) or \
               (metrics.symbol1 == symbol2 and metrics.symbol2 == symbol1):
                return metrics
        return None
    
    def export_pairs(self, filepath: str) -> None:
        """Export selected pairs to CSV file."""
        try:
            if not self.selected_pairs:
                logger.warning("No pairs to export")
                return
            
            # Convert to DataFrame
            data = []
            for metrics in self.selected_pairs:
                data.append({
                    'Symbol1': metrics.symbol1,
                    'Symbol2': metrics.symbol2,
                    'Rank': metrics.rank,
                    'Composite_Score': metrics.composite_score,
                    'Correlation': metrics.correlation,
                    'Correlation_PValue': metrics.correlation_pvalue,
                    'Cointegration_Score': metrics.cointegration_score,
                    'Cointegration_PValue': metrics.cointegration_pvalue,
                    'Distance_Score': metrics.distance_score,
                    'Spread_Volatility': metrics.spread_volatility,
                    'Mean_Reversion_Speed': metrics.spread_mean_reversion_speed,
                    'Volume_Ratio': metrics.trading_volume_ratio,
                    'Market_Cap_Ratio': metrics.market_cap_ratio,
                    'Sector1': metrics.sector1,
                    'Sector2': metrics.sector2,
                    'Industry1': metrics.industry1,
                    'Industry2': metrics.industry2,
                    'Beta_Similarity': metrics.beta_similarity,
                    'Liquidity_Score': metrics.liquidity_score,
                    'Last_Updated': metrics.last_updated
                })
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            logger.info(f"Exported {len(self.selected_pairs)} pairs to {filepath}")
        
        except Exception as e:
            logger.error(f"Error exporting pairs: {e}")