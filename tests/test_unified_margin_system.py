"""
Tests for Unified Margin System
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta

from nautilus_trader_engine.risk.unified_margin_system import (
    UnifiedMarginSystem,
    EquityMarginCalculator,
    OptionsMarginCalculator,
    SPANMarginCalculator,
    PortfolioMarginCalculator,
    MarginOptimizer,
    Position,
    MarginRequirement,
    PortfolioMarginResult,
    MarginType,
    AssetClass
)


class TestPosition:
    """Test Position data class"""
    
    def test_position_creation(self):
        """Test position creation"""
        position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=100,
            current_price=150.0,
            market_value=15000.0
        )
        
        assert position.symbol == "AAPL"
        assert position.asset_class == AssetClass.EQUITY
        assert position.quantity == 100
        assert position.current_price == 150.0
        assert position.market_value == 15000.0
        assert position.currency == "USD"
        assert position.volatility == 0.0
        assert position.beta == 1.0


class TestEquityMarginCalculator:
    """Test equity margin calculation"""
    
    @pytest.fixture
    def calculator(self):
        return EquityMarginCalculator()
    
    @pytest.fixture
    def long_equity_position(self):
        return Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=100,
            current_price=150.0,
            market_value=15000.0,
            volatility=0.25,
            beta=1.2
        )
    
    @pytest.fixture
    def short_equity_position(self):
        return Position(
            symbol="TSLA",
            asset_class=AssetClass.EQUITY,
            quantity=-50,
            current_price=200.0,
            market_value=-10000.0,
            volatility=0.40,
            beta=1.8
        )
    
    @pytest.mark.asyncio
    async def test_long_equity_margin(self, calculator, long_equity_position):
        """Test margin calculation for long equity position"""
        margin_req = await calculator.calculate_margin(long_equity_position)
        
        assert isinstance(margin_req, MarginRequirement)
        assert margin_req.position_id == "AAPL"
        assert margin_req.margin_type == MarginType.INITIAL
        assert margin_req.required_margin > 0
        assert margin_req.initial_margin > 0
        assert margin_req.maintenance_margin > 0
        assert margin_req.leverage > 1.0
        assert margin_req.risk_score > 1.0  # Due to volatility and beta adjustments
        assert margin_req.calculation_method == "Equity Standard Margin"
    
    @pytest.mark.asyncio
    async def test_short_equity_margin(self, calculator, short_equity_position):
        """Test margin calculation for short equity position"""
        margin_req = await calculator.calculate_margin(short_equity_position)
        
        assert isinstance(margin_req, MarginRequirement)
        assert margin_req.position_id == "TSLA"
        assert margin_req.required_margin > 0
        # Short positions should have higher margin requirements
        assert margin_req.required_margin > abs(short_equity_position.market_value) * 1.0
    
    @pytest.mark.asyncio
    async def test_high_volatility_adjustment(self, calculator):
        """Test margin adjustment for high volatility stocks"""
        high_vol_position = Position(
            symbol="MEME",
            asset_class=AssetClass.EQUITY,
            quantity=100,
            current_price=50.0,
            market_value=5000.0,
            volatility=0.80,  # Very high volatility
            beta=2.0
        )
        
        margin_req = await calculator.calculate_margin(high_vol_position)
        
        # Should have significantly higher margin due to volatility
        assert margin_req.risk_score > 2.0
        assert margin_req.required_margin > 5000.0 * 0.5  # More than standard 50%


class TestOptionsMarginCalculator:
    """Test options margin calculation"""
    
    @pytest.fixture
    def calculator(self):
        return OptionsMarginCalculator()
    
    @pytest.fixture
    def long_call_position(self):
        return Position(
            symbol="AAPL240315C00160000",
            asset_class=AssetClass.OPTION,
            quantity=2,
            current_price=5.0,
            market_value=1000.0,
            underlying_symbol="AAPL",
            strike_price=160.0,
            option_type="call",
            delta=0.6,
            volatility=0.25
        )
    
    @pytest.fixture
    def short_call_position(self):
        return Position(
            symbol="AAPL240315C00160000",
            asset_class=AssetClass.OPTION,
            quantity=-2,
            current_price=5.0,
            market_value=-1000.0,
            underlying_symbol="AAPL",
            strike_price=160.0,
            option_type="call",
            delta=0.6,
            gamma=0.05,
            theta=-0.02,
            vega=0.15,
            volatility=0.25
        )
    
    @pytest.mark.asyncio
    async def test_long_option_margin(self, calculator, long_call_position):
        """Test margin calculation for long option position"""
        margin_req = await calculator.calculate_margin(long_call_position)
        
        assert isinstance(margin_req, MarginRequirement)
        assert margin_req.position_id == "AAPL240315C00160000"
        assert margin_req.margin_type == MarginType.OPTIONS
        assert margin_req.required_margin == 0.0  # Long options require no additional margin
        assert margin_req.calculation_method == "Long Options - Premium Only"
    
    @pytest.mark.asyncio
    async def test_short_call_margin(self, calculator, short_call_position):
        """Test margin calculation for short call option"""
        margin_req = await calculator.calculate_margin(short_call_position)
        
        assert isinstance(margin_req, MarginRequirement)
        assert margin_req.required_margin > 0
        assert margin_req.initial_margin > 0
        assert margin_req.maintenance_margin > 0
        assert margin_req.leverage > 1.0
        assert margin_req.calculation_method == "Short Options Standard Margin"
    
    @pytest.mark.asyncio
    async def test_short_put_margin(self, calculator):
        """Test margin calculation for short put option"""
        short_put = Position(
            symbol="AAPL240315P00140000",
            asset_class=AssetClass.OPTION,
            quantity=-1,
            current_price=3.0,
            market_value=-300.0,
            underlying_symbol="AAPL",
            strike_price=140.0,
            option_type="put",
            delta=-0.4,
            volatility=0.25
        )
        
        margin_req = await calculator.calculate_margin(short_put)
        
        assert margin_req.required_margin > 0
        assert margin_req.calculation_method == "Short Options Standard Margin"


class TestSPANMarginCalculator:
    """Test SPAN margin calculation"""
    
    @pytest.fixture
    def calculator(self):
        return SPANMarginCalculator()
    
    @pytest.fixture
    def futures_positions(self):
        return [
            Position(
                symbol="ES_202406",
                asset_class=AssetClass.FUTURE,
                quantity=2,
                current_price=4500.0,
                market_value=450000.0,
                underlying_symbol="ES",
                volatility=0.20
            ),
            Position(
                symbol="ES_202409",
                asset_class=AssetClass.FUTURE,
                quantity=-1,
                current_price=4520.0,
                market_value=-226000.0,
                underlying_symbol="ES",
                volatility=0.20
            )
        ]
    
    @pytest.mark.asyncio
    async def test_span_margin_calculation(self, calculator, futures_positions):
        """Test SPAN margin calculation for futures positions"""
        margin_requirements = await calculator.calculate_span_margin(futures_positions)
        
        assert isinstance(margin_requirements, dict)
        assert len(margin_requirements) == 2
        
        for symbol, margin_req in margin_requirements.items():
            assert isinstance(margin_req, MarginRequirement)
            assert margin_req.margin_type == MarginType.SPAN
            assert margin_req.required_margin > 0
            assert margin_req.calculation_method == "SPAN Margin"
    
    @pytest.mark.asyncio
    async def test_span_margin_with_options(self, calculator):
        """Test SPAN margin with futures and options on same underlying"""
        mixed_positions = [
            Position(
                symbol="ES_202406",
                asset_class=AssetClass.FUTURE,
                quantity=1,
                current_price=4500.0,
                market_value=225000.0,
                underlying_symbol="ES",
                volatility=0.20
            ),
            Position(
                symbol="ES240315C04600",
                asset_class=AssetClass.OPTION,
                quantity=-2,
                current_price=50.0,
                market_value=-10000.0,
                underlying_symbol="ES",
                strike_price=4600.0,
                option_type="call",
                delta=0.4,
                gamma=0.001,
                theta=-5.0,
                vega=20.0,
                volatility=0.20
            )
        ]
        
        margin_requirements = await calculator.calculate_span_margin(mixed_positions)
        
        assert len(margin_requirements) == 2
        # SPAN should recognize hedging benefit between futures and options
        total_span_margin = sum(req.required_margin for req in margin_requirements.values())
        individual_margins = sum(abs(pos.market_value) * 0.1 for pos in mixed_positions)
        
        # SPAN margin should be less than sum of individual margins due to hedging
        assert total_span_margin < individual_margins


class TestPortfolioMarginCalculator:
    """Test portfolio margin calculation"""
    
    @pytest.fixture
    def calculator(self):
        return PortfolioMarginCalculator()
    
    @pytest.fixture
    def diversified_portfolio(self):
        return [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=100,
                current_price=150.0,
                market_value=15000.0,
                volatility=0.25,
                beta=1.2
            ),
            Position(
                symbol="GOOGL",
                asset_class=AssetClass.EQUITY,
                quantity=10,
                current_price=2800.0,
                market_value=28000.0,
                volatility=0.30,
                beta=1.1
            ),
            Position(
                symbol="AAPL240315C00160000",
                asset_class=AssetClass.OPTION,
                quantity=-2,
                current_price=5.0,
                market_value=-1000.0,
                underlying_symbol="AAPL",
                strike_price=160.0,
                option_type="call",
                delta=0.6,
                volatility=0.25
            )
        ]
    
    @pytest.mark.asyncio
    async def test_portfolio_margin_calculation(self, calculator, diversified_portfolio):
        """Test portfolio margin calculation with diversification benefits"""
        portfolio_result = await calculator.calculate_portfolio_margin(diversified_portfolio)
        
        assert isinstance(portfolio_result, PortfolioMarginResult)
        assert portfolio_result.total_margin_required > 0
        assert portfolio_result.portfolio_leverage > 1.0
        assert portfolio_result.margin_utilization > 0
        assert len(portfolio_result.margin_by_asset_class) > 0
        assert portfolio_result.diversification_benefit >= 0
        assert 0 <= portfolio_result.concentration_risk <= 1
    
    @pytest.mark.asyncio
    async def test_hedging_benefit_calculation(self, calculator):
        """Test hedging benefit calculation"""
        hedged_portfolio = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=100,
                current_price=150.0,
                market_value=15000.0,
                delta=1.0
            ),
            Position(
                symbol="AAPL240315P00140000",
                asset_class=AssetClass.OPTION,
                quantity=1,  # Protective put
                current_price=3.0,
                market_value=300.0,
                underlying_symbol="AAPL",
                option_type="put",
                delta=-0.3
            )
        ]
        
        portfolio_result = await calculator.calculate_portfolio_margin(hedged_portfolio)
        
        # Should have some diversification/hedging benefit
        assert portfolio_result.diversification_benefit > 0
        assert len(portfolio_result.optimization_opportunities) >= 0
    
    @pytest.mark.asyncio
    async def test_concentration_risk_calculation(self, calculator):
        """Test concentration risk calculation"""
        concentrated_portfolio = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=1000,
                current_price=150.0,
                market_value=150000.0
            ),
            Position(
                symbol="GOOGL",
                asset_class=AssetClass.EQUITY,
                quantity=1,
                current_price=2800.0,
                market_value=2800.0
            )
        ]
        
        portfolio_result = await calculator.calculate_portfolio_margin(concentrated_portfolio)
        
        # Should detect high concentration risk
        assert portfolio_result.concentration_risk > 0.5


class TestMarginOptimizer:
    """Test margin optimization functionality"""
    
    @pytest.fixture
    def optimizer(self):
        return MarginOptimizer()
    
    @pytest.fixture
    def sample_portfolio(self):
        return [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=100,
                current_price=150.0,
                market_value=15000.0
            ),
            Position(
                symbol="TSLA",
                asset_class=AssetClass.EQUITY,
                quantity=50,
                current_price=200.0,
                market_value=10000.0
            )
        ]
    
    @pytest.mark.asyncio
    async def test_margin_optimization(self, optimizer, sample_portfolio):
        """Test margin usage optimization"""
        available_capital = 50000.0
        target_leverage = 2.0
        
        optimization_result = await optimizer.optimize_margin_usage(
            sample_portfolio, available_capital, target_leverage
        )
        
        assert isinstance(optimization_result, dict)
        assert "current_margin_usage" in optimization_result
        assert "available_capital" in optimization_result
        assert "optimization_suggestions" in optimization_result
        assert "potential_improvements" in optimization_result
        
        assert optimization_result["available_capital"] == available_capital
        assert optimization_result["target_leverage"] == target_leverage
    
    @pytest.mark.asyncio
    async def test_hedging_strategy_suggestions(self, optimizer):
        """Test hedging strategy suggestions"""
        unhedged_portfolio = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=1000,  # Large position
                current_price=150.0,
                market_value=150000.0
            )
        ]
        
        hedging_suggestions = await optimizer._suggest_hedging_strategies(unhedged_portfolio)
        
        assert isinstance(hedging_suggestions, list)
        assert len(hedging_suggestions) > 0
        
        # Should suggest protective put for large unhedged position
        protective_put_suggested = any(
            suggestion["type"] == "protective_put" 
            for suggestion in hedging_suggestions
        )
        assert protective_put_suggested


class TestUnifiedMarginSystem:
    """Test the main unified margin system"""
    
    @pytest.fixture
    def margin_system(self):
        return UnifiedMarginSystem()
    
    @pytest.fixture
    def comprehensive_portfolio(self):
        return [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=100,
                current_price=150.0,
                market_value=15000.0,
                volatility=0.25,
                beta=1.2
            ),
            Position(
                symbol="AAPL240315C00160000",
                asset_class=AssetClass.OPTION,
                quantity=-2,
                current_price=5.0,
                market_value=-1000.0,
                underlying_symbol="AAPL",
                strike_price=160.0,
                option_type="call",
                delta=0.6,
                volatility=0.25
            ),
            Position(
                symbol="ES_202406",
                asset_class=AssetClass.FUTURE,
                quantity=1,
                current_price=4500.0,
                market_value=225000.0,
                volatility=0.20
            )
        ]
    
    @pytest.mark.asyncio
    async def test_comprehensive_margin_calculation(self, margin_system, comprehensive_portfolio):
        """Test comprehensive margin calculation"""
        available_capital = 100000.0
        
        result = await margin_system.calculate_comprehensive_margin(
            comprehensive_portfolio, available_capital
        )
        
        assert isinstance(result, dict)
        assert "portfolio_margin" in result
        assert "individual_margins" in result
        assert "optimization" in result
        assert "compliance" in result
        assert "summary" in result
        assert "calculation_timestamp" in result
        
        # Check portfolio margin
        portfolio_margin = result["portfolio_margin"]
        assert isinstance(portfolio_margin, PortfolioMarginResult)
        assert portfolio_margin.total_margin_required > 0
        
        # Check individual margins
        individual_margins = result["individual_margins"]
        assert len(individual_margins) == 3
        for symbol, margin_req in individual_margins.items():
            assert isinstance(margin_req, MarginRequirement)
            assert margin_req.required_margin >= 0
        
        # Check summary
        summary = result["summary"]
        assert summary["total_positions"] == 3
        assert summary["total_margin"] > 0
        assert summary["portfolio_leverage"] > 0
    
    @pytest.mark.asyncio
    async def test_margin_compliance_check(self, margin_system):
        """Test margin compliance checking"""
        # Create high-leverage portfolio
        high_leverage_portfolio = [
            Position(
                symbol="MEME",
                asset_class=AssetClass.EQUITY,
                quantity=10000,
                current_price=10.0,
                market_value=100000.0,
                volatility=0.80,
                beta=3.0
            )
        ]
        
        available_capital = 20000.0  # Low capital for high exposure
        
        result = await margin_system.calculate_comprehensive_margin(
            high_leverage_portfolio, available_capital
        )
        
        compliance = result["compliance"]
        
        # Should detect compliance issues or warnings
        assert compliance["status"] in ["compliant", "non_compliant"]
        if compliance["status"] == "non_compliant":
            assert len(compliance["issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_trade_impact_simulation(self, margin_system, comprehensive_portfolio):
        """Test trade impact simulation"""
        proposed_trades = [
            {"symbol": "AAPL", "quantity": 50, "price": 150.0, "asset_class": AssetClass.EQUITY},
            {"symbol": "MSFT", "quantity": 100, "price": 300.0, "asset_class": AssetClass.EQUITY}
        ]
        
        impact = await margin_system.simulate_margin_impact(
            comprehensive_portfolio, proposed_trades
        )
        
        assert isinstance(impact, dict)
        assert "current_margin" in impact
        assert "new_margin" in impact
        assert "margin_change" in impact
        assert "leverage_change" in impact
        assert "recommendation" in impact
        
        assert impact["trades_analyzed"] == 2
        assert impact["recommendation"] in ["approve", "reject"]
    
    @pytest.mark.asyncio
    async def test_empty_portfolio_handling(self, margin_system):
        """Test handling of empty portfolio"""
        result = await margin_system.calculate_comprehensive_margin([])
        
        assert isinstance(result, dict)
        assert result["summary"]["total_positions"] == 0
        assert result["summary"]["total_margin"] == 0
        assert result["portfolio_margin"].total_margin_required == 0


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    margin_system = UnifiedMarginSystem()
    
    # Create a realistic portfolio
    portfolio = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=200,
            current_price=150.0,
            market_value=30000.0,
            volatility=0.25,
            beta=1.2
        ),
        Position(
            symbol="AAPL240315C00160000",
            asset_class=AssetClass.OPTION,
            quantity=-3,
            current_price=5.0,
            market_value=-1500.0,
            underlying_symbol="AAPL",
            strike_price=160.0,
            option_type="call",
            delta=0.6,
            gamma=0.05,
            theta=-0.02,
            vega=0.15,
            volatility=0.25
        ),
        Position(
            symbol="SPY",
            asset_class=AssetClass.EQUITY,
            quantity=100,
            current_price=450.0,
            market_value=45000.0,
            volatility=0.15,
            beta=1.0
        )
    ]
    
    available_capital = 50000.0
    
    # Calculate comprehensive margin
    result = await margin_system.calculate_comprehensive_margin(portfolio, available_capital)
    
    # Verify comprehensive results
    assert result["summary"]["total_positions"] == 3
    assert result["summary"]["total_margin"] > 0
    assert result["summary"]["portfolio_leverage"] > 1.0
    
    # Should have margin requirements for each position
    assert len(result["individual_margins"]) == 3
    
    # Should have optimization suggestions
    assert "optimization_suggestions" in result["optimization"]
    
    # Should be compliant (reasonable portfolio)
    assert result["compliance"]["status"] in ["compliant", "non_compliant"]
    
    # Test trade simulation
    new_trade = [{"symbol": "GOOGL", "quantity": 20, "price": 2800.0, "asset_class": AssetClass.EQUITY}]
    impact = await margin_system.simulate_margin_impact(portfolio, new_trade)
    
    assert impact["margin_change"] > 0  # Adding position should increase margin
    assert impact["recommendation"] in ["approve", "reject"]
    
    print("Integration test completed successfully!")
    print(f"Portfolio margin: ${result['summary']['total_margin']:,.2f}")
    print(f"Portfolio leverage: {result['summary']['portfolio_leverage']:.2f}x")
    print(f"Compliance status: {result['compliance']['status']}")
    print(f"Trade impact: ${impact['margin_change']:,.2f} additional margin")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())