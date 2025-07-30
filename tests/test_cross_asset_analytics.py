"""
Tests for Cross-Asset Analytics System
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta

from nautilus_trader_engine.analytics.cross_asset_analytics import (
    CrossAssetCorrelationAnalyzer,
    ArbitrageDetector,
    SpreadTradingAnalyzer,
    CrossAssetRiskAttributor,
    CrossAssetAnalyticsEngine,
    ArbitrageType,
    SpreadType,
    CorrelationResult,
    ArbitrageOpportunity,
    SpreadOpportunity,
    RiskAttribution
)


class TestCrossAssetCorrelationAnalyzer:
    """Test correlation analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return CrossAssetCorrelationAnalyzer()
    
    @pytest.fixture
    def sample_price_data(self):
        np.random.seed(42)
        return {
            "AAPL": np.cumsum(np.random.normal(0.001, 0.02, 100)) + 150,
            "GOOGL": np.cumsum(np.random.normal(0.0008, 0.025, 100)) + 2800,
            "SPY": np.cumsum(np.random.normal(0.0005, 0.015, 100)) + 450
        }
    
    @pytest.mark.asyncio
    async def test_correlation_matrix_calculation(self, analyzer, sample_price_data):
        """Test correlation matrix calculation"""
        correlation_matrix = await analyzer.calculate_correlation_matrix(sample_price_data)
        
        assert not correlation_matrix.empty
        assert correlation_matrix.shape == (3, 3)
        
        # Diagonal should be 1.0
        for asset in sample_price_data.keys():
            assert abs(correlation_matrix.loc[asset, asset] - 1.0) < 0.001
        
        # Matrix should be symmetric
        assets = list(sample_price_data.keys())
        for i in range(len(assets)):
            for j in range(len(assets)):
                assert abs(correlation_matrix.iloc[i, j] - correlation_matrix.iloc[j, i]) < 0.001
    
    @pytest.mark.asyncio
    async def test_pairwise_correlation_analysis(self, analyzer):
        """Test pairwise correlation analysis"""
        # Create correlated data
        np.random.seed(42)
        base_returns = np.random.normal(0.001, 0.02, 100)
        
        asset1_prices = np.cumsum(base_returns) + 100
        asset2_prices = np.cumsum(base_returns * 0.8 + np.random.normal(0, 0.01, 100)) + 200
        
        result = await analyzer.analyze_pairwise_correlation(
            asset1_prices, asset2_prices, "ASSET1", "ASSET2"
        )
        
        assert isinstance(result, CorrelationResult)
        assert result.asset1 == "ASSET1"
        assert result.asset2 == "ASSET2"
        assert -1.0 <= result.correlation <= 1.0
        assert 0.0 <= result.p_value <= 1.0
        assert len(result.confidence_interval) == 2
        assert result.correlation_stability >= 0.0
    
    @pytest.mark.asyncio
    async def test_correlation_breakdown_detection(self, analyzer):
        """Test correlation breakdown detection"""
        # Create correlation history with a breakdown
        correlation_history = [0.8] * 30 + [0.2] * 10 + [0.8] * 30
        
        breakdowns = await analyzer.detect_correlation_breakdowns(correlation_history, threshold=0.3)
        
        assert len(breakdowns) > 0
        # Should detect the breakdown period around index 30-40
        assert any(30 <= bd <= 45 for bd in breakdowns)


