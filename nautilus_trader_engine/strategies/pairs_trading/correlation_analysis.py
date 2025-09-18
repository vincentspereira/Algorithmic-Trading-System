#!/usr/bin/env python3
"""
Correlation and Cointegration Analysis

Advanced statistical analysis for pairs trading including correlation analysis,
cointegration testing, stationarity testing, and time series analysis.

Key Features:
- Rolling correlation analysis
- Engle-Granger cointegration testing
- Johansen cointegration testing
- Augmented Dickey-Fuller stationarity tests
- KPSS stationarity tests
- Spread analysis and modeling
- Time series decomposition
- Regime change detection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple, Union
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrelationType(Enum):
    """Types of correlation analysis."""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    ROLLING = "rolling"
    DYNAMIC = "dynamic"


class StationarityTest(Enum):
    """Types of stationarity tests."""
    ADF = "adf"  # Augmented Dickey-Fuller
    KPSS = "kpss"  # Kwiatkowski-Phillips-Schmidt-Shin
    PP = "pp"  # Phillips-Perron


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    correlation: float
    pvalue: float
    confidence_interval: Tuple[float, float]
    method: str
    sample_size: int
    is_significant: bool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CointegrationResult:
    """Result of cointegration testing."""
    test_statistic: float
    pvalue: float
    critical_values: Dict[str, float]
    is_cointegrated: bool
    method: str
    hedge_ratio: Optional[float] = None
    residuals: Optional[pd.Series] = None
    r_squared: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StationarityResult:
    """Result of stationarity testing."""
    test_statistic: float
    pvalue: float
    critical_values: Dict[str, float]
    is_stationary: bool
    method: str
    lags_used: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SpreadAnalysis:
    """Comprehensive spread analysis results."""
    spread_series: pd.Series
    mean: float
    std: float
    volatility: float
    skewness: float
    kurtosis: float
    half_life: float
    stationarity_result: StationarityResult
    autocorrelation: pd.Series
    regime_changes: List[datetime]
    timestamp: datetime = field(default_factory=datetime.now)


class CorrelationAnalyzer:
    """Advanced correlation analysis for pairs trading."""
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level
    
    def calculate_correlation(self, 
                            series1: pd.Series, 
                            series2: pd.Series,
                            method: CorrelationType = CorrelationType.PEARSON) -> CorrelationResult:
        """Calculate correlation between two series.
        
        Args:
            series1: First time series
            series2: Second time series
            method: Correlation method
            
        Returns:
            CorrelationResult object
        """
        try:
            # Align series and remove NaN values
            aligned_data = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned_data) < 10:
                return CorrelationResult(
                    correlation=0.0, pvalue=1.0, confidence_interval=(0.0, 0.0),
                    method=method.value, sample_size=0, is_significant=False
                )
            
            x = aligned_data.iloc[:, 0].values
            y = aligned_data.iloc[:, 1].values
            n = len(x)
            
            # Calculate correlation based on method
            if method == CorrelationType.PEARSON:
                corr, pval = pearsonr(x, y)
            elif method == CorrelationType.SPEARMAN:
                corr, pval = spearmanr(x, y)
            elif method == CorrelationType.KENDALL:
                corr, pval = kendalltau(x, y)
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            # Calculate confidence interval for Pearson correlation
            if method == CorrelationType.PEARSON and n > 3:
                # Fisher transformation
                z = 0.5 * np.log((1 + corr) / (1 - corr))
                se = 1 / np.sqrt(n - 3)
                z_critical = stats.norm.ppf(1 - self.alpha / 2)
                
                z_lower = z - z_critical * se
                z_upper = z + z_critical * se
                
                # Transform back
                ci_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
                ci_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)
                confidence_interval = (ci_lower, ci_upper)
            else:
                confidence_interval = (corr - 0.1, corr + 0.1)  # Rough estimate
            
            return CorrelationResult(
                correlation=float(corr),
                pvalue=float(pval),
                confidence_interval=confidence_interval,
                method=method.value,
                sample_size=n,
                is_significant=pval < self.alpha
            )
        
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            return CorrelationResult(
                correlation=0.0, pvalue=1.0, confidence_interval=(0.0, 0.0),
                method=method.value, sample_size=0, is_significant=False
            )
    
    def rolling_correlation(self, 
                          series1: pd.Series, 
                          series2: pd.Series,
                          window: int = 30,
                          method: CorrelationType = CorrelationType.PEARSON) -> pd.Series:
        """Calculate rolling correlation between two series.
        
        Args:
            series1: First time series
            series2: Second time series
            window: Rolling window size
            method: Correlation method
            
        Returns:
            Rolling correlation series
        """
        try:
            # Align series
            aligned_data = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned_data) < window:
                return pd.Series(dtype=float)
            
            if method == CorrelationType.PEARSON:
                rolling_corr = aligned_data.iloc[:, 0].rolling(window).corr(aligned_data.iloc[:, 1])
            elif method == CorrelationType.SPEARMAN:
                # Manual calculation for Spearman rolling correlation
                rolling_corr = pd.Series(index=aligned_data.index, dtype=float)
                for i in range(window - 1, len(aligned_data)):
                    window_data = aligned_data.iloc[i - window + 1:i + 1]
                    corr, _ = spearmanr(window_data.iloc[:, 0], window_data.iloc[:, 1])
                    rolling_corr.iloc[i] = corr
            else:
                raise ValueError(f"Rolling correlation not supported for method: {method}")
            
            return rolling_corr
        
        except Exception as e:
            logger.warning(f"Error calculating rolling correlation: {e}")
            return pd.Series(dtype=float)
    
    def correlation_stability(self, 
                            series1: pd.Series, 
                            series2: pd.Series,
                            window: int = 30) -> Dict[str, float]:
        """Analyze correlation stability over time.
        
        Args:
            series1: First time series
            series2: Second time series
            window: Rolling window size
            
        Returns:
            Dictionary of stability metrics
        """
        try:
            rolling_corr = self.rolling_correlation(series1, series2, window)
            
            if rolling_corr.empty:
                return {}
            
            stability_metrics = {
                'mean_correlation': float(rolling_corr.mean()),
                'std_correlation': float(rolling_corr.std()),
                'min_correlation': float(rolling_corr.min()),
                'max_correlation': float(rolling_corr.max()),
                'correlation_range': float(rolling_corr.max() - rolling_corr.min()),
                'stability_ratio': float(rolling_corr.std() / abs(rolling_corr.mean())) if rolling_corr.mean() != 0 else float('inf'),
                'positive_correlation_pct': float((rolling_corr > 0).sum() / len(rolling_corr)),
                'strong_correlation_pct': float((abs(rolling_corr) > 0.7).sum() / len(rolling_corr))
            }
            
            return stability_metrics
        
        except Exception as e:
            logger.warning(f"Error analyzing correlation stability: {e}")
            return {}


class CointegrationTester:
    """Cointegration testing for pairs trading."""
    
    def __init__(self, confidence_level: float = 0.05):
        self.confidence_level = confidence_level
    
    def engle_granger_test(self, 
                          series1: pd.Series, 
                          series2: pd.Series) -> CointegrationResult:
        """Perform Engle-Granger cointegration test.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            CointegrationResult object
        """
        try:
            # Try to import statsmodels
            try:
                from statsmodels.tsa.stattools import coint
                from statsmodels.regression.linear_model import OLS
            except ImportError:
                logger.warning("statsmodels not available for cointegration testing")
                return CointegrationResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_cointegrated=False, method="engle_granger"
                )
            
            # Align series and remove NaN values
            aligned_data = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned_data) < 50:
                return CointegrationResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_cointegrated=False, method="engle_granger"
                )
            
            y = aligned_data.iloc[:, 0].values
            x = aligned_data.iloc[:, 1].values
            
            # Perform cointegration test
            score, pvalue, crit_values = coint(y, x)
            
            # Calculate hedge ratio using OLS
            model = OLS(y, x).fit()
            hedge_ratio = float(model.params[0])
            residuals = pd.Series(model.resid, index=aligned_data.index)
            r_squared = float(model.rsquared)
            
            # Format critical values
            critical_values = {
                '1%': float(crit_values[0]),
                '5%': float(crit_values[1]),
                '10%': float(crit_values[2])
            }
            
            return CointegrationResult(
                test_statistic=float(score),
                pvalue=float(pvalue),
                critical_values=critical_values,
                is_cointegrated=pvalue <= self.confidence_level,
                method="engle_granger",
                hedge_ratio=hedge_ratio,
                residuals=residuals,
                r_squared=r_squared
            )
        
        except Exception as e:
            logger.warning(f"Error in Engle-Granger test: {e}")
            return CointegrationResult(
                test_statistic=0.0, pvalue=1.0, critical_values={},
                is_cointegrated=False, method="engle_granger"
            )
    
    def johansen_test(self, 
                     series1: pd.Series, 
                     series2: pd.Series) -> CointegrationResult:
        """Perform Johansen cointegration test.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            CointegrationResult object
        """
        try:
            # Try to import statsmodels
            try:
                from statsmodels.tsa.vector_ar.vecm import coint_johansen
            except ImportError:
                logger.warning("statsmodels not available for Johansen test")
                return CointegrationResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_cointegrated=False, method="johansen"
                )
            
            # Align series and remove NaN values
            aligned_data = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned_data) < 50:
                return CointegrationResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_cointegrated=False, method="johansen"
                )
            
            # Perform Johansen test
            result = coint_johansen(aligned_data.values, det_order=0, k_ar_diff=1)
            
            # Extract results
            trace_stat = float(result.lr1[0])  # Trace statistic for r=0
            critical_values = {
                '10%': float(result.cvt[0, 0]),
                '5%': float(result.cvt[0, 1]),
                '1%': float(result.cvt[0, 2])
            }
            
            # Determine if cointegrated (trace statistic > critical value)
            is_cointegrated = trace_stat > critical_values['5%']
            
            # Estimate p-value (approximate)
            pvalue = 0.01 if trace_stat > critical_values['1%'] else \
                    0.05 if trace_stat > critical_values['5%'] else \
                    0.10 if trace_stat > critical_values['10%'] else 0.20
            
            return CointegrationResult(
                test_statistic=trace_stat,
                pvalue=pvalue,
                critical_values=critical_values,
                is_cointegrated=is_cointegrated,
                method="johansen"
            )
        
        except Exception as e:
            logger.warning(f"Error in Johansen test: {e}")
            return CointegrationResult(
                test_statistic=0.0, pvalue=1.0, critical_values={},
                is_cointegrated=False, method="johansen"
            )


class StationarityTester:
    """Stationarity testing for time series."""
    
    def __init__(self, confidence_level: float = 0.05):
        self.confidence_level = confidence_level
    
    def adf_test(self, series: pd.Series, maxlag: Optional[int] = None) -> StationarityResult:
        """Perform Augmented Dickey-Fuller test.
        
        Args:
            series: Time series to test
            maxlag: Maximum number of lags to use
            
        Returns:
            StationarityResult object
        """
        try:
            # Try to import statsmodels
            try:
                from statsmodels.tsa.stattools import adfuller
            except ImportError:
                logger.warning("statsmodels not available for ADF test")
                return StationarityResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_stationary=False, method="adf"
                )
            
            # Remove NaN values
            clean_series = series.dropna()
            if len(clean_series) < 20:
                return StationarityResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_stationary=False, method="adf"
                )
            
            # Perform ADF test
            result = adfuller(clean_series.values, maxlag=maxlag, autolag='AIC')
            
            critical_values = {
                '1%': float(result[4]['1%']),
                '5%': float(result[4]['5%']),
                '10%': float(result[4]['10%'])
            }
            
            return StationarityResult(
                test_statistic=float(result[0]),
                pvalue=float(result[1]),
                critical_values=critical_values,
                is_stationary=result[1] <= self.confidence_level,
                method="adf",
                lags_used=int(result[2])
            )
        
        except Exception as e:
            logger.warning(f"Error in ADF test: {e}")
            return StationarityResult(
                test_statistic=0.0, pvalue=1.0, critical_values={},
                is_stationary=False, method="adf"
            )
    
    def kpss_test(self, series: pd.Series, regression: str = 'c') -> StationarityResult:
        """Perform KPSS test.
        
        Args:
            series: Time series to test
            regression: Type of regression ('c' for constant, 'ct' for constant and trend)
            
        Returns:
            StationarityResult object
        """
        try:
            # Try to import statsmodels
            try:
                from statsmodels.tsa.stattools import kpss
            except ImportError:
                logger.warning("statsmodels not available for KPSS test")
                return StationarityResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_stationary=False, method="kpss"
                )
            
            # Remove NaN values
            clean_series = series.dropna()
            if len(clean_series) < 20:
                return StationarityResult(
                    test_statistic=0.0, pvalue=1.0, critical_values={},
                    is_stationary=False, method="kpss"
                )
            
            # Perform KPSS test
            result = kpss(clean_series.values, regression=regression)
            
            critical_values = {
                '10%': float(result[3]['10%']),
                '5%': float(result[3]['5%']),
                '2.5%': float(result[3]['2.5%']),
                '1%': float(result[3]['1%'])
            }
            
            # For KPSS, null hypothesis is stationarity
            # So we reject null (non-stationary) if p-value < alpha
            return StationarityResult(
                test_statistic=float(result[0]),
                pvalue=float(result[1]),
                critical_values=critical_values,
                is_stationary=result[1] > self.confidence_level,  # Opposite of ADF
                method="kpss",
                lags_used=int(result[2])
            )
        
        except Exception as e:
            logger.warning(f"Error in KPSS test: {e}")
            return StationarityResult(
                test_statistic=0.0, pvalue=1.0, critical_values={},
                is_stationary=False, method="kpss"
            )


class SpreadAnalyzer:
    """Comprehensive spread analysis for pairs trading."""
    
    def __init__(self):
        self.stationarity_tester = StationarityTester()
    
    def analyze_spread(self, 
                      series1: pd.Series, 
                      series2: pd.Series,
                      hedge_ratio: Optional[float] = None) -> SpreadAnalysis:
        """Perform comprehensive spread analysis.
        
        Args:
            series1: First time series
            series2: Second time series
            hedge_ratio: Optional hedge ratio (if None, will be calculated)
            
        Returns:
            SpreadAnalysis object
        """
        try:
            # Align series
            aligned_data = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned_data) < 30:
                return self._empty_spread_analysis()
            
            # Calculate hedge ratio if not provided
            if hedge_ratio is None:
                hedge_ratio = self._calculate_hedge_ratio(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])
            
            # Calculate spread
            spread = aligned_data.iloc[:, 0] - hedge_ratio * aligned_data.iloc[:, 1]
            spread.name = 'spread'
            
            # Basic statistics
            mean = float(spread.mean())
            std = float(spread.std())
            volatility = std / abs(mean) if mean != 0 else float('inf')
            skewness = float(spread.skew())
            kurtosis = float(spread.kurtosis())
            
            # Half-life calculation
            half_life = self._calculate_half_life(spread)
            
            # Stationarity test
            stationarity_result = self.stationarity_tester.adf_test(spread)
            
            # Autocorrelation
            autocorr = self._calculate_autocorrelation(spread)
            
            # Regime change detection
            regime_changes = self._detect_regime_changes(spread)
            
            return SpreadAnalysis(
                spread_series=spread,
                mean=mean,
                std=std,
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                half_life=half_life,
                stationarity_result=stationarity_result,
                autocorrelation=autocorr,
                regime_changes=regime_changes
            )
        
        except Exception as e:
            logger.warning(f"Error in spread analysis: {e}")
            return self._empty_spread_analysis()
    
    def _calculate_hedge_ratio(self, series1: pd.Series, series2: pd.Series) -> float:
        """Calculate optimal hedge ratio using OLS."""
        try:
            model = LinearRegression()
            X = series2.values.reshape(-1, 1)
            y = series1.values
            model.fit(X, y)
            return float(model.coef_[0])
        except:
            return 1.0
    
    def _calculate_half_life(self, spread: pd.Series) -> float:
        """Calculate mean reversion half-life."""
        try:
            # Use AR(1) model to estimate half-life
            spread_lag = spread.shift(1).dropna()
            spread_current = spread[1:]
            
            if len(spread_current) < 10:
                return float('inf')
            
            model = LinearRegression()
            X = spread_lag.values.reshape(-1, 1)
            y = spread_current.values
            model.fit(X, y)
            
            slope = model.coef_[0]
            if abs(slope) < 1 and slope != 0:
                half_life = -np.log(2) / np.log(abs(slope))
                return float(half_life)
            else:
                return float('inf')
        except:
            return float('inf')
    
    def _calculate_autocorrelation(self, spread: pd.Series, max_lags: int = 20) -> pd.Series:
        """Calculate autocorrelation function."""
        try:
            autocorr_values = []
            for lag in range(1, min(max_lags + 1, len(spread) // 4)):
                corr = spread.autocorr(lag=lag)
                autocorr_values.append(corr if not pd.isna(corr) else 0.0)
            
            return pd.Series(autocorr_values, index=range(1, len(autocorr_values) + 1))
        except:
            return pd.Series(dtype=float)
    
    def _detect_regime_changes(self, spread: pd.Series, window: int = 50) -> List[datetime]:
        """Detect regime changes in spread behavior."""
        try:
            if len(spread) < window * 2:
                return []
            
            regime_changes = []
            
            # Rolling statistics
            rolling_mean = spread.rolling(window).mean()
            rolling_std = spread.rolling(window).std()
            
            # Detect significant changes in mean or volatility
            mean_changes = abs(rolling_mean.diff()) > 2 * rolling_std
            std_changes = rolling_std.diff() > rolling_std.rolling(window).std()
            
            # Combine change signals
            change_points = mean_changes | std_changes
            
            # Extract timestamps of regime changes
            for timestamp in spread.index[change_points]:
                if isinstance(timestamp, datetime):
                    regime_changes.append(timestamp)
                else:
                    # Convert to datetime if needed
                    try:
                        regime_changes.append(pd.to_datetime(timestamp))
                    except:
                        continue
            
            return regime_changes
        except:
            return []
    
    def _empty_spread_analysis(self) -> SpreadAnalysis:
        """Return empty spread analysis for error cases."""
        return SpreadAnalysis(
            spread_series=pd.Series(dtype=float),
            mean=0.0,
            std=0.0,
            volatility=float('inf'),
            skewness=0.0,
            kurtosis=0.0,
            half_life=float('inf'),
            stationarity_result=StationarityResult(
                test_statistic=0.0, pvalue=1.0, critical_values={},
                is_stationary=False, method="adf"
            ),
            autocorrelation=pd.Series(dtype=float),
            regime_changes=[]
        )


class TimeSeriesAnalyzer:
    """Advanced time series analysis for pairs trading."""
    
    def __init__(self):
        self.correlation_analyzer = CorrelationAnalyzer()
        self.cointegration_tester = CointegrationTester()
        self.stationarity_tester = StationarityTester()
        self.spread_analyzer = SpreadAnalyzer()
    
    def comprehensive_analysis(self, 
                             series1: pd.Series, 
                             series2: pd.Series) -> Dict[str, Union[CorrelationResult, CointegrationResult, SpreadAnalysis]]:
        """Perform comprehensive time series analysis for a pair.
        
        Args:
            series1: First time series
            series2: Second time series
            
        Returns:
            Dictionary containing all analysis results
        """
        try:
            results = {}
            
            # Correlation analysis
            results['correlation_pearson'] = self.correlation_analyzer.calculate_correlation(
                series1, series2, CorrelationType.PEARSON
            )
            results['correlation_spearman'] = self.correlation_analyzer.calculate_correlation(
                series1, series2, CorrelationType.SPEARMAN
            )
            
            # Correlation stability
            results['correlation_stability'] = self.correlation_analyzer.correlation_stability(
                series1, series2
            )
            
            # Cointegration tests
            results['cointegration_eg'] = self.cointegration_tester.engle_granger_test(
                series1, series2
            )
            results['cointegration_johansen'] = self.cointegration_tester.johansen_test(
                series1, series2
            )
            
            # Individual stationarity tests
            results['stationarity_series1'] = self.stationarity_tester.adf_test(series1)
            results['stationarity_series2'] = self.stationarity_tester.adf_test(series2)
            
            # Spread analysis
            results['spread_analysis'] = self.spread_analyzer.analyze_spread(series1, series2)
            
            return results
        
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {}
    
    def generate_report(self, 
                       series1: pd.Series, 
                       series2: pd.Series,
                       symbol1: str = "Series1",
                       symbol2: str = "Series2") -> str:
        """Generate a comprehensive analysis report.
        
        Args:
            series1: First time series
            series2: Second time series
            symbol1: Name of first series
            symbol2: Name of second series
            
        Returns:
            Formatted analysis report
        """
        try:
            results = self.comprehensive_analysis(series1, series2)
            
            report = f"""
