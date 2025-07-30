"""
Comprehensive tests for the Asset Class Framework
Tests all asset classes, pricing models, risk calculations, and lifecycle management
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

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
        equity = EquitySpecification(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            name="Apple Inc.",
            currency="USD",
            exchange="NASDAQ",
            current_price=150.0,
            sector="Technology",
            market_cap=2500000000000,
            dividend_yield=0.005
        )
        
        assert equity.symbol == "AAPL"
        assert equity.asset_class == AssetClass.EQUITY
        assert equity.sector == "Technology"
        assert equity.dividend_yield == 0.005
        assert equity.is_active is True
    
    def test_option_specification_creation(self):
        """Test option specification creation"""
        expiry = datetime(2024, 3, 15)
        option = OptionSpecification(
            symbol="AAPL240315C00150000",
            asset_class=AssetClass.OPTION,
            name="AAPL Call Option",
            currency="USD",
            exchange="CBOE",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            expiry_date=expiry
        )
        
        assert option.symbol == "AAPL240315C00150000"
        assert option.asset_class == AssetClass.OPTION
        assert option.option_type == OptionType.CALL
        assert option.strike_price == 150.0
        assert option.expiry_date == expiry
    
    def test_bond_specification_creation(self):
        """Test bond specification creation"""
        maturity = datetime(2034, 1, 1)
        bond = BondSpecification(
            symbol="US10Y",
            asset_class=AssetClass.BOND,
            name="US 10-Year Treasury",
            currency="USD",
            exchange="NYSE",
            face_value=1000.0,
            coupon_rate=0.04,
            maturity_date=maturity,
            bond_type=BondType.TREASURY
        )
        
        assert bond.symbol == "US10Y"
        assert bond.asset_class == AssetClass.BOND
        assert bond.bond_type == BondType.TREASURY
        assert bond.face_value == 1000.0
        assert bond.coupon_rate == 0.04
    
    def test_future_specification_creation(self):
        """Test future specification creation"""
        expiry = datetime(2024, 6, 15)
        future = FutureSpecification(
            symbol="ESU24",
            asset_class=AssetClass.FUTURE,
            name="E-mini S&P 500 Future",
            currency="USD",
            exchange="CME",
            underlying_symbol="SPX",
            expiry_date=expiry,
            future_type=FutureType.INDEX
        )
        
        assert future.symbol == "ESU24"
        assert future.asset_class == AssetClass.FUTURE
        assert future.future_type == FutureType.INDEX
        assert future.expiry_date == expiry
    
    def test_cryptocurrency_specification_creation(self):
        """Test cryptocurrency specification creation"""
        crypto = CryptocurrencySpecification(
            symbol="BTC/USD",
            asset_class=AssetClass.CRYPTOCURRENCY,
            name="Bitcoin",
            currency="USD",
            exchange="Binance",
            current_price=45000.0,
            circulating_supply=19000000,
            max_supply=21000000
        )
        
        assert crypto.symbol == "BTC/USD"
        assert crypto.asset_class == AssetClass.CRYPTOCURRENCY
        assert crypto.circulating_supply == 19000000
        assert crypto.max_supply == 21000000


class TestEquityPricingModel:
    """Test equity pricing model"""
    
    @pytest.fixture
    def equity_model(self):
        return EquityPricingModel()
    
    @pytest.fixture
    def sample_equity(self):
        return EquitySpecification(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            name="Apple Inc.",
            currency="USD",
            exchange="NASDAQ",
            current_price=150.0,
            market_cap=2500000000000,
            shares_outstanding=16000000000,
            dividend_yield=0.02,
            pe_ratio=25.0
        )
    
    @pytest.mark.asyncio
    async def test_dividend_discount_model(self, equity_model, sample_equity):
        """Test dividend discount model pricing"""
        price = await equity_model.calculate_theoretical_price(
            sample_equity,
            method="dividend_discount",
            growth_rate=0.03,
            discount_rate=0.10
        )
        
        assert price > 0
        assert isinstance(price, float)
    
    @pytest.mark.asyncio
    async def test_pe_multiple_model(self, equity_model, sample_equity):
        """Test P/E multiple model pricing"""
        price = await equity_model.calculate_theoretical_price(
            sample_equity,
            method="pe_multiple",
            target_pe=20.0
        )
        
        assert price > 0
        assert isinstance(price, float)
    
    @pytest.mark.asyncio
    async def test_dcf_model(self, equity_model, sample_equity):
        """Test DCF model pricing"""
        price = await equity_model.calculate_theoretical_price(
            sample_equity,
            method="dcf",
            free_cash_flow=125000000000,
            growth_rate=0.05,
            discount_rate=0.12
        )
        
        assert price > 0
        assert isinstance(price, float)
    
    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, equity_model, sample_equity):
        """Test equity risk metrics calculation"""
        # Generate sample returns
        returns = np.random.normal(0.001, 0.02, 252)
        
        metrics = await equity_model.calculate_risk_metrics(
            sample_equity,
            returns=returns
        )
        
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'var_95' in metrics
        assert 'expected_shortfall' in metrics
        
        assert metrics['volatility'] > 0
        assert isinstance(metrics['max_drawdown'], float)


class TestOptionPricingModel:
    """Test option pricing model"""
    
    @pytest.fixture
    def option_model(self):
        return OptionPricingModel()
    
    @pytest.fixture
    def sample_call_option(self):
        return OptionSpecification(
            symbol="AAPL240315C00150000",
            asset_class=AssetClass.OPTION,
            name="AAPL Call Option",
            currency="USD",
            exchange="CBOE",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            expiry_date=datetime.now() + timedelta(days=30),
            implied_volatility=0.25
        )
    
    @pytest.fixture
    def sample_put_option(self):
        return OptionSpecification(
            symbol="AAPL240315P00150000",
            asset_class=AssetClass.OPTION,
            name="AAPL Put Option",
            currency="USD",
            exchange="CBOE",
            underlying_symbol="AAPL",
            option_type=OptionType.PUT,
            strike_price=150.0,
            expiry_date=datetime.now() + timedelta(days=30),
            implied_volatility=0.25
        )
    
    @pytest.mark.asyncio
    async def test_black_scholes_call_pricing(self, option_model, sample_call_option):
        """Test Black-Scholes call option pricing"""
        price = await option_model.calculate_theoretical_price(
            sample_call_option,
            underlying_price=155.0,
            risk_free_rate=0.05,
            volatility=0.25
        )
        
        assert price > 0
        assert isinstance(price, float)
        # Call option should have intrinsic value when ITM
        assert price >= max(155.0 - 150.0, 0)
    
    @pytest.mark.asyncio
    async def test_black_scholes_put_pricing(self, option_model, sample_put_option):
        """Test Black-Scholes put option pricing"""
        price = await option_model.calculate_theoretical_price(
            sample_put_option,
            underlying_price=145.0,
            risk_free_rate=0.05,
            volatility=0.25
        )
        
        assert price > 0
        assert isinstance(price, float)
        # Put option should have intrinsic value when ITM
        assert price >= max(150.0 - 145.0, 0)
    
    @pytest.mark.asyncio
    async def test_greeks_calculation(self, option_model, sample_call_option):
        """Test option Greeks calculation"""
        metrics = await option_model.calculate_risk_metrics(
            sample_call_option,
            underlying_price=150.0,
            risk_free_rate=0.05,
            volatility=0.25
        )
        
        assert 'delta' in metrics
        assert 'gamma' in metrics
        assert 'theta' in metrics
        assert 'vega' in metrics
        assert 'rho' in metrics
        
        # Delta should be between 0 and 1 for call options
        assert 0 <= metrics['delta'] <= 1
        # Gamma should be positive
        assert metrics['gamma'] >= 0
        # Vega should be positive
        assert metrics['vega'] >= 0
    
    @pytest.mark.asyncio
    async def test_expired_option_pricing(self, option_model):
        """Test pricing of expired options"""
        expired_option = OptionSpecification(
            symbol="EXPIRED",
            asset_class=AssetClass.OPTION,
            name="Expired Option",
            currency="USD",
            exchange="CBOE",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            expiry_date=datetime.now() - timedelta(days=1),
            implied_volatility=0.25
        )
        
        price = await option_model.calculate_theoretical_price(
            expired_option,
            underlying_price=155.0
        )
        
        # Expired ITM call should equal intrinsic value
        assert price == max(155.0 - 150.0, 0)


class TestBondPricingModel:
    """Test bond pricing model"""
    
    @pytest.fixture
    def bond_model(self):
        return BondPricingModel()
    
    @pytest.fixture
    def sample_bond(self):
        return BondSpecification(
            symbol="US10Y",
            asset_class=AssetClass.BOND,
            name="US 10-Year Treasury",
            currency="USD",
            exchange="NYSE",
            face_value=1000.0,
            coupon_rate=0.04,
            maturity_date=datetime.now() + timedelta(days=3650),  # 10 years
            yield_to_maturity=0.045,
            current_price=950.0
        )
    
    @pytest.mark.asyncio
    async def test_ytm_pricing(self, bond_model, sample_bond):
        """Test yield-to-maturity bond pricing"""
        price = await bond_model.calculate_theoretical_price(
            sample_bond,
            yield_to_maturity=0.045
        )
        
        assert price > 0
        assert isinstance(price, float)
        # Price should be close to current price given same YTM
        assert abs(price - sample_bond.current_price) < 100
    
    @pytest.mark.asyncio
    async def test_duration_calculation(self, bond_model, sample_bond):
        """Test bond duration calculation"""
        metrics = await bond_model.calculate_risk_metrics(sample_bond)
        
        assert 'duration' in metrics
        assert 'modified_duration' in metrics
        assert 'convexity' in metrics
        assert 'dv01' in metrics
        
        assert metrics['duration'] > 0
        assert metrics['modified_duration'] > 0
        assert metrics['convexity'] > 0
        assert metrics['dv01'] > 0
    
    @pytest.mark.asyncio
    async def test_matured_bond_pricing(self, bond_model):
        """Test pricing of matured bonds"""
        matured_bond = BondSpecification(
            symbol="MATURED",
            asset_class=AssetClass.BOND,
            name="Matured Bond",
            currency="USD",
            exchange="NYSE",
            face_value=1000.0,
            coupon_rate=0.04,
            maturity_date=datetime.now() - timedelta(days=1),
            yield_to_maturity=0.045
        )
        
        price = await bond_model.calculate_theoretical_price(matured_bond)
        
        # Matured bond should be priced at face value
        assert price == matured_bond.face_value


class TestFuturePricingModel:
    """Test future pricing model"""
    
    @pytest.fixture
    def future_model(self):
        return FuturePricingModel()
    
    @pytest.fixture
    def sample_future(self):
        return FutureSpecification(
            symbol="ESU24",
            asset_class=AssetClass.FUTURE,
            name="E-mini S&P 500 Future",
            currency="USD",
            exchange="CME",
            underlying_symbol="SPX",
            expiry_date=datetime.now() + timedelta(days=90),
            current_price=4500.0,
            initial_margin=12000.0,
            convenience_yield=0.01
        )
    
    @pytest.mark.asyncio
    async def test_cost_of_carry_pricing(self, future_model, sample_future):
        """Test cost of carry future pricing"""
        price = await future_model.calculate_theoretical_price(
            sample_future,
            spot_price=4480.0,
            risk_free_rate=0.05
        )
        
        assert price > 0
        assert isinstance(price, float)
        # Future price should be higher than spot due to carry cost
        assert price > 4480.0
    
    @pytest.mark.asyncio
    async def test_future_risk_metrics(self, future_model, sample_future):
        """Test future risk metrics calculation"""
        metrics = await future_model.calculate_risk_metrics(sample_future)
        
        assert 'basis' in metrics
        assert 'carry_cost' in metrics
        assert 'time_to_expiry' in metrics
        assert 'margin_requirement' in metrics
        assert 'leverage' in metrics
        
        assert metrics['time_to_expiry'] > 0
        assert metrics['margin_requirement'] == sample_future.initial_margin
        assert metrics['leverage'] > 0


class TestCryptocurrencyPricingModel:
    """Test cryptocurrency pricing model"""
    
    @pytest.fixture
    def crypto_model(self):
        return CryptocurrencyPricingModel()
    
    @pytest.fixture
    def sample_crypto(self):
        return CryptocurrencySpecification(
            symbol="BTC/USD",
            asset_class=AssetClass.CRYPTOCURRENCY,
            name="Bitcoin",
            currency="USD",
            exchange="Binance",
            current_price=45000.0,
            circulating_supply=19000000,
            max_supply=21000000,
            hash_rate=150000000000000000000,
            realized_volatility_30d=0.60
        )
    
    @pytest.mark.asyncio
    async def test_network_value_model(self, crypto_model, sample_crypto):
        """Test network value model pricing"""
        price = await crypto_model.calculate_theoretical_price(
            sample_crypto,
            method="network_value",
            network_users=100000000,
            value_per_user=50
        )
        
        assert price > 0
        assert isinstance(price, float)
    
    @pytest.mark.asyncio
    async def test_stock_to_flow_model(self, crypto_model, sample_crypto):
        """Test stock-to-flow model pricing"""
        price = await crypto_model.calculate_theoretical_price(
            sample_crypto,
            method="stock_to_flow",
            annual_production=328500  # Approximate Bitcoin annual production
        )
        
        assert price > 0
        assert isinstance(price, float)
    
    @pytest.mark.asyncio
    async def test_crypto_risk_metrics(self, crypto_model, sample_crypto):
        """Test cryptocurrency risk metrics"""
        # Generate high volatility returns for crypto
        returns = np.random.normal(0.002, 0.05, 252)
        
        metrics = await crypto_model.calculate_risk_metrics(
            sample_crypto,
            returns=returns
        )
        
        assert 'volatility' in metrics
        assert 'realized_volatility_30d' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'supply_inflation' in metrics
        
        assert metrics['volatility'] > 0
        assert metrics['supply_inflation'] >= 0


class TestAssetLifecycleManager:
    """Test asset lifecycle management"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        return AssetLifecycleManager()
    
    @pytest.fixture
    def sample_equity(self):
        return EquitySpecification(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            name="Apple Inc.",
            currency="USD",
            exchange="NASDAQ",
            current_price=150.0
        )
    
    @pytest.mark.asyncio
    async def test_dividend_payment_handling(self, lifecycle_manager, sample_equity):
        """Test dividend payment handling"""
        original_price = sample_equity.current_price
        dividend_amount = 0.50
        ex_date = datetime.now()
        
        await lifecycle_manager.handle_dividend_payment(
            sample_equity, dividend_amount, ex_date
        )
        
        # Price should be adjusted for dividend
        assert sample_equity.current_price == original_price - dividend_amount
        
        # Event should be recorded
        events = lifecycle_manager.get_lifecycle_events("AAPL")
        assert len(events) == 1
        assert events[0]['type'] == 'dividend'
        assert events[0]['amount'] == dividend_amount
    
    @pytest.mark.asyncio
    async def test_stock_split_handling(self, lifecycle_manager, sample_equity):
        """Test stock split handling"""
        original_price = sample_equity.current_price
        original_shares = sample_equity.shares_outstanding
        split_ratio = 2.0
        
        await lifecycle_manager.handle_stock_split(sample_equity, split_ratio)
        
        # Price should be halved, shares should be doubled
        assert sample_equity.current_price == original_price / split_ratio
        assert sample_equity.shares_outstanding == original_shares * split_ratio
        
        # Event should be recorded
        events = lifecycle_manager.get_lifecycle_events("AAPL")
        assert len(events) == 1
        assert events[0]['type'] == 'stock_split'
        assert events[0]['split_ratio'] == split_ratio
    
    @pytest.mark.asyncio
    async def test_option_expiry_handling(self, lifecycle_manager):
        """Test option expiry handling"""
        expired_option = OptionSpecification(
            symbol="EXPIRED_OPTION",
            asset_class=AssetClass.OPTION,
            name="Expired Option",
            currency="USD",
            exchange="CBOE",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            expiry_date=datetime.now() - timedelta(days=1),
            current_price=5.0,
            is_active=True
        )
        
        await lifecycle_manager.handle_option_expiry(expired_option)
        
        # Option should be marked as inactive and price set to 0
        assert not expired_option.is_active
        assert expired_option.current_price == 0.0
        
        # Event should be recorded
        events = lifecycle_manager.get_lifecycle_events("EXPIRED_OPTION")
        assert len(events) == 1
        assert events[0]['type'] == 'option_expiry'


