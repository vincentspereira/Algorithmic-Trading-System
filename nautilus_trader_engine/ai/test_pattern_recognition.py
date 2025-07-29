"""
Test Market Pattern Recognition System
Test the pattern detection capabilities
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List

from pattern_recognition import (
    PatternRecognitionEngine, MarketData, PatternType, 
    PatternSignal, CandlestickPatternDetector, ChartPatternDetector,
    VolumePatternDetector, AnomalyDetector
)


def generate_sample_data(periods: int = 100, base_price: float = 100.0) -> List[MarketData]:
    """Generate sample market data for testing"""
    data = []
    current_price = base_price
    current_time = datetime.now() - timedelta(minutes=periods)
    
    for i in range(periods):
        # Generate realistic OHLCV data
        price_change = np.random.normal(0, 0.02) * current_price
        
        open_price = current_price
        close_price = current_price + price_change
        
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 0.01)) * current_price
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 0.01)) * current_price
        
        volume = max(1000, np.random.normal(10000, 3000))
        
        data.append(MarketData(
            timestamp=current_time + timedelta(minutes=i),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            symbol="TEST"
        ))
        
        current_price = close_price
    
    return data


def create_doji_pattern(base_data: List[MarketData]) -> List[MarketData]:
    """Create data with a Doji pattern"""
    data = base_data.copy()
    
    # Create a Doji candle (open ≈ close)
    last_candle = data[-1]
    doji_candle = MarketData(
        timestamp=last_candle.timestamp + timedelta(minutes=1),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.1,  # Very close to open
        volume=15000,
        symbol="TEST"
    )
    
    data.append(doji_candle)
    return data


def create_hammer_pattern(base_data: List[MarketData]) -> List[MarketData]:
    """Create data with a Hammer pattern"""
    data = base_data.copy()
    
    # Create a Hammer candle (small body, long lower shadow)
    last_candle = data[-1]
    hammer_candle = MarketData(
        timestamp=last_candle.timestamp + timedelta(minutes=1),
        open=100.0,
        high=100.5,
        low=97.0,  # Long lower shadow
        close=99.8,  # Small body
        volume=20000,
        symbol="TEST"
    )
    
    data.append(hammer_candle)
    return data


def create_volume_spike(base_data: List[MarketData]) -> List[MarketData]:
    """Create data with a volume spike"""
    data = base_data.copy()
    
    # Create a volume spike
    last_candle = data[-1]
    spike_candle = MarketData(
        timestamp=last_candle.timestamp + timedelta(minutes=1),
        open=100.0,
        high=102.0,
        low=99.5,
        close=101.5,
        volume=50000,  # Much higher than normal
        symbol="TEST"
    )
    
    data.append(spike_candle)
    return data


async def test_candlestick_patterns():
    """Test candlestick pattern detection"""
    print("Testing Candlestick Pattern Detection...")
    
    detector = CandlestickPatternDetector()
    
    # Test Doji pattern
    base_data = generate_sample_data(50, 100.0)
    doji_data = create_doji_pattern(base_data)
    
    doji_patterns = detector.detect(doji_data)
    print(f"  - Doji patterns detected: {len(doji_patterns)}")
    
    for pattern in doji_patterns:
        if pattern.pattern_type == PatternType.DOJI:
            print(f"    ✓ Doji detected with confidence: {pattern.confidence:.2f}")
            print(f"      Signal: {pattern.signal.value}")
            print(f"      Body ratio: {pattern.pattern_data.get('body_ratio', 0):.3f}")
    
    # Test Hammer pattern
    hammer_data = create_hammer_pattern(base_data)
    hammer_patterns = detector.detect(hammer_data)
    print(f"  - Hammer patterns detected: {len(hammer_patterns)}")
    
    for pattern in hammer_patterns:
        if pattern.pattern_type == PatternType.HAMMER:
            print(f"    ✓ Hammer detected with confidence: {pattern.confidence:.2f}")
            print(f"      Signal: {pattern.signal.value}")
            print(f"      Shadow ratio: {pattern.pattern_data.get('shadow_ratio', 0):.2f}")


async def test_volume_patterns():
    """Test volume pattern detection"""
    print("\nTesting Volume Pattern Detection...")
    
    detector = VolumePatternDetector()
    
    # Test volume spike
    base_data = generate_sample_data(30, 100.0)
    spike_data = create_volume_spike(base_data)
    
    volume_patterns = detector.detect(spike_data)
    print(f"  - Volume patterns detected: {len(volume_patterns)}")
    
    for pattern in volume_patterns:
        if pattern.pattern_type == PatternType.VOLUME_SPIKE:
            print(f"    ✓ Volume spike detected with confidence: {pattern.confidence:.2f}")
            print(f"      Signal: {pattern.signal.value}")
            print(f"      Spike ratio: {pattern.pattern_data.get('spike_ratio', 0):.2f}")
            print(f"      Volume confirmation: {pattern.volume_confirmation}")


async def test_chart_patterns():
    """Test chart pattern detection"""
    print("\nTesting Chart Pattern Detection...")
    
    detector = ChartPatternDetector()
    
    # Generate data with some trend
    data = []
    base_price = 100.0
    current_time = datetime.now() - timedelta(minutes=50)
    
    # Create a potential double top pattern
    for i in range(50):
        if i < 15:
            # Rising to first peak
            price = base_price + (i * 0.5)
        elif i < 25:
            # Falling from first peak
            price = base_price + 7.5 - ((i - 15) * 0.3)
        elif i < 40:
            # Rising to second peak
            price = base_price + 4.5 + ((i - 25) * 0.2)
        else:
            # Falling from second peak
            price = base_price + 7.5 - ((i - 40) * 0.4)
        
        # Add some noise
        price += np.random.normal(0, 0.1)
        
        data.append(MarketData(
            timestamp=current_time + timedelta(minutes=i),
            open=price - 0.1,
            high=price + 0.2,
            low=price - 0.2,
            close=price,
            volume=np.random.normal(10000, 1000),
            symbol="TEST"
        ))
    
    chart_patterns = detector.detect(data)
    print(f"  - Chart patterns detected: {len(chart_patterns)}")
    
    for pattern in chart_patterns:
        print(f"    ✓ {pattern.pattern_type.value} detected with confidence: {pattern.confidence:.2f}")
        print(f"      Signal: {pattern.signal.value}")
        print(f"      Key levels: {[f'{level:.2f}' for level in pattern.key_levels]}")


async def test_anomaly_detection():
    """Test anomaly detection"""
    print("\nTesting Anomaly Detection...")
    
    detector = AnomalyDetector()
    
    # Generate normal data with an anomaly
    base_data = generate_sample_data(60, 100.0)
    
    # Add a price anomaly (large jump)
    anomaly_candle = MarketData(
        timestamp=base_data[-1].timestamp + timedelta(minutes=1),
        open=100.0,
        high=110.0,  # Large jump
        low=99.0,
        close=108.0,
        volume=25000,
        symbol="TEST"
    )
    
    base_data.append(anomaly_candle)
    
    anomaly_patterns = detector.detect(base_data)
    print(f"  - Anomaly patterns detected: {len(anomaly_patterns)}")
    
    for pattern in anomaly_patterns:
        print(f"    ✓ {pattern.pattern_type.value} detected with confidence: {pattern.confidence:.2f}")
        print(f"      Signal: {pattern.signal.value}")
        if 'z_score' in pattern.pattern_data:
            print(f"      Z-score: {pattern.pattern_data['z_score']:.2f}")


async def test_pattern_recognition_engine():
    """Test the main pattern recognition engine"""
    print("\nTesting Pattern Recognition Engine...")
    
    # Create engine with all detectors enabled
    engine = PatternRecognitionEngine(
        enable_candlestick=True,
        enable_chart_patterns=True,
        enable_volume_patterns=True,
        enable_anomaly_detection=True,
        min_confidence=0.3
    )
    
    # Generate comprehensive test data
    test_data = generate_sample_data(100, 100.0)
    
    # Add various patterns
    test_data = create_doji_pattern(test_data)
    test_data = create_hammer_pattern(test_data)
    test_data = create_volume_spike(test_data)
    
    # Detect all patterns
    all_patterns = await engine.detect_patterns(test_data, "TESTSTOCK")
    
    print(f"  - Total patterns detected: {len(all_patterns)}")
    print(f"  - Pattern types found:")
    
    pattern_types = {}
    for pattern in all_patterns:
        pattern_type = pattern.pattern_type.value
        pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
    
    for pattern_type, count in pattern_types.items():
        print(f"    • {pattern_type}: {count}")
    
    # Test pattern analysis
    analysis = await engine.analyze_symbol("TESTSTOCK", test_data)
    print(f"\n  - Symbol Analysis:")
    print(f"    • Overall signal: {analysis['overall_assessment']['signal']}")
    print(f"    • Confidence: {analysis['overall_assessment']['confidence']:.2f}")
    print(f"    • Bullish score: {analysis['overall_assessment']['bullish_score']:.2f}")
    print(f"    • Bearish score: {analysis['overall_assessment']['bearish_score']:.2f}")
    
    # Test statistics
    stats = engine.get_pattern_statistics()
    print(f"\n  - Engine Statistics:")
    print(f"    • Total detections: {stats['metrics']['total_detections']}")
    print(f"    • Patterns found: {stats['metrics']['patterns_found']}")
    print(f"    • Average confidence: {stats['metrics']['avg_confidence']:.2f}")
    print(f"    • Detection time: {stats['metrics']['detection_time_ms']:.2f}ms")
    
    # Test signal summary
    signal_summary = engine.get_signal_summary(hours_back=24)
    print(f"\n  - Signal Summary (24h):")
    print(f"    • Total patterns: {signal_summary['total_patterns']}")
    print(f"    • Average confidence: {signal_summary['avg_confidence']:.2f}")
    if signal_summary['strongest_signal']:
        strongest = signal_summary['strongest_signal']
        print(f"    • Strongest signal: {strongest['signal']} ({strongest['confidence']:.2f})")


async def test_performance():
    """Test performance of pattern recognition"""
    print("\nTesting Performance...")
    
    engine = PatternRecognitionEngine()
    
    # Generate large dataset
    large_data = generate_sample_data(1000, 100.0)
    
    # Measure detection time
    start_time = asyncio.get_event_loop().time()
    patterns = await engine.detect_patterns(large_data, "PERFTEST")
    end_time = asyncio.get_event_loop().time()
    
    detection_time_ms = (end_time - start_time) * 1000
    
    print(f"  - Dataset size: {len(large_data)} candles")
    print(f"  - Patterns detected: {len(patterns)}")
    print(f"  - Detection time: {detection_time_ms:.2f}ms")
    print(f"  - Throughput: {len(large_data) / (detection_time_ms / 1000):.0f} candles/second")
    
    # Performance per detector type
    stats = engine.get_pattern_statistics()
    print(f"  - Average detection time: {stats['metrics']['detection_time_ms']:.2f}ms")


if __name__ == "__main__":
    print("Market Pattern Recognition Test Suite")
    print("=" * 50)
    
    async def run_all_tests():
        await test_candlestick_patterns()
        await test_volume_patterns()
        await test_chart_patterns()
        await test_anomaly_detection()
        await test_pattern_recognition_engine()
        await test_performance()
        
        print("\n✓ All pattern recognition tests completed!")
    
    # Run all tests
    asyncio.run(run_all_tests())