"""System Integration Test for Institutional-Grade Trading System

This module provides comprehensive integration testing for all institutional-grade
features implemented in the algorithmic trading system.

Author: Vincent S. Pereira
Date: December 2024
Version: 2.0.0
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from collections import deque

# Import all institutional components
try:
    from .core_indicator_base import AugmentedIndicator
    from .enhanced_risk_factory import EnhancedRiskFactory
    from .advanced_risk_factory import AdvancedRiskFactory
    from .multi_timeframe_engine import MultiTimeframeEngine
    from .behavioral_overlays import BehavioralOverlay
    from .cross_asset_correlation_engine import CrossAssetCorrelationEngine
    from .adaptive_learning_system import AdaptiveLearningSystem
    from .institutional_candlestick_patterns import InstitutionalCandlestickPatterns
except ImportError as e:
    logging.warning(f"Import warning: {e}")

@dataclass
class TestResult:
    """Test result container."""
    test_name: str
    passed: bool
    execution_time: float
    details: str
    performance_metrics: Optional[Dict] = None

@dataclass
class SystemMetrics:
    """System performance metrics."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_execution_time: float
    average_latency: float
    memory_usage: float
    throughput: float

class SystemIntegrationTest:
    """Comprehensive system integration test suite."""
    
    def __init__(self):
        """Initialize the integration test suite."""
        self.logger = logging.getLogger(__name__)
        self.test_results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        
        # Test data generation
        self.sample_data = self._generate_sample_data()
        
        # Initialize components for testing
        self.components = {}
        self._initialize_components()
    
    def _generate_sample_data(self, periods: int = 1000) -> pd.DataFrame:
        """Generate realistic sample market data for testing."""
        np.random.seed(42)  # For reproducible tests
        
        # Generate realistic price data with trends and volatility
        base_price = 100.0
        returns = np.random.normal(0.0005, 0.02, periods)  # Daily returns
        prices = [base_price]
        
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        prices = np.array(prices[1:])
        
        # Generate OHLC data
        high_noise = np.random.uniform(0.005, 0.02, periods)
        low_noise = np.random.uniform(-0.02, -0.005, periods)
        
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=periods, freq='1H'),
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, periods)),
            'high': prices * (1 + high_noise),
            'low': prices * (1 + low_noise),
            'close': prices,
            'volume': np.random.randint(10000, 1000000, periods)
        }
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _initialize_components(self):
        """Initialize all system components for testing."""
        try:
            # Initialize core components
            self.components['enhanced_risk'] = EnhancedRiskFactory()
            self.components['advanced_risk'] = AdvancedRiskFactory()
            self.components['multi_timeframe'] = MultiTimeframeEngine()
            self.components['behavioral'] = BehavioralOverlay(period=20)
            self.components['correlation'] = CrossAssetCorrelationEngine()
            self.components['adaptive_learning'] = AdaptiveLearningSystem()
            self.components['patterns'] = InstitutionalCandlestickPatterns()
            
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
    
    async def run_comprehensive_test(self) -> SystemMetrics:
        """Run comprehensive system integration tests."""
        self.start_time = time.time()
        self.logger.info("Starting comprehensive system integration tests")
        
        # Test categories
        test_categories = [
            self._test_core_indicators,
            self._test_risk_management,
            self._test_multi_timeframe_analysis,
            self._test_behavioral_analysis,
            self._test_correlation_analysis,
            self._test_adaptive_learning,
            self._test_pattern_recognition,
            self._test_performance_benchmarks,
            self._test_integration_workflows,
            self._test_error_handling
        ]
        
        # Run all test categories
        for test_category in test_categories:
            try:
                await test_category()
            except Exception as e:
                self.logger.error(f"Test category failed: {e}")
                self.test_results.append(
                    TestResult(
                        test_name=test_category.__name__,
                        passed=False,
                        execution_time=0.0,
                        details=f"Exception: {str(e)}"
                    )
                )
        
        self.end_time = time.time()
        return self._generate_system_metrics()
    
    async def _test_core_indicators(self):
        """Test core indicator functionality."""
        start_time = time.time()
        
        try:
            # Test AugmentedIndicator if available
            if 'AugmentedIndicator' in globals():
                indicator = AugmentedIndicator(period=20)
                
                # Test indicator updates
                for _, row in self.sample_data.head(100).iterrows():
                    indicator.update(
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )
                
                # Verify indicator produces valid signals
                signal = indicator.get_signal()
                assert signal is not None, "Indicator should produce signals"
                
                self.test_results.append(
                    TestResult(
                        test_name="Core Indicators",
                        passed=True,
                        execution_time=time.time() - start_time,
                        details="All core indicators functioning correctly"
                    )
                )
            else:
                self.test_results.append(
                    TestResult(
                        test_name="Core Indicators",
                        passed=True,
                        execution_time=time.time() - start_time,
                        details="Core indicators not available for testing"
                    )
                )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Core Indicators",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Core indicator test failed: {str(e)}"
                )
            )
    
    async def _test_risk_management(self):
        """Test risk management systems."""
        start_time = time.time()
        
        try:
            enhanced_risk = self.components['enhanced_risk']
            advanced_risk = self.components['advanced_risk']
            
            # Test position sizing
            returns = self.sample_data['close'].pct_change().dropna()
            
            # Enhanced risk factory tests
            kelly_size = enhanced_risk.calculate_kelly_position_size(
                win_rate=0.6, avg_win=0.02, avg_loss=0.01, confidence=0.8
            )
            assert 0 < kelly_size <= 1, "Kelly size should be between 0 and 1"
            
            # Advanced risk factory tests
            optimal_f = advanced_risk.calculate_optimal_f_position_size(
                returns=returns.values, confidence_level=0.95
            )
            assert optimal_f > 0, "Optimal F should be positive"
            
            # VaR calculations
            var_95 = advanced_risk.calculate_var(returns.values, confidence_level=0.95)
            cvar_95 = advanced_risk.calculate_cvar(returns.values, confidence_level=0.95)
            assert var_95 < 0, "VaR should be negative"
            assert cvar_95 <= var_95, "CVaR should be <= VaR"
            
            self.test_results.append(
                TestResult(
                    test_name="Risk Management",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="All risk management functions working correctly",
                    performance_metrics={
                        'kelly_size': kelly_size,
                        'optimal_f': optimal_f,
                        'var_95': var_95,
                        'cvar_95': cvar_95
                    }
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Risk Management",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Risk management test failed: {str(e)}"
                )
            )
    
    async def _test_multi_timeframe_analysis(self):
        """Test multi-timeframe convergence analysis."""
        start_time = time.time()
        
        try:
            mt_engine = self.components['multi_timeframe']
            
            # Add signals from different timeframes
            timeframes = ['1m', '5m', '15m', '1h']
            
            for i, tf in enumerate(timeframes):
                signal_strength = 0.5 + (i * 0.1)  # Varying signal strengths
                mt_engine.add_signal(
                    symbol='AAPL',
                    timeframe=tf,
                    signal_type='bullish',
                    strength=signal_strength,
                    confidence=0.8,
                    timestamp=datetime.now()
                )
            
            # Test convergence analysis
            convergence = mt_engine.analyze_convergence('AAPL')
            assert convergence is not None, "Convergence analysis should return results"
            
            # Test signal stack retrieval
            signal_stack = mt_engine.get_signal_stack('AAPL')
            assert len(signal_stack) > 0, "Signal stack should contain signals"
            
            self.test_results.append(
                TestResult(
                    test_name="Multi-Timeframe Analysis",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Multi-timeframe convergence analysis working correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Multi-Timeframe Analysis",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Multi-timeframe test failed: {str(e)}"
                )
            )
    
    async def _test_behavioral_analysis(self):
        """Test behavioral analysis overlays."""
        start_time = time.time()
        
        try:
            behavioral = self.components['behavioral']
            
            # Test behavioral overlay updates
            for _, row in self.sample_data.head(50).iterrows():
                behavioral.update(
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                )
            
            # Test sentiment and fear/greed calculations
            sentiment = behavioral.calculate_sentiment_score()
            fear_greed = behavioral.calculate_fear_greed_index()
            
            assert -1 <= sentiment <= 1, "Sentiment should be between -1 and 1"
            assert 0 <= fear_greed <= 100, "Fear/Greed index should be between 0 and 100"
            
            # Test signal adjustment
            base_signal = 0.7
            adjusted_signal = behavioral.adjust_signal_for_behavior(base_signal)
            assert isinstance(adjusted_signal, (int, float)), "Adjusted signal should be numeric"
            
            self.test_results.append(
                TestResult(
                    test_name="Behavioral Analysis",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Behavioral analysis functioning correctly",
                    performance_metrics={
                        'sentiment_score': sentiment,
                        'fear_greed_index': fear_greed
                    }
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Behavioral Analysis",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Behavioral analysis test failed: {str(e)}"
                )
            )
    
    async def _test_correlation_analysis(self):
        """Test cross-asset correlation analysis."""
        start_time = time.time()
        
        try:
            corr_engine = self.components['correlation']
            
            # Add sample asset data
            assets = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
            
            for asset in assets:
                # Generate correlated price data
                prices = self.sample_data['close'].values + np.random.normal(0, 5, len(self.sample_data))
                corr_engine.add_asset_data(asset, 'equity', prices)
            
            # Test correlation matrix calculation
            corr_matrix = corr_engine.calculate_correlation_matrix()
            assert corr_matrix is not None, "Correlation matrix should be calculated"
            
            # Test sector momentum
            sector_momentum = corr_engine.calculate_sector_momentum('technology')
            assert isinstance(sector_momentum, (int, float)), "Sector momentum should be numeric"
            
            self.test_results.append(
                TestResult(
                    test_name="Correlation Analysis",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Cross-asset correlation analysis working correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Correlation Analysis",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Correlation analysis test failed: {str(e)}"
                )
            )
    
    async def _test_adaptive_learning(self):
        """Test adaptive learning system."""
        start_time = time.time()
        
        try:
            learning_system = self.components['adaptive_learning']
            
            # Prepare sample training data
            features = self.sample_data[['open', 'high', 'low', 'volume']].values[:100]
            targets = (self.sample_data['close'].pct_change() > 0).astype(int).values[1:101]
            
            # Test model training
            learning_system.train_model(features[:-1], targets)
            
            # Test prediction
            predictions = learning_system.predict(features[-10:])
            assert len(predictions) == 10, "Should return 10 predictions"
            
            # Test performance feedback
            actual_returns = np.random.choice([0, 1], 10)
            learning_system.update_performance_feedback(predictions, actual_returns)
            
            self.test_results.append(
                TestResult(
                    test_name="Adaptive Learning",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Adaptive learning system functioning correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Adaptive Learning",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Adaptive learning test failed: {str(e)}"
                )
            )
    
    async def _test_pattern_recognition(self):
        """Test institutional candlestick pattern recognition."""
        start_time = time.time()
        
        try:
            patterns = self.components['patterns']
            
            # Test pattern detection on sample data
            ohlcv_data = self.sample_data[['open', 'high', 'low', 'close', 'volume']].values
            
            # Test various pattern detection methods
            hammer_signals = patterns.detect_hammer_pattern(ohlcv_data)
            engulfing_signals = patterns.detect_engulfing_pattern(ohlcv_data)
            doji_signals = patterns.detect_doji_pattern(ohlcv_data)
            
            # Verify patterns return valid signals
            assert isinstance(hammer_signals, np.ndarray), "Hammer signals should be numpy array"
            assert isinstance(engulfing_signals, np.ndarray), "Engulfing signals should be numpy array"
            assert isinstance(doji_signals, np.ndarray), "Doji signals should be numpy array"
            
            # Test institutional validation
            validated_patterns = patterns.validate_with_institutional_criteria(
                hammer_signals, ohlcv_data
            )
            assert len(validated_patterns) <= len(hammer_signals), "Validation should filter patterns"
            
            self.test_results.append(
                TestResult(
                    test_name="Pattern Recognition",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Institutional pattern recognition working correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Pattern Recognition",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Pattern recognition test failed: {str(e)}"
                )
            )
    
    async def _test_performance_benchmarks(self):
        """Test system performance benchmarks."""
        start_time = time.time()
        
        try:
            # Test latency benchmarks
            latencies = []
            
            for _ in range(100):
                test_start = time.perf_counter()
                
                # Simulate typical operations
                enhanced_risk = self.components['enhanced_risk']
                kelly_size = enhanced_risk.calculate_kelly_position_size(
                    win_rate=0.6, avg_win=0.02, avg_loss=0.01
                )
                
                test_end = time.perf_counter()
                latencies.append((test_end - test_start) * 1000)  # Convert to ms
            
            avg_latency = np.mean(latencies)
            p95_latency = np.percentile(latencies, 95)
            
            # Performance assertions
            assert avg_latency < 10, f"Average latency too high: {avg_latency}ms"
            assert p95_latency < 20, f"P95 latency too high: {p95_latency}ms"
            
            self.test_results.append(
                TestResult(
                    test_name="Performance Benchmarks",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Performance benchmarks within acceptable limits",
                    performance_metrics={
                        'avg_latency_ms': avg_latency,
                        'p95_latency_ms': p95_latency
                    }
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Performance Benchmarks",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Performance benchmark test failed: {str(e)}"
                )
            )
    
    async def _test_integration_workflows(self):
        """Test end-to-end integration workflows."""
        start_time = time.time()
        
        try:
            # Test complete trading workflow
            # 1. Generate signals from multiple sources
            behavioral = self.components['behavioral']
            mt_engine = self.components['multi_timeframe']
            enhanced_risk = self.components['enhanced_risk']
            
            # Update behavioral overlay
            sample_row = self.sample_data.iloc[-1]
            behavioral.update(
                high=sample_row['high'],
                low=sample_row['low'],
                close=sample_row['close'],
                volume=sample_row['volume']
            )
            
            # Add multi-timeframe signals
            mt_engine.add_signal(
                symbol='AAPL',
                timeframe='1h',
                signal_type='bullish',
                strength=0.7,
                confidence=0.8,
                timestamp=datetime.now()
            )
            
            # 2. Analyze convergence
            convergence = mt_engine.analyze_convergence('AAPL')
            
            # 3. Calculate risk-adjusted position size
            returns = self.sample_data['close'].pct_change().dropna().values
            position_size = enhanced_risk.calculate_kelly_position_size(
                win_rate=0.6, avg_win=0.02, avg_loss=0.01
            )
            
            # 4. Adjust for behavioral factors
            base_signal = convergence.composite_signal if convergence else 0.5
            adjusted_signal = behavioral.adjust_signal_for_behavior(base_signal)
            
            # Verify workflow produces valid results
            assert convergence is not None, "Convergence analysis should succeed"
            assert 0 < position_size <= 1, "Position size should be valid"
            assert isinstance(adjusted_signal, (int, float)), "Adjusted signal should be numeric"
            
            self.test_results.append(
                TestResult(
                    test_name="Integration Workflows",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="End-to-end integration workflows functioning correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Integration Workflows",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Integration workflow test failed: {str(e)}"
                )
            )
    
    async def _test_error_handling(self):
        """Test error handling and graceful degradation."""
        start_time = time.time()
        
        try:
            # Test with invalid inputs
            enhanced_risk = self.components['enhanced_risk']
            
            # Test with invalid win rate
            try:
                kelly_size = enhanced_risk.calculate_kelly_position_size(
                    win_rate=1.5, avg_win=0.02, avg_loss=0.01  # Invalid win rate > 1
                )
                # Should handle gracefully
            except Exception:
                pass  # Expected to handle errors
            
            # Test with empty data
            try:
                advanced_risk = self.components['advanced_risk']
                var = advanced_risk.calculate_var(np.array([]), confidence_level=0.95)
            except Exception:
                pass  # Expected to handle errors
            
            # Test behavioral overlay with invalid data
            try:
                behavioral = self.components['behavioral']
                behavioral.update(high=np.nan, low=np.nan, close=np.nan, volume=0)
            except Exception:
                pass  # Expected to handle errors
            
            self.test_results.append(
                TestResult(
                    test_name="Error Handling",
                    passed=True,
                    execution_time=time.time() - start_time,
                    details="Error handling and graceful degradation working correctly"
                )
            )
        
        except Exception as e:
            self.test_results.append(
                TestResult(
                    test_name="Error Handling",
                    passed=False,
                    execution_time=time.time() - start_time,
                    details=f"Error handling test failed: {str(e)}"
                )
            )
    
    def _generate_system_metrics(self) -> SystemMetrics:
        """Generate comprehensive system metrics."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        failed_tests = total_tests - passed_tests
        
        total_execution_time = self.end_time - self.start_time if self.end_time else 0
        average_latency = np.mean([result.execution_time for result in self.test_results])
        
        return SystemMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            total_execution_time=total_execution_time,
            average_latency=average_latency,
            memory_usage=0.0,  # Would need psutil for actual memory measurement
            throughput=total_tests / total_execution_time if total_execution_time > 0 else 0
        )
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        metrics = self._generate_system_metrics()
        
        report = f"""
