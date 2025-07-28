"""
Pydantic models for Options Analytics API
Phase 5 Enterprise Feature - Options pricing and risk analytics
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class OptionType(str, Enum):
    """Option type enumeration"""
    CALL = "call"
    PUT = "put"


class OptionPricingRequest(BaseModel):
    """Request model for option pricing calculation"""
    symbol: str = Field(..., description="Option symbol (e.g., AAPL240315C00150000)")
    spot_price: float = Field(..., gt=0, description="Current price of underlying asset")
    strike_price: float = Field(..., gt=0, description="Strike price of the option")
    time_to_expiry: float = Field(..., gt=0, le=10, description="Time to expiry in years")
    risk_free_rate: float = Field(..., ge=0, le=1, description="Risk-free interest rate (as decimal)")
    volatility: float = Field(..., gt=0, le=5, description="Implied volatility (as decimal)")
    option_type: OptionType = Field(..., description="Option type: call or put")
    dividend_yield: float = Field(0.0, ge=0, le=1, description="Dividend yield (as decimal)")
    
    @validator('time_to_expiry')
    def validate_time_to_expiry(cls, v):
        if v <= 0:
            raise ValueError('Time to expiry must be positive')
        return v
    
    @validator('volatility')
    def validate_volatility(cls, v):
        if v <= 0 or v > 5:
            raise ValueError('Volatility must be between 0 and 5 (500%)')
        return v

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL240315C00150000",
                "spot_price": 150.0,
                "strike_price": 155.0,
                "time_to_expiry": 0.25,
                "risk_free_rate": 0.05,
                "volatility": 0.25,
                "option_type": "call",
                "dividend_yield": 0.02
            }
        }


class OptionPricingResponse(BaseModel):
    """Response model for option pricing calculation"""
    symbol: str
    option_type: OptionType
    spot_price: float
    strike_price: float
    time_to_expiry: float
    risk_free_rate: float
    volatility: float
    dividend_yield: float
    theoretical_price: float = Field(..., description="Theoretical option price")
    delta: float = Field(..., description="Price sensitivity to underlying price change")
    gamma: float = Field(..., description="Delta sensitivity to underlying price change")
    theta: float = Field(..., description="Price sensitivity to time decay (per day)")
    vega: float = Field(..., description="Price sensitivity to volatility change (per 1%)")
    rho: float = Field(..., description="Price sensitivity to interest rate change (per 1%)")
    calculation_timestamp: datetime


class GreeksRequest(BaseModel):
    """Request model for Greeks calculation"""
    symbol: str = Field(..., description="Option symbol")
    spot_price: float = Field(..., gt=0, description="Current price of underlying asset")
    strike_price: float = Field(..., gt=0, description="Strike price of the option")
    time_to_expiry: float = Field(..., gt=0, le=10, description="Time to expiry in years")
    risk_free_rate: float = Field(..., ge=0, le=1, description="Risk-free interest rate")
    volatility: float = Field(..., gt=0, le=5, description="Implied volatility")
    option_type: OptionType = Field(..., description="Option type: call or put")
    dividend_yield: float = Field(0.0, ge=0, le=1, description="Dividend yield")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL240315C00150000",
                "spot_price": 150.0,
                "strike_price": 155.0,
                "time_to_expiry": 0.25,
                "risk_free_rate": 0.05,
                "volatility": 0.25,
                "option_type": "call",
                "dividend_yield": 0.02
            }
        }


class GreeksResponse(BaseModel):
    """Response model for Greeks calculation"""
    symbol: str
    option_type: OptionType
    delta: float = Field(..., description="Price sensitivity to underlying price change")
    gamma: float = Field(..., description="Delta sensitivity to underlying price change")
    theta: float = Field(..., description="Price sensitivity to time decay (per day)")
    vega: float = Field(..., description="Price sensitivity to volatility change (per 1%)")
    rho: float = Field(..., description="Price sensitivity to interest rate change (per 1%)")
    calculation_timestamp: datetime


class ImpliedVolatilityRequest(BaseModel):
    """Request model for implied volatility calculation"""
    symbol: str = Field(..., description="Option symbol")
    market_price: float = Field(..., gt=0, description="Current market price of the option")
    spot_price: float = Field(..., gt=0, description="Current price of underlying asset")
    strike_price: float = Field(..., gt=0, description="Strike price of the option")
    time_to_expiry: float = Field(..., gt=0, le=10, description="Time to expiry in years")
    risk_free_rate: float = Field(..., ge=0, le=1, description="Risk-free interest rate")
    option_type: OptionType = Field(..., description="Option type: call or put")
    dividend_yield: float = Field(0.0, ge=0, le=1, description="Dividend yield")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL240315C00150000",
                "market_price": 5.50,
                "spot_price": 150.0,
                "strike_price": 155.0,
                "time_to_expiry": 0.25,
                "risk_free_rate": 0.05,
                "option_type": "call",
                "dividend_yield": 0.02
            }
        }


class ImpliedVolatilityResponse(BaseModel):
    """Response model for implied volatility calculation"""
    symbol: str
    option_type: OptionType
    market_price: float
    implied_volatility: float = Field(..., description="Calculated implied volatility")
    calculation_timestamp: datetime


class VolatilitySurfacePoint(BaseModel):
    """Single point on volatility surface"""
    strike: float
    expiry: float
    implied_volatility: float


class VolatilitySurfaceRequest(BaseModel):
    """Request model for volatility surface calculation"""
    symbol: str = Field(..., description="Underlying symbol")
    spot_price: float = Field(..., gt=0, description="Current price of underlying asset")
    strikes: List[float] = Field(..., description="List of strike prices")
    expiries: List[float] = Field(..., description="List of expiry times in years")
    risk_free_rate: float = Field(..., ge=0, le=1, description="Risk-free interest rate")
    dividend_yield: float = Field(0.0, ge=0, le=1, description="Dividend yield")
    market_prices: Dict[str, float] = Field(..., description="Market prices keyed by 'strike_expiry'")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "spot_price": 150.0,
                "strikes": [140.0, 145.0, 150.0, 155.0, 160.0],
                "expiries": [0.25, 0.5, 1.0],
                "risk_free_rate": 0.05,
                "dividend_yield": 0.02,
                "market_prices": {
                    "140.0_0.25": 12.50,
                    "145.0_0.25": 8.75,
                    "150.0_0.25": 5.50
                }
            }
        }


class VolatilitySurfaceResponse(BaseModel):
    """Response model for volatility surface calculation"""
    symbol: str
    spot_price: float
    surface_points: List[VolatilitySurfacePoint]
    calculation_timestamp: datetime


class OptionPosition(BaseModel):
    """Single option position in portfolio"""
    symbol: str
    option_type: OptionType
    strike_price: float
    time_to_expiry: float
    quantity: int = Field(..., description="Number of contracts (positive for long, negative for short)")
    market_price: float


class OptionsPortfolioRiskRequest(BaseModel):
    """Request model for options portfolio risk calculation"""
    portfolio_name: str = Field(..., description="Portfolio identifier")
    underlying_price: float = Field(..., gt=0, description="Current underlying price")
    positions: List[OptionPosition] = Field(..., description="List of option positions")
    risk_free_rate: float = Field(..., ge=0, le=1, description="Risk-free interest rate")
    dividend_yield: float = Field(0.0, ge=0, le=1, description="Dividend yield")
    volatility: float = Field(..., gt=0, le=5, description="Current implied volatility")

    class Config:
        schema_extra = {
            "example": {
                "portfolio_name": "AAPL_Options_Portfolio",
                "underlying_price": 150.0,
                "positions": [
                    {
                        "symbol": "AAPL240315C00155000",
                        "option_type": "call",
                        "strike_price": 155.0,
                        "time_to_expiry": 0.25,
                        "quantity": 10,
                        "market_price": 5.50
                    }
                ],
                "risk_free_rate": 0.05,
                "dividend_yield": 0.02,
                "volatility": 0.25
            }
        }


class PortfolioGreeks(BaseModel):
    """Portfolio-level Greeks"""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float


class OptionsPortfolioRiskResponse(BaseModel):
    """Response model for options portfolio risk calculation"""
    portfolio_name: str
    underlying_price: float
    total_market_value: float
    total_theoretical_value: float
    portfolio_greeks: PortfolioGreeks
    position_count: int
    calculation_timestamp: datetime


class OptionChain(BaseModel):
    """Option chain data for a specific expiry"""
    expiry_date: str
    calls: List[Dict[str, Any]]
    puts: List[Dict[str, Any]]


class OptionChainRequest(BaseModel):
    """Request model for option chain data"""
    symbol: str = Field(..., description="Underlying symbol")
    expiry_dates: Optional[List[str]] = Field(None, description="Specific expiry dates (YYYY-MM-DD)")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "expiry_dates": ["2024-03-15", "2024-06-21"]
            }
        }


class OptionChainResponse(BaseModel):
    """Response model for option chain data"""
    symbol: str
    spot_price: float
    option_chains: List[OptionChain]
    timestamp: datetime