# Pairs Trading Analysis Report
## Pair: {symbol1} - {symbol2}
## Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Correlation Analysis
- Pearson Correlation: {results.get('correlation_pearson', {}).correlation:.4f} (p-value: {results.get('correlation_pearson', {}).pvalue:.4f})
- Spearman Correlation: {results.get('correlation_spearman', {}).correlation:.4f} (p-value: {results.get('correlation_spearman', {}).pvalue:.4f})
- Correlation Stability: {results.get('correlation_stability', {}).get('stability_ratio', 'N/A')}

### Cointegration Analysis
- Engle-Granger Test: {'Cointegrated' if results.get('cointegration_eg', {}).is_cointegrated else 'Not Cointegrated'} (p-value: {results.get('cointegration_eg', {}).pvalue:.4f})
- Johansen Test: {'Cointegrated' if results.get('cointegration_johansen', {}).is_cointegrated else 'Not Cointegrated'} (p-value: {results.get('cointegration_johansen', {}).pvalue:.4f})
- Hedge Ratio: {results.get('cointegration_eg', {}).hedge_ratio:.4f if results.get('cointegration_eg', {}).hedge_ratio else 'N/A'}

### Stationarity Analysis
- {symbol1} Stationarity: {'Stationary' if results.get('stationarity_series1', {}).is_stationary else 'Non-Stationary'} (ADF p-value: {results.get('stationarity_series1', {}).pvalue:.4f})
- {symbol2} Stationarity: {'Stationary' if results.get('stationarity_series2', {}).is_stationary else 'Non-Stationary'} (ADF p-value: {results.get('stationarity_series2', {}).pvalue:.4f})

