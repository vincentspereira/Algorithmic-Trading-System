#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Technical Indicators Library
Tests 80+ indicators and 25+ candlestick patterns

Phase 1 - Core System Validation & Hardening
"""

import asyncio
import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from nautilus_trader_engine.indicators.comprehensive_indicators import ComprehensiveIndicators
    from nautilus_trader_engine.indicators.enhanced_indicators_part1 import EnhancedTechnicalIndicators
    from nautilus_trader_engine.indicators.enhanced_indicators_part2 import EnhancedVolatilityVolumeIndicators
    from nautilus_trader_engine.indicators.enhanced_candlestick_patterns import EnhancedCandlestickPatterns
    from nautilus_trader_engine.indicators.technical_indicators import TechnicalIndicators
    INDICATORS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    INDICATORS_AVAILABLE = False

class ComprehensiveIndicatorTester:
    """Comprehensive testing framework for all indicators"""
    
    def __init__(self):
        self.indicators = ComprehensiveIndicators() if INDICATORS_AVAILABLE else None
        self.test_results = {
            'test_start': datetime.now().isoformat(),
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'test_details': {},
            'performance_metrics': {},
            'indicator_summary': {}
        }
    
    def generate_test_data(self, periods: int = 200) -> Dict[str, pd.Series]:
        """Generate synthetic market data for testing"""
        print("📊 Generating synthetic test data...")
        
        # Create realistic market data
        np.random.seed(42)  # For reproducible results
        
        # Price simulation with trend and noise
        base_price = 100.0
        trend = 0.02  # 2% upward trend
        volatility = 0.15  # 15% volatility
        
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
        
        # Generate correlated OHLCV data
        returns = np.random.normal(trend/periods, volatility/np.sqrt(periods), periods)
        prices = [base_price]
        
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        close_prices = pd.Series(prices[1:], index=dates)
        
        # Generate OHLC from close prices
        high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.02, periods)))
        low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.02, periods)))
        
        # Ensure price relationships are correct
        open_prices = close_prices.shift(1).fillna(base_price)
        
        # Ensure OHLC relationships
        high_prices = pd.concat([high_prices, close_prices, open_prices], axis=1).max(axis=1)
        low_prices = pd.concat([low_prices, close_prices, open_prices], axis=1).min(axis=1)
        
        # Generate volume with realistic patterns
        base_volume = 1000000
        volume = np.random.lognormal(np.log(base_volume), 0.5, periods)
        volume_series = pd.Series(volume, index=dates)
        
        return {
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume_series
        }
    
    def get_real_market_data(self, symbol: str = "AAPL", period: str = "1y") -> Dict[str, pd.Series]:
        """Get real market data for testing"""
        print(f"📈 Fetching real market data for {symbol}...")
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                print(f"⚠️ No data for {symbol}, using synthetic data")
                return self.generate_test_data()
            
            return {
                'open': data['Open'],
                'high': data['High'],
                'low': data['Low'],
                'close': data['Close'],
                'volume': data['Volume']
            }
        except Exception as e:
            print(f"⚠️ Error fetching real data: {e}, using synthetic data")
            return self.generate_test_data()
    
    def test_individual_indicator(self, indicator_name: str, indicator_func, test_data: Dict) -> Dict:
        """Test individual indicator"""
        test_result = {
            'indicator': indicator_name,
            'status': 'PENDING',
            'execution_time': 0,
            'error_message': None,
            'signal_analysis': {},
            'data_quality': {}
        }
        
        try:
            start_time = datetime.now()
            
            # Test based on indicator requirements with proper signatures
            if 'rsi' in indicator_name.lower() and 'vw_' not in indicator_name.lower():
                result = indicator_func(test_data['close'], 14)
            elif 'vw_rsi' in indicator_name.lower():
                result = indicator_func(test_data['close'], test_data['volume'], 14)
            elif 'macd' in indicator_name.lower() and 'vw_' not in indicator_name.lower():
                result = indicator_func(test_data['close'], 12, 26, 9)
            elif 'vw_macd' in indicator_name.lower():
                result = indicator_func(test_data['close'], test_data['volume'], 12, 26, 9)
            elif 'bollinger' in indicator_name.lower():
                result = indicator_func(test_data['close'], 20, 2.0)
            elif 'atr' in indicator_name.lower() and 'vw_' not in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 14)
            elif 'vw_atr' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'], 14)
            elif 'stochastic' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 14, 3, 3)
            elif 'williams' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 14)
            elif 'cci' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 20)
            elif 'awesome' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], 5, 34)
            elif 'fisher' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], 10)
            elif 'keltner' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 20, 2.0)
            elif 'donchian' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 20)
            elif 'adx' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], 14)
            elif 'vwap' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'])
            elif 'obv' in indicator_name.lower():
                result = indicator_func(test_data['close'], test_data['volume'])
            elif 'ad_line' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'])
            elif 'mfi' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'], 14)
            elif 'cmf' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'], 20)
            elif 'volume_roc' in indicator_name.lower():
                result = indicator_func(test_data['volume'], 12)
            elif 'pvt' in indicator_name.lower():
                result = indicator_func(test_data['close'], test_data['volume'])
            elif 'emv' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], test_data['volume'], 14)
            elif 'historical_volatility' in indicator_name.lower():
                result = indicator_func(test_data['close'], 30, 252)
            elif 'mass_index' in indicator_name.lower():
                result = indicator_func(test_data['high'], test_data['low'], 9, 25)
            elif 'vw_' in indicator_name.lower():
                # Generic volume-weighted indicators
                result = indicator_func(test_data['close'], test_data['volume'], 20)
            else:
                # Default single parameter test
                result = indicator_func(test_data['close'], 20)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Validate result
            if hasattr(result, 'value') and hasattr(result, 'signal'):
                # Check for valid values
                if isinstance(result.value, pd.Series):
                    valid_values = (~result.value.isna()).sum()
                    total_values = len(result.value)
                    validity_ratio = valid_values / total_values
                    
                    test_result.update({
                        'status': 'SUCCESS',
                        'execution_time': execution_time,
                        'signal_analysis': {
                            'signal': result.signal,
                            'strength': getattr(result, 'strength', 0),
                            'confidence': getattr(result, 'confidence', 0),
                            'metadata': getattr(result, 'metadata', {})
                        },
                        'data_quality': {
                            'valid_values': valid_values,
                            'total_values': total_values,
                            'validity_ratio': validity_ratio,
                            'has_nan': result.value.isna().any(),
                            'has_inf': np.isinf(result.value.replace([np.inf, -np.inf], np.nan)).any()
                        }
                    })
                else:
                    test_result.update({
                        'status': 'SUCCESS',
                        'execution_time': execution_time,
                        'signal_analysis': {
                            'signal': result.signal,
                            'strength': getattr(result, 'strength', 0),
                            'confidence': getattr(result, 'confidence', 0)
                        },
                        'data_quality': {'non_series_result': True}
                    })
            else:
                test_result.update({
                    'status': 'FAILED',
                    'execution_time': execution_time,
                    'error_message': 'Invalid result format'
                })
                
        except Exception as e:
            test_result.update({
                'status': 'ERROR',
                'execution_time': (datetime.now() - start_time).total_seconds() * 1000,
                'error_message': str(e)
            })
        
        return test_result
    
    def test_trend_indicators(self, test_data: Dict) -> List[Dict]:
        """Test all trend indicators"""
        print("🔄 Testing Trend Indicators...")
        results = []
        
        if not INDICATORS_AVAILABLE:
            return [{'indicator': 'trend_indicators', 'status': 'SKIPPED', 'error_message': 'Indicators not available'}]
        
        trend_tests = [
            ('SMA_20', self.indicators.traditional_indicators.sma),
            ('EMA_20', self.indicators.traditional_indicators.ema),
            ('VWMA_20', self.indicators.traditional_indicators.vwma),
            ('VW_EMA_20', self.indicators.traditional_indicators.vw_ema),
            ('Hull_MA_21', self.indicators.enhanced_indicators.hull_moving_average),
            ('KAMA_20', self.indicators.enhanced_indicators.adaptive_moving_average),
            ('DEMA_21', self.indicators.enhanced_indicators.double_exponential_ma),
            ('TEMA_21', self.indicators.enhanced_indicators.triple_exponential_ma),
            ('McGinley_Dynamic', self.indicators.enhanced_indicators.mcginley_dynamic),
            ('Zero_Lag_EMA', self.indicators.enhanced_indicators.zero_lag_ema),
            ('Linear_Regression', self.indicators.enhanced_indicators.linear_regression)
        ]
        
        for name, func in trend_tests:
            try:
                if 'vw_' in name.lower() or 'vwma' in name.lower():
                    result = self.test_vw_indicator(name, func, test_data)
                else:
                    result = self.test_individual_indicator(name, func, test_data)
                results.append(result)
                self.test_results['total_tests'] += 1
                if result['status'] == 'SUCCESS':
                    self.test_results['successful_tests'] += 1
                else:
                    self.test_results['failed_tests'] += 1
            except Exception as e:
                results.append({'indicator': name, 'status': 'ERROR', 'error_message': str(e)})
                self.test_results['total_tests'] += 1
                self.test_results['failed_tests'] += 1
        
        return results
    
    def test_vw_indicator(self, indicator_name: str, indicator_func, test_data: Dict) -> Dict:
        """Test volume-weighted indicators"""
        test_result = {
            'indicator': indicator_name,
            'status': 'PENDING',
            'execution_time': 0,
            'error_message': None
        }
        
        try:
            start_time = datetime.now()
            
            # Handle different volume-weighted indicator signatures
            if 'vw_atr' in indicator_name.lower() or 'vw_atrp' in indicator_name.lower():
                # ATR indicators need high, low, close, volume
                result = indicator_func(test_data['high'], test_data['low'], test_data['close'], test_data['volume'], 14)
            elif 'vw_rsi' in indicator_name.lower():
                # RSI indicators need close, volume
                result = indicator_func(test_data['close'], test_data['volume'], 14)
            elif 'vw_macd' in indicator_name.lower():
                # MACD indicators need close, volume
                result = indicator_func(test_data['close'], test_data['volume'], 12, 26, 9)
            else:
                # Default volume-weighted indicators (close, volume, period)
                result = indicator_func(test_data['close'], test_data['volume'], 20)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if hasattr(result, 'value') and hasattr(result, 'signal'):
                test_result.update({
                    'status': 'SUCCESS',
                    'execution_time': execution_time,
                    'signal': result.signal,
                    'strength': getattr(result, 'strength', 0),
                    'volume_weighted': True
                })
            else:
                test_result.update({
                    'status': 'FAILED',
                    'execution_time': execution_time,
                    'error_message': 'Invalid result format'
                })
                
        except Exception as e:
            test_result.update({
                'status': 'ERROR',
                'execution_time': (datetime.now() - start_time).total_seconds() * 1000,
                'error_message': str(e)
            })
        
        return test_result
    
    def test_momentum_indicators(self, test_data: Dict) -> List[Dict]:
        """Test all momentum indicators"""
        print("⚡ Testing Momentum Indicators...")
        results = []
        
        if not INDICATORS_AVAILABLE:
            return [{'indicator': 'momentum_indicators', 'status': 'SKIPPED', 'error_message': 'Indicators not available'}]
        
        momentum_tests = [
            ('RSI_14', self.indicators.traditional_indicators.rsi),
            ('VW_RSI_14', self.indicators.traditional_indicators.vw_rsi),
            ('MACD', self.indicators.traditional_indicators.macd),
            ('VW_MACD', self.indicators.traditional_indicators.vw_macd),
            ('Stochastic', self.indicators.enhanced_indicators.stochastic_oscillator),
            ('Williams_R', self.indicators.enhanced_indicators.williams_percent_r),
            ('CCI', self.indicators.enhanced_indicators.commodity_channel_index),
            ('Awesome_Oscillator', self.indicators.enhanced_indicators.awesome_oscillator),
            ('Fisher_Transform', self.indicators.enhanced_indicators.fisher_transform)
        ]
        
        for name, func in momentum_tests:
            try:
                if 'vw_' in name.lower():
                    result = self.test_vw_indicator(name, func, test_data)
                else:
                    result = self.test_individual_indicator(name, func, test_data)
                results.append(result)
                self.test_results['total_tests'] += 1
                if result['status'] == 'SUCCESS':
                    self.test_results['successful_tests'] += 1
                else:
                    self.test_results['failed_tests'] += 1
            except Exception as e:
                results.append({'indicator': name, 'status': 'ERROR', 'error_message': str(e)})
                self.test_results['total_tests'] += 1
                self.test_results['failed_tests'] += 1
        
        return results
    
    def test_volatility_indicators(self, test_data: Dict) -> List[Dict]:
        """Test all volatility indicators"""
        print("📊 Testing Volatility Indicators...")
        results = []
        
        if not INDICATORS_AVAILABLE:
            return [{'indicator': 'volatility_indicators', 'status': 'SKIPPED', 'error_message': 'Indicators not available'}]
        
        volatility_tests = [
            ('Bollinger_Bands', self.indicators.traditional_indicators.bollinger_bands),
            ('ATR_14', self.indicators.traditional_indicators.atr),
            ('VW_ATR_14', self.indicators.traditional_indicators.vw_atr),
            ('VW_ATRP_14', self.indicators.traditional_indicators.vw_atrp),
            ('Keltner_Channels', self.indicators.volatility_volume_indicators.keltner_channels),
            ('Donchian_Channels', self.indicators.volatility_volume_indicators.donchian_channels),
            ('Historical_Volatility', self.indicators.volatility_volume_indicators.historical_volatility),
            ('ADX', self.indicators.volatility_volume_indicators.average_directional_index)
        ]
        
        for name, func in volatility_tests:
            try:
                if 'vw_' in name.lower():
                    result = self.test_vw_indicator(name, func, test_data)
                else:
                    result = self.test_individual_indicator(name, func, test_data)
                results.append(result)
                self.test_results['total_tests'] += 1
                if result['status'] == 'SUCCESS':
                    self.test_results['successful_tests'] += 1
                else:
                    self.test_results['failed_tests'] += 1
            except Exception as e:
                results.append({'indicator': name, 'status': 'ERROR', 'error_message': str(e)})
                self.test_results['total_tests'] += 1
                self.test_results['failed_tests'] += 1
        
        return results
    
    def test_volume_indicators(self, test_data: Dict) -> List[Dict]:
        """Test all volume indicators"""
        print("📈 Testing Volume Indicators...")
        results = []
        
        if not INDICATORS_AVAILABLE:
            return [{'indicator': 'volume_indicators', 'status': 'SKIPPED', 'error_message': 'Indicators not available'}]
        
        volume_tests = [
            ('VWAP', self.indicators.traditional_indicators.vwap),
            ('OBV', self.indicators.traditional_indicators.obv),
            ('Enhanced_VWAP', self.indicators.volatility_volume_indicators.volume_weighted_average_price),
            ('Enhanced_OBV', self.indicators.volatility_volume_indicators.on_balance_volume_enhanced),
            ('AD_Line', self.indicators.volatility_volume_indicators.accumulation_distribution_line),
            ('MFI_14', self.indicators.volatility_volume_indicators.money_flow_index),
            ('CMF_20', self.indicators.volatility_volume_indicators.chaikin_money_flow),
            ('Volume_ROC', self.indicators.volatility_volume_indicators.volume_rate_of_change),
            ('PVT', self.indicators.volatility_volume_indicators.price_volume_trend),
            ('EMV', self.indicators.volatility_volume_indicators.ease_of_movement)
        ]
        
        for name, func in volume_tests:
            try:
                result = self.test_individual_indicator(name, func, test_data)
                results.append(result)
                self.test_results['total_tests'] += 1
                if result['status'] == 'SUCCESS':
                    self.test_results['successful_tests'] += 1
                else:
                    self.test_results['failed_tests'] += 1
            except Exception as e:
                results.append({'indicator': name, 'status': 'ERROR', 'error_message': str(e)})
                self.test_results['total_tests'] += 1
                self.test_results['failed_tests'] += 1
        
        return results
    
    def test_candlestick_patterns(self, test_data: Dict) -> Dict:
        """Test candlestick pattern recognition"""
        print("🕯️ Testing Candlestick Patterns...")
        
        if not INDICATORS_AVAILABLE:
            return {'status': 'SKIPPED', 'error_message': 'Indicators not available'}
        
        try:
            start_time = datetime.now()
            
            # Create DataFrame for pattern analysis
            pattern_df = pd.DataFrame(test_data)
            
            # Test pattern detection
            pattern_detector = EnhancedCandlestickPatterns()
            patterns_dict = pattern_detector.detect_all_patterns(pattern_df)
            pattern_summary = pattern_detector.get_pattern_summary(patterns_dict)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.test_results['total_tests'] += 1
            if patterns_dict is not None:
                self.test_results['successful_tests'] += 1
                
                return {
                    'status': 'SUCCESS',
                    'execution_time': execution_time,
                    'patterns_detected': pattern_summary.get('total_patterns', 0),
                    'unique_patterns': pattern_summary.get('unique_patterns', 0),
                    'strongest_signals': pattern_summary.get('strongest_signals', [])[:5],
                    'pattern_counts': pattern_summary.get('pattern_counts', {})
                }
            else:
                self.test_results['failed_tests'] += 1
                return {
                    'status': 'FAILED',
                    'execution_time': execution_time,
                    'error_message': 'No patterns detected'
                }
                
        except Exception as e:
            self.test_results['total_tests'] += 1
            self.test_results['failed_tests'] += 1
            return {
                'status': 'ERROR',
                'execution_time': (datetime.now() - start_time).total_seconds() * 1000,
                'error_message': str(e)
            }
    
    def test_comprehensive_analysis(self, test_data: Dict) -> Dict:
        """Test the comprehensive indicators analysis"""
        print("🔍 Testing Comprehensive Analysis...")
        
        if not INDICATORS_AVAILABLE:
            return {'status': 'SKIPPED', 'error_message': 'Indicators not available'}
        
        try:
            start_time = datetime.now()
            
            # Test comprehensive calculation
            results = self.indicators.calculate_all_indicators(
                test_data,
                include_patterns=True,
                include_volume_weighted=True
            )
            
            # Get summary
            summary = self.indicators.get_indicator_summary(results)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.test_results['total_tests'] += 1
            if results and summary:
                self.test_results['successful_tests'] += 1
                
                return {
                    'status': 'SUCCESS',
                    'execution_time': execution_time,
                    'total_indicators_calculated': summary.get('total_indicators', 0),
                    'indicators_by_category': summary.get('by_category', {}),
                    'volume_weighted_count': summary.get('volume_weighted_count', 0),
                    'strong_signals_count': len(summary.get('strong_signals', [])),
                    'sentiment_analysis': summary.get('sentiment_percentages', {}),
                    'top_signals': summary.get('strong_signals', [])[:5]
                }
            else:
                self.test_results['failed_tests'] += 1
                return {
                    'status': 'FAILED',
                    'execution_time': execution_time,
                    'error_message': 'No results from comprehensive analysis'
                }
                
        except Exception as e:
            self.test_results['total_tests'] += 1
            self.test_results['failed_tests'] += 1
            return {
                'status': 'ERROR',
                'execution_time': (datetime.now() - start_time).total_seconds() * 1000,
                'error_message': str(e)
            }

async def run_comprehensive_test():
    """Run comprehensive test suite"""
    print('🚀 Starting Comprehensive Technical Indicators Test Suite')
    print('=' * 80)
    print(f'Test Start Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    if not INDICATORS_AVAILABLE:
        print('❌ CRITICAL ERROR: Indicators library not available')
        print('Please ensure all indicator modules are properly installed')
        return
    
    # Initialize tester
    tester = ComprehensiveIndicatorTester()
    
    # Test with both synthetic and real data
    test_datasets = {
        'synthetic': tester.generate_test_data(200),
        'real_market': tester.get_real_market_data('AAPL', '1y')
    }
    
    for dataset_name, test_data in test_datasets.items():
        print(f'\n📊 Testing with {dataset_name} data ({len(test_data["close"])} periods)')
        print('-' * 60)
        
        # Test all indicator categories
        trend_results = tester.test_trend_indicators(test_data)
        momentum_results = tester.test_momentum_indicators(test_data)
        volatility_results = tester.test_volatility_indicators(test_data)
        volume_results = tester.test_volume_indicators(test_data)
        pattern_results = tester.test_candlestick_patterns(test_data)
        comprehensive_results = tester.test_comprehensive_analysis(test_data)
        
        # Store results
        tester.test_results['test_details'][dataset_name] = {
            'trend_indicators': trend_results,
            'momentum_indicators': momentum_results,
            'volatility_indicators': volatility_results,
            'volume_indicators': volume_results,
            'candlestick_patterns': pattern_results,
            'comprehensive_analysis': comprehensive_results
        }
        
        # Print summary for this dataset
        successful_trend = sum(1 for r in trend_results if r.get('status') == 'SUCCESS')
        successful_momentum = sum(1 for r in momentum_results if r.get('status') == 'SUCCESS')
        successful_volatility = sum(1 for r in volatility_results if r.get('status') == 'SUCCESS')
        successful_volume = sum(1 for r in volume_results if r.get('status') == 'SUCCESS')
        
        print(f'  ✅ Trend Indicators: {successful_trend}/{len(trend_results)} passed')
        print(f'  ✅ Momentum Indicators: {successful_momentum}/{len(momentum_results)} passed')
        print(f'  ✅ Volatility Indicators: {successful_volatility}/{len(volatility_results)} passed')
        print(f'  ✅ Volume Indicators: {successful_volume}/{len(volume_results)} passed')
        print(f'  ✅ Pattern Analysis: {pattern_results.get("status", "UNKNOWN")}')
        print(f'  ✅ Comprehensive Analysis: {comprehensive_results.get("status", "UNKNOWN")}')
        
        if pattern_results.get('status') == 'SUCCESS':
            print(f'    - Patterns detected: {pattern_results.get("patterns_detected", 0)}')
        
        if comprehensive_results.get('status') == 'SUCCESS':
            print(f'    - Total indicators: {comprehensive_results.get("total_indicators_calculated", 0)}')
            print(f'    - Strong signals: {comprehensive_results.get("strong_signals_count", 0)}')
    
    # Final summary
    print('\n🎯 COMPREHENSIVE TEST SUMMARY')
    print('=' * 60)
    
    total_tests = tester.test_results['total_tests']
    successful_tests = tester.test_results['successful_tests']
    failed_tests = tester.test_results['failed_tests']
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f'Total Tests Executed: {total_tests}')
    print(f'Successful Tests: {successful_tests}')
    print(f'Failed Tests: {failed_tests}')
    print(f'Success Rate: {success_rate:.1f}%')
    
    # Performance summary
    all_results = []
    for dataset_results in tester.test_results['test_details'].values():
        for category_results in dataset_results.values():
            if isinstance(category_results, list):
                all_results.extend(category_results)
            elif isinstance(category_results, dict):
                all_results.append(category_results)
    
    execution_times = [r.get('execution_time', 0) for r in all_results if r.get('execution_time')]
    if execution_times:
        avg_execution_time = sum(execution_times) / len(execution_times)
        print(f'Average Execution Time: {avg_execution_time:.2f}ms')
        print(f'Total Execution Time: {sum(execution_times):.2f}ms')
    
    # Status assessment
    if success_rate >= 90:
        status = "🟢 EXCELLENT"
    elif success_rate >= 75:
        status = "🟡 GOOD"
    elif success_rate >= 50:
        status = "🟠 NEEDS IMPROVEMENT"
    else:
        status = "🔴 CRITICAL ISSUES"
    
    print(f'\nOverall Status: {status}')
    print(f'Indicators Library: {"✅ OPERATIONAL" if success_rate >= 75 else "❌ NEEDS ATTENTION"}')
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'comprehensive_indicators_test_{timestamp}.json'
    
    # Finalize test results
    tester.test_results['test_end'] = datetime.now().isoformat()
    tester.test_results['success_rate'] = success_rate
    tester.test_results['status'] = status
    
    with open(results_file, 'w') as f:
        json.dump(tester.test_results, f, indent=2, default=str)
    
    print(f'\n💾 Detailed test results saved to: {results_file}')
    
    return tester.test_results

if __name__ == '__main__':
    asyncio.run(run_comprehensive_test())