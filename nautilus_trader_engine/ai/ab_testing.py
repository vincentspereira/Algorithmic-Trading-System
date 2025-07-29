"""
A/B Testing Framework for ML Models
Statistical testing and comparison framework for trading models
"""

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
import logging
import numpy as np
from scipy import stats
import pandas as pd


class TestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficSplitMethod(Enum):
    """Traffic splitting methods"""
    RANDOM = "random"
    HASH_BASED = "hash_based"
    TIME_BASED = "time_based"
    FEATURE_BASED = "feature_based"


class StatisticalTest(Enum):
    """Statistical test types"""
    T_TEST = "t_test"
    MANN_WHITNEY = "mann_whitney"
    CHI_SQUARE = "chi_square"
    BOOTSTRAP = "bootstrap"
    BAYESIAN = "bayesian"


@dataclass
class ModelVariant:
    """Model variant in A/B test"""
    variant_id: str
    model_id: str
    model_version: str
    traffic_percentage: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not (0 <= self.traffic_percentage <= 100):
            raise ValueError("Traffic percentage must be between 0 and 100")


@dataclass
class TestMetric:
    """Metric definition for A/B test"""
    name: str
    description: str
    metric_type: str  # 'conversion', 'continuous', 'count'
    higher_is_better: bool = True
    minimum_detectable_effect: float = 0.05  # 5% minimum effect
    statistical_power: float = 0.8
    significance_level: float = 0.05
    
    def __post_init__(self):
        if not (0 < self.statistical_power < 1):
            raise ValueError("Statistical power must be between 0 and 1")
        if not (0 < self.significance_level < 1):
            raise ValueError("Significance level must be between 0 and 1")


