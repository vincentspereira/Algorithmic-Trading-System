"""
Compatibility shim for ComprehensiveIndicators API.
Provides the classes expected by api.main and tests by re-exporting
mock implementations defined in the indicators package __init__.
Replace with real implementation when ready.
"""
from . import (
    ComprehensiveIndicators,
    ComprehensiveIndicatorResult,
    IndicatorCategory,
)

__all__ = [
    "ComprehensiveIndicators",
    "ComprehensiveIndicatorResult",
    "IndicatorCategory",
]