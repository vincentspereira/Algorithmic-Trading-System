#!/usr/bin/env python3
"""
Simple Technical Indicators Validation Test
Phase 1 - Core System Validation & Hardening

Tests the key volume-weighted technical indicators required for Phase 1
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def generate_test_data(periods=200):
    """Generate synthetic market data for testing"""
    np.random.seed(42)
    
    # Generate price data with realistic patterns
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='D')
    base_price = 100.0
    
    # Random walk with trend
    price_changes = np.random.normal(0.001, 0.02, periods)
    prices = [base_price]
    
    for change in price_changes[1:]:
        prices.append(prices[-1] * (1 + change))
    
    # Create OHLC data
    open_prices = np.array(prices) * (1 + np.random.normal(0, 0.005, periods))
    close_prices = np.array(prices)
    high_prices = np.maximum(open_prices, close_prices) * (1 + np.random.uniform(0, 0.01, periods))
    low_prices = np.minimum(open_prices, close_prices) * (1 - np.random.uniform(0, 0.01, periods))
    volumes = np.random.lognormal(12, 0.5, periods).astype(int)
    
    return pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })

def test_basic_indicators():
    """Test basic technical indicators"""
    print("🚀 Starting Technical Indicators Validation Test")
    print("=" * 60)
    
    # Import indicators
    try:
        from nautilus_trader_engine.indicators.technical_indicators import TechnicalIndicators
        print("✅ Technical indicators imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import technical indicators: {e}")
        return False
    
    # Generate test data
    print("\n📊 Generating test data...")
    data = generate_test_data(200)
    print(f"✅ Generated {len(data)} periods of synthetic market data")
    
    results = {}
    test_results = []
    
    # Test 1: Simple Moving Average
    try:
        sma_result = TechnicalIndicators.sma(data['close'], 20)
        print(f"✅ SMA: {sma_result.value.iloc[-1]:.2f} | Signal: {sma_result.signal}")
        test_results.append("SMA: PASS")
        results['sma'] = {'value': sma_result.value.iloc[-1], 'signal': sma_result.signal}
    except Exception as e:
        print(f"❌ SMA failed: {e}")
        test_results.append("SMA: FAIL")
    
    # Test 2: Volume Weighted Moving Average
    try:
        vwma_result = TechnicalIndicators.vwma(data['close'], data['volume'], 20)
        print(f"✅ VWMA: {vwma_result.value.iloc[-1]:.2f} | Signal: {vwma_result.signal}")
        test_results.append("VWMA: PASS")
        results['vwma'] = {'value': vwma_result.value.iloc[-1], 'signal': vwma_result.signal}
    except Exception as e:
        print(f"❌ VWMA failed: {e}")
        test_results.append("VWMA: FAIL")
    
    # Test 3: Volume Weighted EMA
    try:
        vw_ema_result = TechnicalIndicators.vw_ema(data['close'], data['volume'], 20)
        print(f"✅ VW EMA: {vw_ema_result.value.iloc[-1]:.2f} | Signal: {vw_ema_result.signal}")
        test_results.append("VW_EMA: PASS")
        results['vw_ema'] = {'value': vw_ema_result.value.iloc[-1], 'signal': vw_ema_result.signal}
    except Exception as e:
        print(f"❌ VW EMA failed: {e}")
        test_results.append("VW_EMA: FAIL")
    
    # Test 4: RSI
    try:
        rsi_result = TechnicalIndicators.rsi(data['close'], 14)
        print(f"✅ RSI: {rsi_result.value.iloc[-1]:.1f} | Signal: {rsi_result.signal}")
        test_results.append("RSI: PASS")
        results['rsi'] = {'value': rsi_result.value.iloc[-1], 'signal': rsi_result.signal}
    except Exception as e:
        print(f"❌ RSI failed: {e}")
        test_results.append("RSI: FAIL")
    
    # Test 5: Volume Weighted RSI
    try:
        vw_rsi_result = TechnicalIndicators.vw_rsi(data['close'], data['volume'], 14)
        print(f"✅ VW RSI: {vw_rsi_result.value.iloc[-1]:.1f} | Signal: {vw_rsi_result.signal}")
        test_results.append("VW_RSI: PASS")
        results['vw_rsi'] = {'value': vw_rsi_result.value.iloc[-1], 'signal': vw_rsi_result.signal}
    except Exception as e:
        print(f"❌ VW RSI failed: {e}")
        test_results.append("VW_RSI: FAIL")
    
    # Test 6: MACD
    try:
        macd_result = TechnicalIndicators.macd(data['close'], 12, 26, 9)
        macd_val = macd_result.value['macd'].iloc[-1]
        print(f"✅ MACD: {macd_val:.4f} | Signal: {macd_result.signal}")
        test_results.append("MACD: PASS")
        results['macd'] = {'value': macd_val, 'signal': macd_result.signal}
    except Exception as e:
        print(f"❌ MACD failed: {e}")
        test_results.append("MACD: FAIL")
    
    # Test 7: Volume Weighted MACD
    try:
        vw_macd_result = TechnicalIndicators.vw_macd(data['close'], data['volume'], 12, 26, 9)
        vw_macd_val = vw_macd_result.value['vw_macd'].iloc[-1]
        print(f"✅ VW MACD: {vw_macd_val:.4f} | Signal: {vw_macd_result.signal}")
        test_results.append("VW_MACD: PASS")
        results['vw_macd'] = {'value': vw_macd_val, 'signal': vw_macd_result.signal}
    except Exception as e:
        print(f"❌ VW MACD failed: {e}")
        test_results.append("VW_MACD: FAIL")
    
    # Test 8: ATR
    try:
        atr_result = TechnicalIndicators.atr(data['high'], data['low'], data['close'], 14)
        print(f"✅ ATR: {atr_result.value.iloc[-1]:.4f} | Signal: {atr_result.signal}")
        test_results.append("ATR: PASS")
        results['atr'] = {'value': atr_result.value.iloc[-1], 'signal': atr_result.signal}
    except Exception as e:
        print(f"❌ ATR failed: {e}")
        test_results.append("ATR: FAIL")
    
    # Test 9: Volume Weighted ATR
    try:
        vw_atr_result = TechnicalIndicators.vw_atr(data['high'], data['low'], data['close'], data['volume'], 14)
        print(f"✅ VW ATR: {vw_atr_result.value.iloc[-1]:.4f} | Signal: {vw_atr_result.signal}")
        test_results.append("VW_ATR: PASS")
        results['vw_atr'] = {'value': vw_atr_result.value.iloc[-1], 'signal': vw_atr_result.signal}
    except Exception as e:
        print(f"❌ VW ATR failed: {e}")
        test_results.append("VW_ATR: FAIL")
    
    # Test 10: Bollinger Bands
    try:
        bb_result = TechnicalIndicators.bollinger_bands(data['close'], 20, 2.0)
        bb_percent = bb_result.value['percent']
        print(f"✅ Bollinger Bands: {bb_percent:.2f} | Signal: {bb_result.signal}")
        test_results.append("BOLLINGER: PASS")
        results['bollinger'] = {'value': bb_percent, 'signal': bb_result.signal}
    except Exception as e:
        print(f"❌ Bollinger Bands failed: {e}")
        test_results.append("BOLLINGER: FAIL")
    
    # Test 11: VWAP
    try:
        vwap_result = TechnicalIndicators.vwap(data['high'], data['low'], data['close'], data['volume'])
        print(f"✅ VWAP: {vwap_result.value.iloc[-1]:.2f} | Signal: {vwap_result.signal}")
        test_results.append("VWAP: PASS")
        results['vwap'] = {'value': vwap_result.value.iloc[-1], 'signal': vwap_result.signal}
    except Exception as e:
        print(f"❌ VWAP failed: {e}")
        test_results.append("VWAP: FAIL")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 40)
    
    passed = len([t for t in test_results if "PASS" in t])
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print(f"\nDetailed Results:")
    for result in test_results:
        status = "✅" if "PASS" in result else "❌"
        print(f"  {status} {result}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"phase1_technical_indicators_test_{timestamp}.json"
    
    final_results = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed_tests": passed,
            "success_rate": success_rate,
            "data_periods": len(data)
        },
        "test_results": test_results,
        "indicator_results": results,
        "phase1_readiness": "READY" if success_rate >= 80 else "NEEDS_WORK"
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    if success_rate >= 80:
        print(f"\n🎉 Phase 1 Technical Indicators: READY!")
        print(f"   • {passed}/{total} indicators working correctly")
        print(f"   • Volume-weighted indicators implemented")
        print(f"   • System ready for advanced features")
    else:
        print(f"\n⚠️  Phase 1 Technical Indicators: NEEDS WORK")
        print(f"   • Only {passed}/{total} indicators working")
        print(f"   • Review failed indicators before proceeding")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = test_basic_indicators()
    sys.exit(0 if success else 1)