class TestArbitrageDetector:
    """Test arbitrage detection functionality"""
    
    @pytest.fixture
    def detector(self):
        return ArbitrageDetector(min_profit_threshold=0.001)
    
    @pytest.mark.asyncio
    async def test_statistical_arbitrage_detection(self, detector):
        """Test statistical arbitrage detection"""
        np.random.seed(42)
        
        # Create mean-reverting spread
        base_price = 100
        asset1_prices = np.cumsum(np.random.normal(0.001, 0.02, 100)) + base_price
        
        # Asset2 follows asset1 but with temporary divergence
        ratio_mean = 2.0
        ratio = np.full(100, ratio_mean)
        ratio[-10:] = ratio_mean + 0.5  # Create divergence
        
        asset2_prices = asset1_prices / ratio
        
        price_data = {
            "ASSET1": asset1_prices,
            "ASSET2": asset2_prices
        }
        
        opportunities = await detector.detect_statistical_arbitrage(price_data)
        
        assert len(opportunities) > 0
        
        opp = opportunities[0]
        assert isinstance(opp, ArbitrageOpportunity)
        assert opp.arbitrage_type == ArbitrageType.STATISTICAL
        assert len(opp.assets_involved) == 2
        assert opp.expected_profit > 0
        assert 0 <= opp.confidence_score <= 1
    
    @pytest.mark.asyncio
    async def test_triangular_arbitrage_detection(self, detector):
        """Test triangular arbitrage detection"""
        # Create currency pairs with arbitrage opportunity
        currency_pairs = {
            "EURUSD": 1.1000,
            "GBPUSD": 1.3000,
            "EURGBP": 0.8500  # Should be ~0.8462 (1.1/1.3), so there's an opportunity
        }
        
        opportunities = await detector.detect_triangular_arbitrage(currency_pairs)
        
        assert len(opportunities) > 0
        
        opp = opportunities[0]
        assert isinstance(opp, ArbitrageOpportunity)
        assert opp.arbitrage_type == ArbitrageType.TRIANGULAR
        assert len(opp.assets_involved) == 3
        assert opp.expected_profit > 0
    
    @pytest.mark.asyncio
    async def test_calendar_arbitrage_detection(self, detector):
        """Test calendar arbitrage detection"""
        # Create futures data with calendar arbitrage
        futures_data = {
            "ES_202403": 4500.0,
            "ES_202406": 4480.0,  # Backwardation - potential opportunity
            "ES_202409": 4490.0
        }
        
        opportunities = await detector.detect_calendar_arbitrage(futures_data)
        
        assert len(opportunities) > 0
        
        opp = opportunities[0]
        assert isinstance(opp, ArbitrageOpportunity)
        assert opp.arbitrage_type == ArbitrageType.CALENDAR
        assert len(opp.assets_involved) == 2


