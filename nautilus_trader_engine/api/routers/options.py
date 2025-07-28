"""
Options Analytics Router - Phase 5 Enterprise Feature
Advanced options pricing and risk analytics using QuantLib

This module provides comprehensive options analytics including:
- Black-Scholes pricing
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Implied volatility calculation
- Volatility surface analysis
- Risk metrics for options portfolios
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator
import numpy as np

# QuantLib imports
try:
    import QuantLib as ql
    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False
    logging.warning("QuantLib not available. Options analytics will use fallback calculations.")

from ..core.security import get_current_active_user
from ..models.options import (
    OptionPricingRequest,
    OptionPricingResponse,
    GreeksRequest,
    GreeksResponse,
    ImpliedVolatilityRequest,
    ImpliedVolatilityResponse,
    VolatilitySurfaceRequest,
    VolatilitySurfaceResponse,
    OptionsPortfolioRiskRequest,
    OptionsPortfolioRiskResponse
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


class OptionsAnalyticsService:
    """Service class for options analytics calculations using QuantLib"""
    
    def __init__(self):
        self.calendar = ql.UnitedStates() if QUANTLIB_AVAILABLE else None
        self.day_counter = ql.Actual365Fixed() if QUANTLIB_AVAILABLE else None
    
    def calculate_option_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str = "call",
        dividend_yield: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate option price using Black-Scholes model
        
        Args:
            spot_price: Current price of underlying asset
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free interest rate
            volatility: Implied volatility
            option_type: "call" or "put"
            dividend_yield: Dividend yield of underlying
            
        Returns:
            Dictionary containing option price and Greeks
        """
        if not QUANTLIB_AVAILABLE:
            return self._fallback_black_scholes(
                spot_price, strike_price, time_to_expiry, 
                risk_free_rate, volatility, option_type, dividend_yield
            )
        
        try:
            # Set up QuantLib calculation date
            calculation_date = ql.Date.todaysDate()
            ql.Settings.instance().evaluationDate = calculation_date
            
            # Create option
            exercise = ql.EuropeanExercise(
                calculation_date + int(time_to_expiry * 365)
            )
            
            payoff = ql.PlainVanillaPayoff(
                ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
                strike_price
            )
            
            option = ql.VanillaOption(payoff, exercise)
            
            # Market data
            spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot_price))
            flat_ts = ql.YieldTermStructureHandle(
                ql.FlatForward(calculation_date, risk_free_rate, self.day_counter)
            )
            dividend_ts = ql.YieldTermStructureHandle(
                ql.FlatForward(calculation_date, dividend_yield, self.day_counter)
            )
            flat_vol_ts = ql.BlackVolTermStructureHandle(
                ql.BlackConstantVol(calculation_date, self.calendar, volatility, self.day_counter)
            )
            
            # Black-Scholes process
            bs_process = ql.BlackScholesMertonProcess(
                spot_handle, dividend_ts, flat_ts, flat_vol_ts
            )
            
            # Pricing engine
            engine = ql.AnalyticEuropeanEngine(bs_process)
            option.setPricingEngine(engine)
            
            # Calculate price and Greeks
            price = option.NPV()
            delta = option.delta()
            gamma = option.gamma()
            theta = option.theta()
            vega = option.vega()
            rho = option.rho()
            
            return {
                "price": price,
                "delta": delta,
                "gamma": gamma,
                "theta": theta / 365,  # Convert to per-day
                "vega": vega / 100,   # Convert to per 1% vol change
                "rho": rho / 100      # Convert to per 1% rate change
            }
            
        except Exception as e:
            logger.error(f"QuantLib calculation error: {e}")
            return self._fallback_black_scholes(
                spot_price, strike_price, time_to_expiry,
                risk_free_rate, volatility, option_type, dividend_yield
            )
    
    def _fallback_black_scholes(
        self,
        S: float, K: float, T: float, r: float, sigma: float,
        option_type: str = "call", q: float = 0.0
    ) -> Dict[str, float]:
        """Fallback Black-Scholes implementation using numpy"""
        from scipy.stats import norm
        import math
        
        # Black-Scholes formula
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type.lower() == "call":
            price = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
            delta = math.exp(-q * T) * norm.cdf(d1)
        else:
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)
            delta = -math.exp(-q * T) * norm.cdf(-d1)
        
        # Greeks calculations
        gamma = math.exp(-q * T) * norm.pdf(d1) / (S * sigma * math.sqrt(T))
        theta_call = (-S * norm.pdf(d1) * sigma * math.exp(-q * T) / (2 * math.sqrt(T)) 
                     - r * K * math.exp(-r * T) * norm.cdf(d2) 
                     + q * S * math.exp(-q * T) * norm.cdf(d1))
        theta_put = (-S * norm.pdf(d1) * sigma * math.exp(-q * T) / (2 * math.sqrt(T)) 
                    + r * K * math.exp(-r * T) * norm.cdf(-d2) 
                    - q * S * math.exp(-q * T) * norm.cdf(-d1))
        theta = theta_call if option_type.lower() == "call" else theta_put
        
        vega = S * math.exp(-q * T) * norm.pdf(d1) * math.sqrt(T)
        
        if option_type.lower() == "call":
            rho = K * T * math.exp(-r * T) * norm.cdf(d2)
        else:
            rho = -K * T * math.exp(-r * T) * norm.cdf(-d2)
        
        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "theta": theta / 365,  # Per day
            "vega": vega / 100,    # Per 1% vol change
            "rho": rho / 100       # Per 1% rate change
        }
    
    def calculate_implied_volatility(
        self,
        market_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str = "call",
        dividend_yield: float = 0.0
    ) -> float:
        """Calculate implied volatility using Newton-Raphson method"""
        
        def bs_price(vol):
            return self.calculate_option_price(
                spot_price, strike_price, time_to_expiry,
                risk_free_rate, vol, option_type, dividend_yield
            )["price"]
        
        def bs_vega(vol):
            return self.calculate_option_price(
                spot_price, strike_price, time_to_expiry,
                risk_free_rate, vol, option_type, dividend_yield
            )["vega"] * 100  # Convert back to per 100% vol change
        
        # Newton-Raphson iteration
        vol = 0.2  # Initial guess
        tolerance = 1e-6
        max_iterations = 100
        
        for i in range(max_iterations):
            price_diff = bs_price(vol) - market_price
            if abs(price_diff) < tolerance:
                return vol
            
            vega = bs_vega(vol)
            if abs(vega) < 1e-10:
                break
                
            vol = vol - price_diff / vega
            
            # Keep volatility in reasonable bounds
            vol = max(0.001, min(vol, 5.0))
        
        return vol


