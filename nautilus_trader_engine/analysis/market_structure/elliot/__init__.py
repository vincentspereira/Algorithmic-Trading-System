"""
Elliot Wave Analysis Module

This module provides institutional-grade Elliot Wave analysis tools including:
- Wave Counting: Dynamic identification of impulse and corrective wave patterns
- Wave Degree Analysis: Multi-degree wave analysis (grand supercycle to subminuette)
- Wave Strength Assessment: Volume-weighted wave strength calculation
- Fibonacci Relationships: Built-in Fibonacci ratio validation for waves
- Pattern Recognition: Automatic detection of triangles, diagonals, and complex corrections
- Wave Completion Signals: Trading signals based on wave completion

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .elliot_wave_analyzer import (
    InstitutionalElliotWaveAnalyzer, ElliotWave, WaveSignal,
    WaveType, WaveDegree, WavePosition, WaveStrength,
    create_elliot_wave_analyzer, identify_wave_pattern,
    calculate_wave_fibonacci_target
)

__all__ = [
    "InstitutionalElliotWaveAnalyzer",
    "ElliotWave",
    "WaveSignal",
    "WaveType",
    "WaveDegree",
    "WavePosition",
    "WaveStrength",
    "create_elliot_wave_analyzer",
    "identify_wave_pattern",
    "calculate_wave_fibonacci_target"
]