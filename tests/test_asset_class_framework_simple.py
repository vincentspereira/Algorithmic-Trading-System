"""
Tests for Asset Class Framework (Simplified Version)
"""

import pytest
import asyncio
from datetime import datetime

from nautilus_trader_engine.assets.asset_class_framework import (
    AssetClass, OptionType,
    AssetSpecification, EquitySpecification, OptionSpecification,
    EquityPricingModel, OptionPricingModel,
    AssetClassFramework,
    create_equity_asset, create_option_asset
)


class TestAssetSpecifications:
    """Test asset specification classes"""
    
    def test_equity_specification_creation(self):
        """Test equity specification creation"""
        equity = create_equity_asset(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=150.0,
            market_cap=2500000000000,
            pe_ratio=25.0,
            dividend_yield=0.005
        )
        
        assert equity.symbol == "AAPL"
        assert equity.name == "Apple Inc."
        assert equity.asset_class == AssetClass.EQUITY
        assert equity.current_price == 150.0
        assert equity.pe_ratio == 25.0
        assert equity.is_active is True
    
    def test_option_specification_creation(self):
        """Test option specification creation"""
        option = create_option_asset(
            symbol="AAPL240315C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            current_price=5.0,
            implied_volatility=0.25
        )
        
        assert option.symbol == "AAPL240315C00150000"
        assert option.asset_class == AssetClass.OPTION
        assert option.underlying_symbol == "AAPL"
        assert option.option_type == OptionType.CALL
        assert option.strike_price == 150.0
        assert option.implied_volatility == 0.25


class TestEquityPricingModel:
    """Test equity pricing model"""
    
    @pytest.fixture
    def equity_model(self):
        return EquityPricingModel()
    
    @pytest.fixture
    def sample_equity(self):
        return create_equity_asset(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=150.0,
            pe_ratio=25.0,
            dividend_yield=0.005
        )
    
    @pytest.mark.asyncio
    async def test_pe_multiple_model(self, equity_model, sample_equity):
        """Test P/E multiple model pricing"""
        price = await equity_model.calculate_theoretical_price(
            sample_equity,
            method="pe_multiple",
            target_pe=20.0
        )
        
        # Expected: (150/25) * 20 = 120
        assert abs(price - 120.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, equity_model, sample_equity):
        """Test equity risk metrics calculation"""
        import numpy as np
        
        # Generate sample returns
        returns = np.random.normal(0.001, 0.02, 252)
        
        metrics = await equity_model.calculate_risk_metrics(
            sample_equity,
            returns=returns
        )
        
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'var_95' in metrics
        assert metrics['volatility'] > 0


class TestOptionPricingModel:
    """Test option pricing model"""
    
    @pytest.fixture
    def option_model(self):
        return OptionPricingModel()
    
    @pytest.fixture
    def sample_call_option(self):
        return create_option_asset(
            symbol="AAPL240315C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            current_price=5.0,
            implied_volatility=0.25
        )
    
    @pytest.mark.asyncio
    async def test_black_scholes_call_pricing(self, option_model, sample_call_option):
        """Test Black-Scholes call option pricing"""
        price = await option_model.calculate_theoretical_price(
            sample_call_option,
            underlying_price=155.0,
            time_to_expiry=0.25,
            risk_free_rate=0.05,
            volatility=0.25
        )
        
        # Should be positive for ITM call
        assert price > 5.0  # Should be at least intrinsic value
        assert price < 155.0  # Should be less than underlying price
    
    @pytest.mark.asyncio
    async def test_greeks_calculation(self, option_model, sample_call_option):
        """Test option Greeks calculation"""
        metrics = await option_model.calculate_risk_metrics(
            sample_call_option,
            underlying_price=155.0,
            time_to_expiry=0.25,
            risk_free_rate=0.05,
            volatility=0.25
        )
        
        assert 'delta' in metrics
        assert 'gamma' in metrics
        assert 'theta' in metrics
        assert 'vega' in metrics
        
        # Call delta should be positive
        assert metrics['delta'] > 0
        assert metrics['delta'] < 1
        
        # Gamma should be positive
        assert metrics['gamma'] > 0