class TestAssetClassFramework:
    """Test main asset class framework"""
    
    @pytest.fixture
    def framework(self):
        return AssetClassFramework()
    
    @pytest.fixture
    def sample_assets(self):
        """Create sample assets for testing"""
        equity = create_equity_asset(
            symbol="AAPL",
            name="Apple Inc.",
            current_price=150.0,
            market_cap=2500000000000,
            dividend_yield=0.005
        )
        
        option = create_option_asset(
            symbol="AAPL240315C00150000",
            underlying_symbol="AAPL",
            option_type=OptionType.CALL,
            strike_price=150.0,
            expiry_date=datetime.now() + timedelta(days=30),
            current_price=5.0
        )
        
        bond = create_bond_asset(
            symbol="US10Y",
            name="US 10-Year Treasury",
            face_value=1000.0,
            coupon_rate=0.04,
            maturity_date=datetime.now() + timedelta(days=3650),
            current_price=950.0
        )
        
        return [equity, option, bond]
    
    def test_asset_registration(self, framework, sample_assets):
        """Test asset registration"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        assert len(framework.assets) == 3
        assert framework.get_asset("AAPL") is not None
        assert framework.get_asset("AAPL240315C00150000") is not None
        assert framework.get_asset("US10Y") is not None
    
    def test_get_assets_by_class(self, framework, sample_assets):
        """Test getting assets by class"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        equities = framework.get_assets_by_class(AssetClass.EQUITY)
        options = framework.get_assets_by_class(AssetClass.OPTION)
        bonds = framework.get_assets_by_class(AssetClass.BOND)
        
        assert len(equities) == 1
        assert len(options) == 1
        assert len(bonds) == 1
        assert equities[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_theoretical_price_calculation(self, framework, sample_assets):
        """Test theoretical price calculation"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        # Test equity pricing
        equity_price = await framework.calculate_theoretical_price("AAPL")
        assert equity_price is not None
        assert equity_price > 0
        
        # Test option pricing
        option_price = await framework.calculate_theoretical_price(
            "AAPL240315C00150000", underlying_price=150.0
        )
        assert option_price is not None
        assert option_price > 0
        
        # Test bond pricing
        bond_price = await framework.calculate_theoretical_price("US10Y")
        assert bond_price is not None
        assert bond_price > 0
    
    @pytest.mark.asyncio
    async def test_risk_metrics_calculation(self, framework, sample_assets):
        """Test risk metrics calculation"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        # Test equity risk metrics
        equity_risk = await framework.calculate_risk_metrics("AAPL")
        assert equity_risk is not None
        assert 'volatility' in equity_risk
        
        # Test option risk metrics
        option_risk = await framework.calculate_risk_metrics(
            "AAPL240315C00150000", underlying_price=150.0
        )
        assert option_risk is not None
        assert 'delta' in option_risk
    
    @pytest.mark.asyncio
    async def test_market_data_update(self, framework, sample_assets):
        """Test market data updates"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        await framework.update_market_data("AAPL", 155.0, 154.5, 155.5, 1000000)
        
        asset = framework.get_asset("AAPL")
        assert asset.current_price == 155.0
        assert asset.bid_price == 154.5
        assert asset.ask_price == 155.5
        assert asset.volume == 1000000
    
    def test_portfolio_summary(self, framework, sample_assets):
        """Test portfolio summary generation"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        summary = framework.get_portfolio_summary(["AAPL", "AAPL240315C00150000", "US10Y"])
        
        assert summary['total_assets'] == 3
        assert summary['asset_classes']['equity'] == 1
        assert summary['asset_classes']['option'] == 1
        assert summary['asset_classes']['bond'] == 1
        assert len(summary['assets']) == 3
    
    @pytest.mark.asyncio
    async def test_batch_calculations(self, framework, sample_assets):
        """Test batch calculations"""
        for asset in sample_assets:
            framework.register_asset(asset)
        
        results = await framework.run_batch_calculations(
            ["AAPL", "US10Y"],
            calculation_type="both"
        )
        
        assert "AAPL" in results
        assert "US10Y" in results
        assert 'theoretical_price' in results["AAPL"]
        assert 'risk_metrics' in results["AAPL"]


class TestFactoryFunctions:
    """Test asset factory functions"""
    
    def test_create_equity_asset(self):
        """Test equity asset creation"""
        equity = create_equity_asset(
            symbol="MSFT",
            name="Microsoft Corporation",
            current_price=300.0,
            sector="Technology",
            market_cap=2200000000000
        )
        
        assert equity.symbol == "MSFT"
        assert equity.asset_class == AssetClass.EQUITY
        assert equity.current_price == 300.0
        assert equity.sector == "Technology"
    
    def test_create_option_asset(self):
        """Test option asset creation"""
        option = create_option_asset(
            symbol="MSFT240315P00300000",
            underlying_symbol="MSFT",
            option_type=OptionType.PUT,
            strike_price=300.0,
            expiry_date=datetime(2024, 3, 15),
            current_price=8.0
        )
        
        assert option.symbol == "MSFT240315P00300000"
        assert option.asset_class == AssetClass.OPTION
        assert option.option_type == OptionType.PUT
        assert option.strike_price == 300.0
    
    def test_create_bond_asset(self):
        """Test bond asset creation"""
        bond = create_bond_asset(
            symbol="CORP5Y",
            name="Corporate 5-Year Bond",
            face_value=1000.0,
            coupon_rate=0.035,
            maturity_date=datetime(2029, 1, 1),
            bond_type=BondType.CORPORATE
        )
        
        assert bond.symbol == "CORP5Y"
        assert bond.asset_class == AssetClass.BOND
        assert bond.bond_type == BondType.CORPORATE
        assert bond.coupon_rate == 0.035
    
    def test_create_future_asset(self):
        """Test future asset creation"""
        future = create_future_asset(
            symbol="CLZ24",
            underlying_symbol="CL",
            expiry_date=datetime(2024, 12, 15),
            future_type=FutureType.COMMODITY,
            current_price=75.0
        )
        
        assert future.symbol == "CLZ24"
        assert future.asset_class == AssetClass.FUTURE
        assert future.future_type == FutureType.COMMODITY
        assert future.current_price == 75.0
    
    def test_create_cryptocurrency_asset(self):
        """Test cryptocurrency asset creation"""
        crypto = create_cryptocurrency_asset(
            symbol="ETH/USD",
            name="Ethereum",
            current_price=2500.0,
            circulating_supply=120000000,
            market_cap_rank=2
        )
        
        assert crypto.symbol == "ETH/USD"
        assert crypto.asset_class == AssetClass.CRYPTOCURRENCY
        assert crypto.current_price == 2500.0
        assert crypto.market_cap_rank == 2


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    framework = AssetClassFramework()
    
    # Create and register assets
    equity = create_equity_asset("GOOGL", "Alphabet Inc.", 2800.0, market_cap=1800000000000)
    option = create_option_asset(
        "GOOGL240315C02800000", "GOOGL", OptionType.CALL, 2800.0,
        datetime.now() + timedelta(days=45), current_price=120.0
    )
    
    framework.register_asset(equity)
    framework.register_asset(option)
    
    # Update market data
    await framework.update_market_data("GOOGL", 2850.0, 2849.0, 2851.0, 500000)
    
    # Calculate theoretical prices
    equity_price = await framework.calculate_theoretical_price("GOOGL")
    option_price = await framework.calculate_theoretical_price("GOOGL240315C02800000", underlying_price=2850.0)
    
    # Calculate risk metrics
    equity_risk = await framework.calculate_risk_metrics("GOOGL")
    option_risk = await framework.calculate_risk_metrics("GOOGL240315C02800000", underlying_price=2850.0)
    
    # Generate portfolio summary
    portfolio = framework.get_portfolio_summary(["GOOGL", "GOOGL240315C02800000"])
    
    # Assertions
    assert equity_price > 0
    assert option_price > 0
    assert 'volatility' in equity_risk
    assert 'delta' in option_risk
    assert portfolio['total_assets'] == 2
    
    # Process lifecycle events
    await framework.process_lifecycle_events()
    
    print("Integration test completed successfully!")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())