# Initialize service
options_service = OptionsAnalyticsService()


@router.post("/price", response_model=OptionPricingResponse, tags=["Options Analytics"])
async def calculate_option_price(
    request: OptionPricingRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Calculate option price using Black-Scholes model
    
    This endpoint calculates the theoretical price of European options using the
    Black-Scholes-Merton model. It supports both call and put options and includes
    dividend yield adjustments.
    """
    try:
        logger.info(f"Calculating option price for {request.symbol}")
        
        result = options_service.calculate_option_price(
            spot_price=request.spot_price,
            strike_price=request.strike_price,
            time_to_expiry=request.time_to_expiry,
            risk_free_rate=request.risk_free_rate,
            volatility=request.volatility,
            option_type=request.option_type,
            dividend_yield=request.dividend_yield
        )
        
        return OptionPricingResponse(
            symbol=request.symbol,
            option_type=request.option_type,
            spot_price=request.spot_price,
            strike_price=request.strike_price,
            time_to_expiry=request.time_to_expiry,
            risk_free_rate=request.risk_free_rate,
            volatility=request.volatility,
            dividend_yield=request.dividend_yield,
            theoretical_price=result["price"],
            delta=result["delta"],
            gamma=result["gamma"],
            theta=result["theta"],
            vega=result["vega"],
            rho=result["rho"],
            calculation_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error calculating option price: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate option price: {str(e)}"
        )


@router.post("/greeks", response_model=GreeksResponse, tags=["Options Analytics"])
async def calculate_greeks(
    request: GreeksRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho)
    
    This endpoint calculates the risk sensitivities (Greeks) for options positions.
    Greeks help traders understand how option prices change with respect to various
    market parameters.
    """
    try:
        logger.info(f"Calculating Greeks for {request.symbol}")
        
        result = options_service.calculate_option_price(
            spot_price=request.spot_price,
            strike_price=request.strike_price,
            time_to_expiry=request.time_to_expiry,
            risk_free_rate=request.risk_free_rate,
            volatility=request.volatility,
            option_type=request.option_type,
            dividend_yield=request.dividend_yield
        )
        
        return GreeksResponse(
            symbol=request.symbol,
            option_type=request.option_type,
            delta=result["delta"],
            gamma=result["gamma"],
            theta=result["theta"],
            vega=result["vega"],
            rho=result["rho"],
            calculation_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error calculating Greeks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate Greeks: {str(e)}"
        )


@router.post("/implied-volatility", response_model=ImpliedVolatilityResponse, tags=["Options Analytics"])
async def calculate_implied_volatility(
    request: ImpliedVolatilityRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Calculate implied volatility from market price
    
    This endpoint calculates the implied volatility of an option given its market price.
    Implied volatility represents the market's expectation of future volatility.
    """
    try:
        logger.info(f"Calculating implied volatility for {request.symbol}")
        
        implied_vol = options_service.calculate_implied_volatility(
            market_price=request.market_price,
            spot_price=request.spot_price,
            strike_price=request.strike_price,
            time_to_expiry=request.time_to_expiry,
            risk_free_rate=request.risk_free_rate,
            option_type=request.option_type,
            dividend_yield=request.dividend_yield
        )
        
        return ImpliedVolatilityResponse(
            symbol=request.symbol,
            option_type=request.option_type,
            market_price=request.market_price,
            implied_volatility=implied_vol,
            calculation_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error calculating implied volatility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate implied volatility: {str(e)}"
        )


@router.get("/health", tags=["Options Analytics"])
async def options_health_check():
    """Health check for options analytics service"""
    return {
        "status": "healthy",
        "quantlib_available": QUANTLIB_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "options_analytics"
    }