class TestAssetClassFramework:
    """Test main framework class"""
    
    @pytest.fixture
    def framework(self):
        return AssetClassFramework()
    
    @pytest.fixture
    def sample_assets(self):
        equity = create_equity_asset(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=150.0,
            pe_ratio=25.0
        )
        
        option = create_option_asset(
            symbol="AAPL240315C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            current_price=5.0
        )
        
        return [equity, option]
    
    @pytest.mark.asyncio
    async def test_asset_registration(self, framework, sample_assets):
        """Test asset registration"""
        for asset in sample_assets:
            result = await framework.register_asset(asset)
            assert result is True
        
        assert len(framework.assets) == 2
        assert await framework.get_asset("AAPL") is not None
        assert await framework.get_asset("AAPL240315C00150000") is not None
    
    @pytest.mark.asyncio
    async def test_theoretical_price_calculation(self, framework, sample_assets):
        """Test theoretical price calculation"""
        for asset in sample_assets:
            await framework.register_asset(asset)
        
        # Test equity pricing
        equity_price = await framework.calculate_theoretical_price(
            "AAPL",
            target_pe=20.0
        )
        assert equity_price is not None
        assert equity_price > 0
        
        # Test option pricing
        option_price = await framework.calculate_theoretical_price(
            "AAPL240315C00150000",
            underlying_price=155.0
        )
        assert option_price is not None
        assert option_price > 0
    
    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, framework, sample_assets):
        """Test risk metrics calculation"""
        for asset in sample_assets:
            await framework.register_asset(asset)
        
        # Test equity risk metrics
        equity_metrics = await framework.calculate_risk_metrics("AAPL")
        assert equity_metrics is not None
        assert 'volatility' in equity_metrics
        
        # Test option risk metrics
        option_metrics = await framework.calculate_risk_metrics(
            "AAPL240315C00150000",
            underlying_price=155.0
        )
        assert option_metrics is not None
        assert 'delta' in option_metrics
    
    def test_get_assets_by_class(self, framework, sample_assets):
        """Test getting assets by class"""
        # Register assets synchronously for this test
        for asset in sample_assets:
            framework.assets[asset.symbol] = asset
        
        equities = framework.get_assets_by_class(AssetClass.EQUITY)
        options = framework.get_assets_by_class(AssetClass.OPTION)
        
        assert len(equities) == 1
        assert len(options) == 1
        assert equities[0].symbol == "AAPL"
        assert options[0].symbol == "AAPL240315C00150000"


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    framework = AssetClassFramework()
    
    # Create and register assets
    equity = create_equity_asset(
        symbol="AAPL",
        name="Apple Inc.",
        current_price=150.0,
        pe_ratio=25.0
    )
    
    option = create_option_asset(
        symbol="AAPL240315C00150000",
        underlying_symbol="AAPL",
        option_type=OptionType.CALL,
        strike_price=150.0,
        current_price=5.0,
        implied_volatility=0.25
    )
    
    await framework.register_asset(equity)
    await framework.register_asset(option)
    
    # Calculate theoretical prices
    equity_price = await framework.calculate_theoretical_price("AAPL", target_pe=20.0)
    option_price = await framework.calculate_theoretical_price(
        "AAPL240315C00150000",
        underlying_price=155.0
    )
    
    # Calculate risk metrics
    equity_risk = await framework.calculate_risk_metrics("AAPL")
    option_risk = await framework.calculate_risk_metrics(
        "AAPL240315C00150000",
        underlying_price=155.0
    )
    
    # Verify results
    assert equity_price == 120.0  # (150/25) * 20
    assert option_price > 5.0  # Should be greater than intrinsic value
    assert 'volatility' in equity_risk
    assert 'delta' in option_risk
    
    print(f"Integration test completed successfully!")
    print(f"Equity theoretical price: ${equity_price:.2f}")
    print(f"Option theoretical price: ${option_price:.2f}")
    print(f"Equity volatility: {equity_risk['volatility']:.4f}")
    print(f"Option delta: {option_risk['delta']:.4f}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())