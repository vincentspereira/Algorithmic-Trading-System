"""Risk Manager Service

Comprehensive risk management system with real-time monitoring,
VaR calculations, position sizing, and advanced risk controls.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from .core.risk_engine import RiskEngine
from .core.var_calculator import VaRCalculator
from .core.position_sizer import PositionSizer
from .core.risk_monitor import RealTimeRiskMonitor
from .models.risk_models import (
    RiskLimits,
    RiskMetric,
    RiskViolation,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    PortfolioRiskSummary
)
from .api.risk_api import RiskManagerAPI

__version__ = "1.0.0"
__author__ = "Vincent S. Pereira"

__all__ = [
    "RiskEngine",
    "VaRCalculator",
    "PositionSizer",
    "RealTimeRiskMonitor",
    "RiskLimits",
    "RiskMetric",
    "RiskViolation",
    "RiskAssessmentRequest",
    "RiskAssessmentResponse",
    "PortfolioRiskSummary",
    "RiskManagerAPI"
]