### Spread Analysis
- Spread Mean: {results.get('spread_analysis', {}).mean:.4f}
- Spread Volatility: {results.get('spread_analysis', {}).volatility:.4f}
- Half-Life: {results.get('spread_analysis', {}).half_life:.2f} periods
- Spread Stationarity: {'Stationary' if results.get('spread_analysis', {}).stationarity_result.is_stationary else 'Non-Stationary'}
- Regime Changes Detected: {len(results.get('spread_analysis', {}).regime_changes)}

### Trading Recommendation
"""
            
            # Add trading recommendation
            corr_result = results.get('correlation_pearson', {})
            coint_result = results.get('cointegration_eg', {})
            spread_result = results.get('spread_analysis', {})
            
            if (abs(corr_result.correlation) > 0.7 and 
                coint_result.is_cointegrated and 
                spread_result.stationarity_result.is_stationary and
                spread_result.half_life < 30):
                recommendation = "STRONG BUY - Excellent pair for mean reversion strategy"
            elif (abs(corr_result.correlation) > 0.6 and 
                  coint_result.is_cointegrated):
                recommendation = "BUY - Good pair for pairs trading"
            elif abs(corr_result.correlation) > 0.5:
                recommendation = "HOLD - Moderate pair, monitor closely"
            else:
                recommendation = "AVOID - Poor statistical relationship"
            
            report += f"**{recommendation}**\n"
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating analysis report: {e}"