@dataclass
class TestConfiguration:
    """A/B test configuration"""
    test_id: str
    name: str
    description: str
    variants: List[ModelVariant]
    metrics: List[TestMetric]
    traffic_split_method: TrafficSplitMethod = TrafficSplitMethod.RANDOM
    minimum_sample_size: int = 1000
    maximum_duration_days: int = 30
    early_stopping_enabled: bool = True
    confidence_threshold: float = 0.95
    
    def __post_init__(self):
        # Validate traffic percentages sum to 100
        total_traffic = sum(v.traffic_percentage for v in self.variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Traffic percentages must sum to 100, got {total_traffic}")
        
        # Ensure at least 2 variants
        if len(self.variants) < 2:
            raise ValueError("A/B test must have at least 2 variants")


@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    variant_id: str
    user_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatisticalResult:
    """Statistical test result"""
    metric_name: str
    test_type: StatisticalTest
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    power: float
    sample_size_a: int
    sample_size_b: int
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float


class ABTestManager:
    """
    A/B Testing Framework for ML Models
    
    Features:
    - Multiple traffic splitting strategies
    - Statistical significance testing
    - Early stopping mechanisms
    - Real-time monitoring
    - Bayesian analysis
    - Multi-armed bandit support
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Active tests
        self._active_tests: Dict[str, TestConfiguration] = {}
        self._test_results: Dict[str, List[TestResult]] = {}
        self._test_status: Dict[str, TestStatus] = {}
        
        # Traffic assignment cache
        self._assignment_cache: Dict[str, Dict[str, str]] = {}  # test_id -> user_id -> variant_id
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistical analyzers
        self._statistical_analyzers = {
            StatisticalTest.T_TEST: self._perform_t_test,
            StatisticalTest.MANN_WHITNEY: self._perform_mann_whitney,
            StatisticalTest.CHI_SQUARE: self._perform_chi_square,
            StatisticalTest.BOOTSTRAP: self._perform_bootstrap,
            StatisticalTest.BAYESIAN: self._perform_bayesian
        }
    
    async def start(self):
        """Start the A/B testing framework"""
        if self._running:
            return
        
        self._running = True
        
        # Start background monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        self.logger.info("A/B Testing framework started")
    
    async def stop(self):
        """Stop the A/B testing framework"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("A/B Testing framework stopped")
    
    async def create_test(self, config: TestConfiguration) -> str:
        """Create a new A/B test"""
        try:
            # Validate configuration
            self._validate_test_config(config)
            
            # Store test configuration
            self._active_tests[config.test_id] = config
            self._test_results[config.test_id] = []
            self._test_status[config.test_id] = TestStatus.DRAFT
            self._assignment_cache[config.test_id] = {}
            
            self.logger.info(f"Created A/B test: {config.test_id}")
            return config.test_id
            
        except Exception as e:
            self.logger.error(f"Failed to create A/B test: {e}")
            raise
    
    async def start_test(self, test_id: str):
        """Start an A/B test"""
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        if self._test_status[test_id] != TestStatus.DRAFT:
            raise ValueError(f"Test {test_id} is not in draft status")
        
        self._test_status[test_id] = TestStatus.RUNNING
        
        self.logger.info(f"Started A/B test: {test_id}")
    
    async def pause_test(self, test_id: str):
        """Pause an A/B test"""
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        if self._test_status[test_id] != TestStatus.RUNNING:
            raise ValueError(f"Test {test_id} is not running")
        
        self._test_status[test_id] = TestStatus.PAUSED
        
        self.logger.info(f"Paused A/B test: {test_id}")
    
    async def stop_test(self, test_id: str, reason: str = "Manual stop"):
        """Stop an A/B test"""
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        self._test_status[test_id] = TestStatus.COMPLETED
        
        # Perform final analysis
        analysis = await self.analyze_test(test_id)
        
        self.logger.info(f"Stopped A/B test: {test_id}, Reason: {reason}")
        return analysis
    
    async def assign_variant(self, test_id: str, user_id: str, context: Dict[str, Any] = None) -> str:
        """Assign user to a test variant"""
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        if self._test_status[test_id] != TestStatus.RUNNING:
            # Return control variant for non-running tests
            config = self._active_tests[test_id]
            return config.variants[0].variant_id
        
        # Check cache first
        if user_id in self._assignment_cache[test_id]:
            return self._assignment_cache[test_id][user_id]
        
        # Assign variant based on splitting method
        config = self._active_tests[test_id]
        variant_id = await self._assign_variant_by_method(config, user_id, context)
        
        # Cache assignment
        self._assignment_cache[test_id][user_id] = variant_id
        
        return variant_id
    
    async def record_result(self, result: TestResult):
        """Record a test result"""
        if result.test_id not in self._active_tests:
            raise ValueError(f"Test {result.test_id} not found")
        
        # Validate variant exists
        config = self._active_tests[result.test_id]
        variant_ids = [v.variant_id for v in config.variants]
        if result.variant_id not in variant_ids:
            raise ValueError(f"Variant {result.variant_id} not found in test {result.test_id}")
        
        # Store result
        self._test_results[result.test_id].append(result)
        
        self.logger.debug(f"Recorded result for test {result.test_id}, variant {result.variant_id}")
    
    async def analyze_test(self, test_id: str) -> Dict[str, Any]:
        """Perform statistical analysis of A/B test"""
        if test_id not in self._active_tests:
            raise ValueError(f"Test {test_id} not found")
        
        config = self._active_tests[test_id]
        results = self._test_results[test_id]
        
        if len(results) < 2:
            return {"error": "Insufficient data for analysis"}
        
        # Convert results to DataFrame for analysis
        df = self._results_to_dataframe(results)
        
        analysis = {
            "test_id": test_id,
            "status": self._test_status[test_id].value,
            "total_samples": len(results),
            "variants": {},
            "statistical_tests": {},
            "recommendations": []
        }
        
        # Analyze each variant
        for variant in config.variants:
            variant_data = df[df['variant_id'] == variant.variant_id]
            analysis["variants"][variant.variant_id] = {
                "sample_size": len(variant_data),
                "traffic_percentage": variant.traffic_percentage,
                "metrics": {}
            }
            
            # Calculate metrics for this variant
            for metric in config.metrics:
                if metric.name in variant_data.columns:
                    values = variant_data[metric.name].dropna()
                    if len(values) > 0:
                        analysis["variants"][variant.variant_id]["metrics"][metric.name] = {
                            "mean": float(values.mean()),
                            "std": float(values.std()),
                            "count": len(values),
                            "min": float(values.min()),
                            "max": float(values.max()),
                            "median": float(values.median())
                        }
        
        # Perform pairwise statistical tests
        if len(config.variants) >= 2:
            control_variant = config.variants[0]  # First variant is control
            
            for i, test_variant in enumerate(config.variants[1:], 1):
                for metric in config.metrics:
                    stat_result = await self._compare_variants(
                        df, control_variant.variant_id, test_variant.variant_id, metric
                    )
                    
                    if stat_result:
                        test_key = f"{control_variant.variant_id}_vs_{test_variant.variant_id}_{metric.name}"
                        analysis["statistical_tests"][test_key] = {
                            "metric": metric.name,
                            "control_variant": control_variant.variant_id,
                            "test_variant": test_variant.variant_id,
                            "p_value": stat_result.p_value,
                            "effect_size": stat_result.effect_size,
                            "confidence_interval": stat_result.confidence_interval,
                            "is_significant": stat_result.is_significant,
                            "statistical_power": stat_result.power,
                            "test_type": stat_result.test_type.value
                        }
        
        # Generate recommendations
        analysis["recommendations"] = await self._generate_recommendations(config, analysis)
        
        return analysis
    
    async def _assign_variant_by_method(self, config: TestConfiguration, user_id: str, context: Dict[str, Any] = None) -> str:
        """Assign variant based on splitting method"""
        if config.traffic_split_method == TrafficSplitMethod.RANDOM:
            return self._assign_random(config.variants)
        
        elif config.traffic_split_method == TrafficSplitMethod.HASH_BASED:
            return self._assign_hash_based(config.variants, user_id)
        
        elif config.traffic_split_method == TrafficSplitMethod.TIME_BASED:
            return self._assign_time_based(config.variants)
        
        elif config.traffic_split_method == TrafficSplitMethod.FEATURE_BASED:
            return self._assign_feature_based(config.variants, context or {})
        
        else:
            # Default to random
            return self._assign_random(config.variants)
    
    def _assign_random(self, variants: List[ModelVariant]) -> str:
        """Random assignment"""
        rand_val = np.random.random() * 100
        cumulative = 0
        
        for variant in variants:
            cumulative += variant.traffic_percentage
            if rand_val <= cumulative:
                return variant.variant_id
        
        # Fallback to last variant
        return variants[-1].variant_id
    
    def _assign_hash_based(self, variants: List[ModelVariant], user_id: str) -> str:
        """Hash-based deterministic assignment"""
        # Create hash of user_id
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
        
        cumulative = 0
        for variant in variants:
            cumulative += variant.traffic_percentage
            if hash_val < cumulative:
                return variant.variant_id
        
        return variants[-1].variant_id
    
    def _assign_time_based(self, variants: List[ModelVariant]) -> str:
        """Time-based assignment (e.g., alternating by hour)"""
        hour = datetime.now().hour
        variant_index = hour % len(variants)
        return variants[variant_index].variant_id
    
    def _assign_feature_based(self, variants: List[ModelVariant], context: Dict[str, Any]) -> str:
        """Feature-based assignment"""
        # Simple example: assign based on a feature value
        feature_value = context.get('segment', 'default')
        
        if feature_value == 'premium':
            # Premium users get first variant
            return variants[0].variant_id
        else:
            # Regular assignment for others
            return self._assign_random(variants)
    
    async def _compare_variants(self, df: pd.DataFrame, control_id: str, test_id: str, metric: TestMetric) -> Optional[StatisticalResult]:
        """Compare two variants statistically"""
        try:
            control_data = df[df['variant_id'] == control_id][metric.name].dropna()
            test_data = df[df['variant_id'] == test_id][metric.name].dropna()
            
            if len(control_data) < 10 or len(test_data) < 10:
                return None  # Insufficient data
            
            # Choose appropriate statistical test
            if metric.metric_type == 'continuous':
                # Check for normality
                _, p_control = stats.normaltest(control_data)
                _, p_test = stats.normaltest(test_data)
                
                if p_control > 0.05 and p_test > 0.05:
                    # Data is normal, use t-test
                    return await self._statistical_analyzers[StatisticalTest.T_TEST](
                        control_data, test_data, metric
                    )
                else:
                    # Non-normal data, use Mann-Whitney
                    return await self._statistical_analyzers[StatisticalTest.MANN_WHITNEY](
                        control_data, test_data, metric
                    )
            
            elif metric.metric_type == 'conversion':
                # Use chi-square test for conversion rates
                return await self._statistical_analyzers[StatisticalTest.CHI_SQUARE](
                    control_data, test_data, metric
                )
            
            else:
                # Default to bootstrap
                return await self._statistical_analyzers[StatisticalTest.BOOTSTRAP](
                    control_data, test_data, metric
                )
        
        except Exception as e:
            self.logger.error(f"Error comparing variants: {e}")
            return None
    
    async def _perform_t_test(self, control_data: pd.Series, test_data: pd.Series, metric: TestMetric) -> StatisticalResult:
        """Perform t-test"""
        statistic, p_value = stats.ttest_ind(control_data, test_data)
        
        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt(((len(control_data) - 1) * control_data.var() + 
                             (len(test_data) - 1) * test_data.var()) / 
                            (len(control_data) + len(test_data) - 2))
        effect_size = (test_data.mean() - control_data.mean()) / pooled_std
        
        # Calculate confidence interval
        se = pooled_std * np.sqrt(1/len(control_data) + 1/len(test_data))
        df = len(control_data) + len(test_data) - 2
        t_critical = stats.t.ppf(1 - metric.significance_level/2, df)
        margin_error = t_critical * se
        
        mean_diff = test_data.mean() - control_data.mean()
        ci_lower = mean_diff - margin_error
        ci_upper = mean_diff + margin_error
        
        # Calculate statistical power
        power = self._calculate_power(control_data, test_data, metric.significance_level)
        
        return StatisticalResult(
            metric_name=metric.name,
            test_type=StatisticalTest.T_TEST,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < metric.significance_level,
            power=power,
            sample_size_a=len(control_data),
            sample_size_b=len(test_data),
            mean_a=control_data.mean(),
            mean_b=test_data.mean(),
            std_a=control_data.std(),
            std_b=test_data.std()
        )
    
    async def _perform_mann_whitney(self, control_data: pd.Series, test_data: pd.Series, metric: TestMetric) -> StatisticalResult:
        """Perform Mann-Whitney U test"""
        statistic, p_value = stats.mannwhitneyu(control_data, test_data, alternative='two-sided')
        
        # Calculate effect size (rank-biserial correlation)
        n1, n2 = len(control_data), len(test_data)
        effect_size = 1 - (2 * statistic) / (n1 * n2)
        
        # Bootstrap confidence interval for median difference
        n_bootstrap = 1000
        bootstrap_diffs = []
        
        for _ in range(n_bootstrap):
            boot_control = np.random.choice(control_data, size=len(control_data), replace=True)
            boot_test = np.random.choice(test_data, size=len(test_data), replace=True)
            bootstrap_diffs.append(np.median(boot_test) - np.median(boot_control))
        
        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)
        
        return StatisticalResult(
            metric_name=metric.name,
            test_type=StatisticalTest.MANN_WHITNEY,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < metric.significance_level,
            power=0.8,  # Approximate
            sample_size_a=len(control_data),
            sample_size_b=len(test_data),
            mean_a=control_data.mean(),
            mean_b=test_data.mean(),
            std_a=control_data.std(),
            std_b=test_data.std()
        )
    
    async def _perform_chi_square(self, control_data: pd.Series, test_data: pd.Series, metric: TestMetric) -> StatisticalResult:
        """Perform chi-square test for conversion rates"""
        # Assume binary data (0/1 for conversion)
        control_conversions = control_data.sum()
        control_total = len(control_data)
        test_conversions = test_data.sum()
        test_total = len(test_data)
        
        # Create contingency table
        contingency = np.array([
            [control_conversions, control_total - control_conversions],
            [test_conversions, test_total - test_conversions]
        ])
        
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        
        # Calculate effect size (Cramér's V)
        n = contingency.sum()
        effect_size = np.sqrt(chi2 / (n * (min(contingency.shape) - 1)))
        
        # Calculate confidence interval for difference in proportions
        p1 = control_conversions / control_total
        p2 = test_conversions / test_total
        
        se = np.sqrt(p1 * (1 - p1) / control_total + p2 * (1 - p2) / test_total)
        z_critical = stats.norm.ppf(1 - metric.significance_level/2)
        margin_error = z_critical * se
        
        diff = p2 - p1
        ci_lower = diff - margin_error
        ci_upper = diff + margin_error
        
        return StatisticalResult(
            metric_name=metric.name,
            test_type=StatisticalTest.CHI_SQUARE,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < metric.significance_level,
            power=0.8,  # Approximate
            sample_size_a=control_total,
            sample_size_b=test_total,
            mean_a=p1,
            mean_b=p2,
            std_a=np.sqrt(p1 * (1 - p1)),
            std_b=np.sqrt(p2 * (1 - p2))
        )
    
    async def _perform_bootstrap(self, control_data: pd.Series, test_data: pd.Series, metric: TestMetric) -> StatisticalResult:
        """Perform bootstrap test"""
        n_bootstrap = 10000
        
        # Calculate observed difference
        observed_diff = test_data.mean() - control_data.mean()
        
        # Bootstrap under null hypothesis
        combined_data = np.concatenate([control_data, test_data])
        bootstrap_diffs = []
        
        for _ in range(n_bootstrap):
            # Resample under null hypothesis
            boot_combined = np.random.choice(combined_data, size=len(combined_data), replace=True)
            boot_control = boot_combined[:len(control_data)]
            boot_test = boot_combined[len(control_data):]
            
            bootstrap_diffs.append(boot_test.mean() - boot_control.mean())
        
        # Calculate p-value
        p_value = np.mean(np.abs(bootstrap_diffs) >= np.abs(observed_diff))
        
        # Effect size (standardized mean difference)
        pooled_std = np.sqrt((control_data.var() + test_data.var()) / 2)
        effect_size = observed_diff / pooled_std
        
        # Confidence interval
        ci_lower = np.percentile(bootstrap_diffs, 2.5)
        ci_upper = np.percentile(bootstrap_diffs, 97.5)
        
        return StatisticalResult(
            metric_name=metric.name,
            test_type=StatisticalTest.BOOTSTRAP,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < metric.significance_level,
            power=0.8,  # Approximate
            sample_size_a=len(control_data),
            sample_size_b=len(test_data),
            mean_a=control_data.mean(),
            mean_b=test_data.mean(),
            std_a=control_data.std(),
            std_b=test_data.std()
        )
    
    async def _perform_bayesian(self, control_data: pd.Series, test_data: pd.Series, metric: TestMetric) -> StatisticalResult:
        """Perform Bayesian analysis"""
        # Simple Bayesian t-test approximation
        # In practice, you'd use more sophisticated Bayesian methods
        
        # Prior parameters (non-informative)
        prior_mean = 0
        prior_precision = 0.001
        
        # Posterior parameters for control
        n_control = len(control_data)
        mean_control = control_data.mean()
        var_control = control_data.var()
        
        posterior_precision_control = prior_precision + n_control / var_control
        posterior_mean_control = (prior_precision * prior_mean + n_control * mean_control / var_control) / posterior_precision_control
        
        # Posterior parameters for test
        n_test = len(test_data)
        mean_test = test_data.mean()
        var_test = test_data.var()
        
        posterior_precision_test = prior_precision + n_test / var_test
        posterior_mean_test = (prior_precision * prior_mean + n_test * mean_test / var_test) / posterior_precision_test
        
        # Probability that test > control
        diff_mean = posterior_mean_test - posterior_mean_control
        diff_var = 1/posterior_precision_test + 1/posterior_precision_control
        
        # Approximate p-value
        z_score = diff_mean / np.sqrt(diff_var)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        # Effect size
        effect_size = diff_mean / np.sqrt((var_control + var_test) / 2)
        
        # Credible interval
        ci_lower = diff_mean - 1.96 * np.sqrt(diff_var)
        ci_upper = diff_mean + 1.96 * np.sqrt(diff_var)
        
        return StatisticalResult(
            metric_name=metric.name,
            test_type=StatisticalTest.BAYESIAN,
            p_value=p_value,
            effect_size=effect_size,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < metric.significance_level,
            power=0.8,  # Approximate
            sample_size_a=len(control_data),
            sample_size_b=len(test_data),
            mean_a=control_data.mean(),
            mean_b=test_data.mean(),
            std_a=control_data.std(),
            std_b=test_data.std()
        )
    
    def _calculate_power(self, control_data: pd.Series, test_data: pd.Series, alpha: float) -> float:
        """Calculate statistical power"""
        try:
            from statsmodels.stats.power import ttest_power
            
            # Calculate effect size
            pooled_std = np.sqrt((control_data.var() + test_data.var()) / 2)
            effect_size = abs(test_data.mean() - control_data.mean()) / pooled_std
            
            # Calculate power
            power = ttest_power(effect_size, len(control_data), alpha, alternative='two-sided')
            return power
        except ImportError:
            # Fallback approximation
            return 0.8
    
    def _results_to_dataframe(self, results: List[TestResult]) -> pd.DataFrame:
        """Convert test results to DataFrame"""
        data = []
        for result in results:
            row = {
                'test_id': result.test_id,
                'variant_id': result.variant_id,
                'user_id': result.user_id,
                'timestamp': result.timestamp
            }
            row.update(result.metrics)
            row.update(result.metadata)
            data.append(row)
        
        return pd.DataFrame(data)
    
    async def _generate_recommendations(self, config: TestConfiguration, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check sample sizes
        total_samples = analysis["total_samples"]
        if total_samples < config.minimum_sample_size:
            recommendations.append(f"Insufficient sample size: {total_samples} < {config.minimum_sample_size}")
        
        # Check for significant results
        significant_tests = [
            test for test in analysis["statistical_tests"].values()
            if test["is_significant"]
        ]
        
        if significant_tests:
            recommendations.append(f"Found {len(significant_tests)} statistically significant results")
            
            # Find best performing variant
            best_variants = {}
            for test in significant_tests:
                metric = test["metric"]
                if test["effect_size"] > 0:  # Test variant is better
                    best_variants[metric] = test["test_variant"]
                else:  # Control variant is better
                    best_variants[metric] = test["control_variant"]
            
            if best_variants:
                recommendations.append(f"Best performing variants: {best_variants}")
        else:
            recommendations.append("No statistically significant differences found")
        
        # Check for early stopping
        if config.early_stopping_enabled:
            for test in analysis["statistical_tests"].values():
                if test["is_significant"] and test["statistical_power"] > 0.8:
                    recommendations.append(f"Consider early stopping for metric {test['metric']}")
        
        return recommendations
    
    def _validate_test_config(self, config: TestConfiguration):
        """Validate test configuration"""
        # Already validated in TestConfiguration.__post_init__
        pass
    
    async def _monitoring_worker(self):
        """Background worker for monitoring tests"""
        while self._running:
            try:
                for test_id in list(self._active_tests.keys()):
                    if self._test_status[test_id] == TestStatus.RUNNING:
                        await self._check_test_conditions(test_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring worker error: {e}")
                await asyncio.sleep(60)
    
    async def _check_test_conditions(self, test_id: str):
        """Check test conditions for early stopping or completion"""
        config = self._active_tests[test_id]
        results = self._test_results[test_id]
        
        # Check maximum duration
        if len(results) > 0:
            first_result_time = min(r.timestamp for r in results)
            duration = datetime.now() - first_result_time
            
            if duration.days >= config.maximum_duration_days:
                await self.stop_test(test_id, "Maximum duration reached")
                return
        
        # Check for early stopping
        if config.early_stopping_enabled and len(results) >= config.minimum_sample_size:
            analysis = await self.analyze_test(test_id)
            
            # Check if any metric has strong significance
            for test_result in analysis.get("statistical_tests", {}).values():
                if (test_result["is_significant"] and 
                    test_result["statistical_power"] > 0.9 and
                    test_result["p_value"] < 0.01):
                    
                    await self.stop_test(test_id, f"Early stopping: strong significance for {test_result['metric']}")
                    return
    
    def get_test_status(self, test_id: str) -> Optional[TestStatus]:
        """Get test status"""
        return self._test_status.get(test_id)
    
    def get_active_tests(self) -> List[str]:
        """Get list of active test IDs"""
        return [
            test_id for test_id, status in self._test_status.items()
            if status in [TestStatus.RUNNING, TestStatus.PAUSED]
        ]
    
    def get_test_config(self, test_id: str) -> Optional[TestConfiguration]:
        """Get test configuration"""
        return self._active_tests.get(test_id)
    
    async def get_test_summary(self, test_id: str) -> Dict[str, Any]:
        """Get test summary"""
        if test_id not in self._active_tests:
            return {"error": "Test not found"}
        
        config = self._active_tests[test_id]
        results = self._test_results[test_id]
        status = self._test_status[test_id]
        
        return {
            "test_id": test_id,
            "name": config.name,
            "status": status.value,
            "variants": len(config.variants),
            "metrics": len(config.metrics),
            "total_results": len(results),
            "start_time": min(r.timestamp for r in results) if results else None,
            "last_result_time": max(r.timestamp for r in results) if results else None
        }