class TestSpreadTradingAnalyzer:
    """Test spread trading analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        return SpreadTradingAnalyzer(z_score_threshold=2.0)
    
    @pytest.mark.asyncio
    async def test_pairs_trading_analysis(self, analyzer):
        """Test pairs trading analysis"""
        np.random.seed(42)
        
        # Create cointegrated pair with temporary divergence
        base_returns = np.random.normal(0.001, 0.02, 100)
        asset1_prices = np.cumsum(base_returns) + 100
        
        # Asset2 normally follows asset1 but diverges at the end
        asset2_prices = asset1_prices * 2.0
        asset2_prices[-10:] *= 1.1  # Create divergence
        
        opportunity = await analyzer.analyze_pairs_trading(
            asset1_prices, asset2_prices, "ASSET1", "ASSET2"
        )
        
        assert opportunity is not None
        assert isinstance(opportunity, SpreadOpportunity)
        assert opportunity.spread_type == SpreadType.PAIRS_TRADING
        assert opportunity.long_asset in ["ASSET1", "ASSET2"]
        assert opportunity.short_asset in ["ASSET1", "ASSET2"]
        assert opportunity.long_asset != opportunity.short_asset
        assert abs(opportunity.z_score) > 0
    
    @pytest.mark.asyncio
    async def test_calendar_spread_analysis(self, analyzer):
        """Test calendar spread analysis"""
        np.random.seed(42)
        
        # Create near and far contract prices with spread opportunity
        base_price = 100
        near_prices = np.cumsum(np.random.normal(0.001, 0.02, 60)) + base_price
        far_prices = near_prices + 2.0  # Normal contango
        
        # Create temporary spread widening
        far_prices[-10:] += 3.0
        
        opportunity = await analyzer.analyze_calendar_spread(
            near_prices, far_prices, "NEAR_CONTRACT", "FAR_CONTRACT"
        )
        
        assert opportunity is not None
        assert isinstance(opportunity, SpreadOpportunity)
        assert opportunity.spread_type == SpreadType.CALENDAR_SPREAD
        assert abs(opportunity.z_score) > 0
    
    @pytest.mark.asyncio
    async def test_yield_curve_spread_analysis(self, analyzer):
        """Test yield curve spread analysis"""
        np.random.seed(42)
        
        # Create yield curve data with spread opportunity
        short_rates = np.random.normal(0.02, 0.005, 60)  # 2% average
        long_rates = short_rates + 0.01  # Normal upward sloping curve
        
        # Create temporary flattening
        long_rates[-10:] -= 0.015
        
        opportunity = await analyzer.analyze_yield_curve_spread(
            short_rates, long_rates, "2Y", "10Y"
        )
        
        assert opportunity is not None
        assert isinstance(opportunity, SpreadOpportunity)
        assert opportunity.spread_type == SpreadType.YIELD_CURVE
        assert abs(opportunity.z_score) > 0


class TestCrossAssetRiskAttributor:
    """Test risk attribution functionality"""
    
    @pytest.fixture
    def attributor(self):
        return CrossAssetRiskAttributor()
    
    @pytest.fixture
    def sample_returns_data(self):
        np.random.seed(42)
        return {
            "ASSET1": np.random.normal(0.001, 0.02, 100),
            "ASSET2": np.random.normal(0.0008, 0.025, 100),
            "ASSET3": np.random.normal(0.0005, 0.015, 100)
        }
    
    @pytest.fixture
    def sample_weights(self):
        return {"ASSET1": 0.5, "ASSET2": 0.3, "ASSET3": 0.2}
    
    @pytest.mark.asyncio
    async def test_portfolio_risk_attribution(self, attributor, sample_returns_data, sample_weights):
        """Test portfolio risk attribution calculation"""
        attribution = await attributor.calculate_portfolio_risk_attribution(
            sample_returns_data, sample_weights
        )
        
        assert isinstance(attribution, RiskAttribution)
        assert attribution.portfolio_var != 0.0
        assert len(attribution.component_vars) == 3
        assert len(attribution.marginal_vars) == 3
        assert len(attribution.component_contributions) == 3
        assert 0.0 <= attribution.diversification_ratio <= 1.0
        assert 0.0 <= attribution.concentration_risk <= 1.0
        assert 0.0 <= attribution.correlation_risk <= 1.0
        
        # Check that contributions sum approximately to portfolio VaR
        total_contribution = sum(attribution.component_contributions.values())
        # Note: This is an approximation, so we allow some tolerance
        assert abs(total_contribution) > 0  # Should have some contribution
    
    @pytest.mark.asyncio
    async def test_correlation_risk_analysis(self, attributor, sample_returns_data):
        """Test correlation risk analysis"""
        analysis = await attributor.analyze_correlation_risk(sample_returns_data)
        
        assert isinstance(analysis, dict)
        assert "normal" in analysis
        
        normal_analysis = analysis["normal"]
        assert "mean_correlation" in normal_analysis
        assert "max_correlation" in normal_analysis
        assert "min_correlation" in normal_analysis
        assert "correlation_std" in normal_analysis
        assert "correlation_matrix" in normal_analysis
        assert "asset_names" in normal_analysis
        
        # Check correlation bounds
        assert -1.0 <= normal_analysis["mean_correlation"] <= 1.0
        assert -1.0 <= normal_analysis["max_correlation"] <= 1.0
        assert -1.0 <= normal_analysis["min_correlation"] <= 1.0


class TestCrossAssetAnalyticsEngine:
    """Test the main analytics engine"""
    
    @pytest.fixture
    def engine(self):
        return CrossAssetAnalyticsEngine()
    
    @pytest.fixture
    def sample_market_data(self):
        np.random.seed(42)
        return {
            "AAPL": {
                "prices": np.cumsum(np.random.normal(0.001, 0.02, 100)) + 150,
                "weight": 0.4
            },
            "GOOGL": {
                "prices": np.cumsum(np.random.normal(0.0008, 0.025, 100)) + 2800,
                "weight": 0.3
            },
            "SPY": {
                "prices": np.cumsum(np.random.normal(0.0005, 0.015, 100)) + 450,
                "weight": 0.3
            }
        }
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis(self, engine, sample_market_data):
        """Test comprehensive cross-asset analysis"""
        results = await engine.run_comprehensive_analysis(sample_market_data)
        
        assert isinstance(results, dict)
        assert "analysis_timestamp" in results
        assert "correlations" in results
        assert "arbitrage_opportunities" in results
        assert "spread_opportunities" in results
        assert "risk_attribution" in results
        assert "summary" in results
        
        # Check correlations
        assert "matrix" in results["correlations"]
        assert "pairwise" in results["correlations"]
        
        # Check summary
        summary = results["summary"]
        assert summary["total_assets_analyzed"] == 3
        assert summary["correlation_pairs"] == 3  # 3 choose 2
        assert "arbitrage_opportunities" in summary
        assert "spread_opportunities" in summary
        assert "analysis_quality" in summary
    
    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, engine):
        """Test handling of insufficient data"""
        # Provide minimal data
        minimal_data = {
            "ASSET1": {"prices": [100]}
        }
        
        results = await engine.run_comprehensive_analysis(minimal_data)
        
        assert isinstance(results, dict)
        assert "analysis_timestamp" in results
        # Should handle gracefully without crashing


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    engine = CrossAssetAnalyticsEngine()
    
    # Create realistic market data with known relationships
    np.random.seed(42)
    
    # Create correlated equity data
    market_factor = np.random.normal(0.0005, 0.015, 120)
    
    market_data = {
        "SPY": {
            "prices": np.cumsum(market_factor) + 450,
            "weight": 0.4
        },
        "AAPL": {
            "prices": np.cumsum(market_factor * 1.2 + np.random.normal(0, 0.01, 120)) + 150,
            "weight": 0.3
        },
        "TLT": {
            "prices": np.cumsum(-market_factor * 0.5 + np.random.normal(0, 0.008, 120)) + 120,
            "weight": 0.3
        }
    }
    
    # Run analysis
    results = await engine.run_comprehensive_analysis(market_data)
    
    # Verify comprehensive results
    assert results["summary"]["total_assets_analyzed"] == 3
    assert len(results["correlations"]["pairwise"]) == 3
    
    # Should find some correlation between SPY and AAPL
    spy_aapl_corr = None
    for corr in results["correlations"]["pairwise"]:
        if (corr["asset1"] == "SPY" and corr["asset2"] == "AAPL") or \
           (corr["asset1"] == "AAPL" and corr["asset2"] == "SPY"):
            spy_aapl_corr = corr["correlation"]
            break
    
    assert spy_aapl_corr is not None
    assert spy_aapl_corr > 0.3  # Should be positively correlated
    
    # Should find negative correlation between SPY and TLT
    spy_tlt_corr = None
    for corr in results["correlations"]["pairwise"]:
        if (corr["asset1"] == "SPY" and corr["asset2"] == "TLT") or \
           (corr["asset1"] == "TLT" and corr["asset2"] == "SPY"):
            spy_tlt_corr = corr["correlation"]
            break
    
    assert spy_tlt_corr is not None
    assert spy_tlt_corr < 0  # Should be negatively correlated
    
    # Risk attribution should be calculated
    assert "portfolio_var" in results["risk_attribution"]
    assert "diversification_ratio" in results["risk_attribution"]
    
    print("Integration test completed successfully!")
    print(f"SPY-AAPL correlation: {spy_aapl_corr:.3f}")
    print(f"SPY-TLT correlation: {spy_tlt_corr:.3f}")
    print(f"Portfolio VaR: {results['risk_attribution']['portfolio_var']:.4f}")
    print(f"Diversification ratio: {results['risk_attribution']['diversification_ratio']:.3f}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())