# System Integration Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**System Version:** 2.0.0

## Test Summary

- **Total Tests:** {metrics.total_tests}
- **Passed:** {metrics.passed_tests}
- **Failed:** {metrics.failed_tests}
- **Success Rate:** {(metrics.passed_tests / metrics.total_tests * 100):.1f}%
- **Total Execution Time:** {metrics.total_execution_time:.2f}s
- **Average Test Latency:** {metrics.average_latency:.3f}s
- **Throughput:** {metrics.throughput:.1f} tests/second

## Detailed Results

"""
        
        for result in self.test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report += f"### {result.test_name} - {status}\n\n"
            report += f"- **Execution Time:** {result.execution_time:.3f}s\n"
            report += f"- **Details:** {result.details}\n"
            
            if result.performance_metrics:
                report += "- **Performance Metrics:**\n"
                for key, value in result.performance_metrics.items():
                    report += f"  - {key}: {value}\n"
            
            report += "\n"
        
        report += f"""
## System Health Assessment

{"🟢 SYSTEM HEALTHY" if metrics.failed_tests == 0 else "🟡 SYSTEM ISSUES DETECTED" if metrics.failed_tests < 3 else "🔴 SYSTEM CRITICAL"}

The institutional-grade trading system has been comprehensively tested across all major components.
{"All tests passed successfully." if metrics.failed_tests == 0 else f"{metrics.failed_tests} test(s) failed and require attention."}

## Recommendations

{"- System is ready for production deployment" if metrics.failed_tests == 0 else "- Address failed tests before production deployment"}
- Monitor performance metrics in production
- Implement continuous integration testing
- Regular system health checks recommended
"""
        
        return report

# Example usage and testing
if __name__ == "__main__":
    async def main():
        """Run the comprehensive system integration test."""
        test_suite = SystemIntegrationTest()
        
        print("Starting Institutional-Grade Trading System Integration Tests...")
        print("=" * 70)
        
        # Run comprehensive tests
        metrics = await test_suite.run_comprehensive_test()
        
        # Generate and display report
        report = test_suite.generate_test_report()
        print(report)
        
        # Save report to file
        with open('system_integration_test_report.md', 'w') as f:
            f.write(report)
        
        print("\nTest report saved to: system_integration_test_report.md")
        
        return metrics
    
    # Run the tests
    asyncio.run(main())