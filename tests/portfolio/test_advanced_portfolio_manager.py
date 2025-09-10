"""Tests for Advanced Portfolio Management System"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from nautilus_trader_engine.portfolio.advanced_portfolio_manager import (
    AdvancedPortfolioManager, AssetClass, RebalancingStrategy, RebalancingFrequency,
    AssetAllocation, PortfolioConstraints, RebalancingConfig, PortfolioMetrics,
    get_advanced_portfolio_manager, initialize_advanced_portfolio_manager
)
from nautilus_trader_engine.risk.portfolio_optimizer import (
    OptimizationResult, OptimizationMethod, ObjectiveFunction
)


class TestAdvancedPortfolioManager:
    """Test cases for Advanced Portfolio Manager"""
    
    @pytest.fixture
    def portfolio_manager(self):
        """Create a portfolio manager instance for testing"""
        return AdvancedPortfolioManager()
    
    @pytest.fixture
    def sample_allocations(self):
        """Create sample asset allocations"""
        return [
            AssetAllocation(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                target_weight=0.3,
                sector="Technology",
                country="US",
                current_price=150.0,
                market_value=30000.0,
                quantity=200
            ),
            AssetAllocation(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                target_weight=0.25,
                sector="Technology",
                country="US",
                current_price=300.0,
                market_value=25000.0,
                quantity=83.33
            ),
            AssetAllocation(
                symbol="TLT",
                asset_class=AssetClass.BOND,
                target_weight=0.2,
                sector="Government Bonds",
                country="US",
                current_price=100.0,
                market_value=20000.0,
                quantity=200
            ),
            AssetAllocation(
                symbol="GLD",
                asset_class=AssetClass.COMMODITY,
                target_weight=0.15,
                sector="Precious Metals",
                country="Global",
                current_price=180.0,
                market_value=15000.0,
                quantity=83.33
            ),
            AssetAllocation(
                symbol="VTI",
                asset_class=AssetClass.EQUITY,
                target_weight=0.1,
                sector="Broad Market",
                country="US",
                current_price=200.0,
                market_value=10000.0,
                quantity=50
            )
        ]
    
    @pytest.fixture
    def sample_constraints(self):
        """Create sample portfolio constraints"""
        return PortfolioConstraints(
            max_single_asset_weight=0.35,
            max_sector_weight=0.60,
            max_country_weight=0.80,
            max_portfolio_volatility=0.18,
            max_portfolio_drawdown=0.12,
            asset_class_limits={
                AssetClass.EQUITY: (0.3, 0.7),
                AssetClass.BOND: (0.1, 0.4),
                AssetClass.COMMODITY: (0.0, 0.2)
            }
        )
    
    @pytest.fixture
    def sample_rebalancing_config(self):
        """Create sample rebalancing configuration"""
        return RebalancingConfig(
            strategy=RebalancingStrategy.THRESHOLD,
            frequency=RebalancingFrequency.MONTHLY,
            drift_threshold=0.05,
            target_volatility=0.12
        )
    
    def test_create_portfolio(self, portfolio_manager, sample_constraints, sample_rebalancing_config):
        """Test portfolio creation"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_001",
            initial_capital=100000.0,
            base_currency="USD",
            constraints=sample_constraints,
            rebalancing_config=sample_rebalancing_config
        )
        
        assert portfolio_id.startswith("ADV_PORT_")
        assert portfolio_id in portfolio_manager.portfolios
        
        portfolio = portfolio_manager.portfolios[portfolio_id]
        assert portfolio['account_id'] == "TEST_ACCOUNT_001"
        assert portfolio['initial_capital'] == 100000.0
        assert portfolio['current_value'] == 100000.0
        assert portfolio['base_currency'] == "USD"
        assert portfolio['status'] == 'active'
        
        # Check constraints and config are set
        assert portfolio_id in portfolio_manager.constraints
        assert portfolio_id in portfolio_manager.rebalancing_configs
    
    def test_set_target_allocation_valid(self, portfolio_manager, sample_allocations):
        """Test setting valid target allocation"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_002",
            initial_capital=100000.0
        )
        
        result = portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        assert result is True
        assert len(portfolio_manager.allocations[portfolio_id]) == 5
        
        # Check total weights sum to 1.0
        total_weight = sum(alloc.target_weight for alloc in portfolio_manager.allocations[portfolio_id])
        assert abs(total_weight - 1.0) < 0.001
    
    def test_set_target_allocation_invalid_weights(self, portfolio_manager, sample_allocations):
        """Test setting invalid target allocation (weights don't sum to 1.0)"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_003",
            initial_capital=100000.0
        )
        
        # Modify weights to not sum to 1.0
        invalid_allocations = sample_allocations.copy()
        invalid_allocations[0].target_weight = 0.5  # This makes total > 1.0
        
        result = portfolio_manager.set_target_allocation(portfolio_id, invalid_allocations)
        
        assert result is False
        assert len(portfolio_manager.allocations[portfolio_id]) == 0
    
    def test_set_target_allocation_constraint_violation(self, portfolio_manager, sample_allocations, sample_constraints):
        """Test setting allocation that violates constraints"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_004",
            initial_capital=100000.0,
            constraints=sample_constraints
        )
        
        # Create allocation that violates max single asset weight
        violating_allocations = sample_allocations.copy()
        violating_allocations[0].target_weight = 0.4  # Exceeds max_single_asset_weight of 0.35
        violating_allocations[1].target_weight = 0.2
        violating_allocations[2].target_weight = 0.15
        violating_allocations[3].target_weight = 0.15
        violating_allocations[4].target_weight = 0.1
        
        result = portfolio_manager.set_target_allocation(portfolio_id, violating_allocations)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_calculate_portfolio_metrics(self, portfolio_manager, sample_allocations):
        """Test portfolio metrics calculation"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_005",
            initial_capital=100000.0
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        # Mock the _update_market_values method
        with patch.object(portfolio_manager, '_update_market_values', new_callable=AsyncMock):
            metrics = await portfolio_manager.calculate_portfolio_metrics(portfolio_id)
        
        assert metrics is not None
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_value == 100000.0
        assert metrics.cash_balance == 100000.0  # No actual investments yet
        assert metrics.invested_value == 0.0
        
        # Check allocation metrics
        assert AssetClass.EQUITY in metrics.asset_class_allocation
        assert AssetClass.BOND in metrics.asset_class_allocation
        assert AssetClass.COMMODITY in metrics.asset_class_allocation
        
        # Check that metrics are stored in history
        assert len(portfolio_manager.performance_history[portfolio_id]) == 1
    
    @pytest.mark.asyncio
    async def test_check_rebalancing_needed_threshold(self, portfolio_manager, sample_allocations, sample_rebalancing_config):
        """Test threshold-based rebalancing check"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_006",
            initial_capital=100000.0,
            rebalancing_config=sample_rebalancing_config
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        # Mock methods
        with patch.object(portfolio_manager, '_update_market_values', new_callable=AsyncMock), \
             patch.object(portfolio_manager, '_calculate_current_weights') as mock_weights:
            
            # Simulate significant drift
            mock_weights.return_value = {
                "AAPL": 0.4,  # Target is 0.3, drift = 0.1 > threshold 0.05
                "MSFT": 0.25,
                "TLT": 0.2,
                "GLD": 0.15,
                "VTI": 0.0  # Target is 0.1, drift = 0.1 > threshold 0.05
            }
            
            needed, analysis = await portfolio_manager.check_rebalancing_needed(portfolio_id)
        
        assert needed is True
        assert len(analysis['reasons']) >= 1
        assert 'current_weights' in analysis
        assert 'target_weights' in analysis
    
    @pytest.mark.asyncio
    async def test_check_rebalancing_needed_periodic(self, portfolio_manager, sample_allocations):
        """Test periodic rebalancing check"""
        periodic_config = RebalancingConfig(
            strategy=RebalancingStrategy.PERIODIC,
            frequency=RebalancingFrequency.MONTHLY
        )
        
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_007",
            initial_capital=100000.0,
            rebalancing_config=periodic_config
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        # Set last rebalanced to 35 days ago (> monthly threshold)
        portfolio_manager.portfolios[portfolio_id]['last_rebalanced'] = datetime.now() - timedelta(days=35)
        
        with patch.object(portfolio_manager, '_update_market_values', new_callable=AsyncMock), \
             patch.object(portfolio_manager, '_calculate_current_weights') as mock_weights:
            
            mock_weights.return_value = {alloc.symbol: alloc.target_weight for alloc in sample_allocations}
            
            needed, analysis = await portfolio_manager.check_rebalancing_needed(portfolio_id)
        
        assert needed is True
        assert any("Periodic rebalancing due" in reason for reason in analysis['reasons'])
    
    @pytest.mark.asyncio
    async def test_execute_rebalancing_success(self, portfolio_manager, sample_allocations, sample_rebalancing_config):
        """Test successful rebalancing execution"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_008",
            initial_capital=100000.0,
            rebalancing_config=sample_rebalancing_config
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        # Mock optimization result
        mock_result = OptimizationResult(
            method=OptimizationMethod.MEAN_VARIANCE,
            objective=ObjectiveFunction.MAXIMIZE_SHARPE,
            weights={"AAPL": 0.3, "MSFT": 0.25, "TLT": 0.2, "GLD": 0.15, "VTI": 0.1},
            expected_return=0.08,
            expected_risk=0.12,
            sharpe_ratio=0.67,
            optimization_time=datetime.now(),
            convergence=True,
            turnover=0.1,
            total_transaction_cost=100.0
        )
        
        with patch.object(portfolio_manager, 'check_rebalancing_needed', new_callable=AsyncMock) as mock_check, \
             patch.object(portfolio_manager, '_prepare_assets_for_optimization', new_callable=AsyncMock), \
             patch.object(portfolio_manager, '_get_optimization_constraints'), \
             patch.object(portfolio_manager.optimization_engine, 'optimize_portfolio', new_callable=AsyncMock) as mock_optimize, \
             patch.object(portfolio_manager, '_generate_rebalancing_orders', new_callable=AsyncMock) as mock_orders:
            
            mock_check.return_value = (True, {'reasons': ['Test rebalancing']})
            mock_optimize.return_value = mock_result
            mock_orders.return_value = [{'symbol': 'AAPL', 'side': 'buy', 'value': 1000}]
            
            result = await portfolio_manager.execute_rebalancing(portfolio_id)
        
        assert result['status'] == 'completed'
        assert 'rebalancing_record' in result
        assert 'orders' in result
        
        # Check that rebalancing history is recorded
        assert len(portfolio_manager.rebalancing_history[portfolio_id]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_rebalancing_not_needed(self, portfolio_manager, sample_allocations, sample_rebalancing_config):
        """Test rebalancing when not needed"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_009",
            initial_capital=100000.0,
            rebalancing_config=sample_rebalancing_config
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        with patch.object(portfolio_manager, 'check_rebalancing_needed', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = (False, {'reasons': []})
            
            result = await portfolio_manager.execute_rebalancing(portfolio_id)
        
        assert result['status'] == 'no_rebalancing_needed'
    
    @pytest.mark.asyncio
    async def test_monitor_risk_limits(self, portfolio_manager, sample_allocations, sample_constraints):
        """Test risk limit monitoring"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_010",
            initial_capital=100000.0,
            constraints=sample_constraints
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        # Mock metrics with violations
        mock_metrics = PortfolioMetrics(
            total_value=100000.0,
            cash_balance=10000.0,
            invested_value=90000.0,
            total_return=0.05,
            annualized_return=0.05,
            volatility=0.25,  # Exceeds max_portfolio_volatility of 0.18
            sharpe_ratio=0.2,
            sortino_ratio=0.24,
            max_drawdown=0.15,  # Exceeds max_portfolio_drawdown of 0.12
            var_95=0.06,  # Exceeds max_var_95 of 0.05
            var_99=0.08,
            expected_shortfall=0.09,
            beta=1.0,
            asset_class_allocation={
                AssetClass.EQUITY: 0.8,  # Exceeds max limit of 0.7
                AssetClass.BOND: 0.15,
                AssetClass.COMMODITY: 0.05
            },
            sector_allocation={"Technology": 0.55},
            country_allocation={"US": 0.85},
            diversification_ratio=0.8,
            effective_assets=4.2,
            concentration_index=0.24,
            turnover=0.1,
            calculation_time=datetime.now()
        )
        
        with patch.object(portfolio_manager, 'calculate_portfolio_metrics', new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = mock_metrics
            
            result = await portfolio_manager.monitor_risk_limits(portfolio_id)
        
        assert len(result['violations']) >= 3  # volatility, drawdown, var, asset_class
        assert any(v['type'] == 'volatility_breach' for v in result['violations'])
        assert any(v['type'] == 'drawdown_breach' for v in result['violations'])
        assert any(v['type'] == 'var_breach' for v in result['violations'])
        assert any(v['type'] == 'asset_class_concentration' for v in result['violations'])
        
        # Check that risk alert is stored
        assert len(portfolio_manager.risk_alerts) == 1
    
    def test_calculate_current_weights(self, portfolio_manager, sample_allocations):
        """Test current weights calculation"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_011",
            initial_capital=100000.0
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        weights = portfolio_manager._calculate_current_weights(portfolio_id)
        
        # Check that weights are calculated correctly
        total_value = sum(alloc.market_value for alloc in sample_allocations)
        expected_weights = {
            alloc.symbol: alloc.market_value / total_value
            for alloc in sample_allocations
        }
        
        for symbol, expected_weight in expected_weights.items():
            assert abs(weights[symbol] - expected_weight) < 0.001
    
    def test_calculate_asset_class_allocation(self, portfolio_manager, sample_allocations):
        """Test asset class allocation calculation"""
        allocation = portfolio_manager._calculate_asset_class_allocation(sample_allocations)
        
        total_value = sum(alloc.market_value for alloc in sample_allocations)
        
        # Check equity allocation (AAPL + MSFT + VTI)
        equity_value = 30000 + 25000 + 10000  # 65000
        expected_equity_allocation = equity_value / total_value
        assert abs(allocation[AssetClass.EQUITY] - expected_equity_allocation) < 0.001
        
        # Check bond allocation (TLT)
        bond_value = 20000
        expected_bond_allocation = bond_value / total_value
        assert abs(allocation[AssetClass.BOND] - expected_bond_allocation) < 0.001
        
        # Check commodity allocation (GLD)
        commodity_value = 15000
        expected_commodity_allocation = commodity_value / total_value
        assert abs(allocation[AssetClass.COMMODITY] - expected_commodity_allocation) < 0.001
    
    def test_calculate_effective_assets(self, portfolio_manager, sample_allocations):
        """Test effective assets calculation"""
        effective_assets = portfolio_manager._calculate_effective_assets(sample_allocations)
        
        # Calculate expected value using inverse Herfindahl index
        weights = [alloc.target_weight for alloc in sample_allocations]
        herfindahl = sum(w**2 for w in weights)
        expected_effective_assets = 1.0 / herfindahl
        
        assert abs(effective_assets - expected_effective_assets) < 0.001
    
    def test_get_portfolio_summary(self, portfolio_manager, sample_allocations, sample_constraints, sample_rebalancing_config):
        """Test portfolio summary generation"""
        portfolio_id = portfolio_manager.create_portfolio(
            account_id="TEST_ACCOUNT_012",
            initial_capital=100000.0,
            constraints=sample_constraints,
            rebalancing_config=sample_rebalancing_config
        )
        
        portfolio_manager.set_target_allocation(portfolio_id, sample_allocations)
        
        summary = portfolio_manager.get_portfolio_summary(portfolio_id)
        
        assert 'portfolio_info' in summary
        assert 'allocations' in summary
        assert 'constraints' in summary
        assert 'rebalancing_config' in summary
        assert 'latest_metrics' in summary
        assert 'rebalancing_history_count' in summary
        assert 'risk_alerts_count' in summary
        
        # Check allocation details
        assert len(summary['allocations']) == 5
        for alloc_summary in summary['allocations']:
            assert 'symbol' in alloc_summary
            assert 'asset_class' in alloc_summary
            assert 'target_weight' in alloc_summary
            assert 'current_weight' in alloc_summary
    
    def test_get_portfolio_summary_nonexistent(self, portfolio_manager):
        """Test portfolio summary for non-existent portfolio"""
        summary = portfolio_manager.get_portfolio_summary("NONEXISTENT")
        assert 'error' in summary
        assert summary['error'] == 'Portfolio not found'


class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_advanced_portfolio_manager(self):
        """Test getting global portfolio manager instance"""
        manager1 = get_advanced_portfolio_manager()
        manager2 = get_advanced_portfolio_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        assert isinstance(manager1, AdvancedPortfolioManager)
    
    @pytest.mark.asyncio
    async def test_initialize_advanced_portfolio_manager(self):
        """Test initializing global portfolio manager"""
        config = {'test_setting': 'test_value'}
        
        with patch.object(AdvancedPortfolioManager, 'initialize', new_callable=AsyncMock) as mock_init:
            manager = await initialize_advanced_portfolio_manager(config)
            
            assert isinstance(manager, AdvancedPortfolioManager)
            assert manager.config == config
            mock_init.assert_called_once()


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_portfolio_lifecycle(self):
        """Test complete portfolio lifecycle"""
        manager = AdvancedPortfolioManager()
        
        # Create portfolio
        portfolio_id = manager.create_portfolio(
            account_id="INTEGRATION_TEST",
            initial_capital=100000.0,
            constraints=PortfolioConstraints(
                max_single_asset_weight=0.4,
                max_portfolio_volatility=0.2
            ),
            rebalancing_config=RebalancingConfig(
                strategy=RebalancingStrategy.THRESHOLD,
                frequency=RebalancingFrequency.MONTHLY,
                drift_threshold=0.05
            )
        )
        
        # Set allocations
        allocations = [
            AssetAllocation(
                symbol="SPY",
                asset_class=AssetClass.EQUITY,
                target_weight=0.6,
                sector="Broad Market",
                country="US",
                current_price=400.0,
                market_value=60000.0,
                quantity=150
            ),
            AssetAllocation(
                symbol="TLT",
                asset_class=AssetClass.BOND,
                target_weight=0.4,
                sector="Government Bonds",
                country="US",
                current_price=100.0,
                market_value=40000.0,
                quantity=400
            )
        ]
        
        success = manager.set_target_allocation(portfolio_id, allocations)
        assert success is True
        
        # Calculate metrics
        with patch.object(manager, '_update_market_values', new_callable=AsyncMock):
            metrics = await manager.calculate_portfolio_metrics(portfolio_id)
        
        assert metrics is not None
        assert metrics.total_value == 100000.0
        
        # Check rebalancing
        with patch.object(manager, '_update_market_values', new_callable=AsyncMock), \
             patch.object(manager, '_calculate_current_weights') as mock_weights:
            
            # Simulate drift
            mock_weights.return_value = {"SPY": 0.7, "TLT": 0.3}  # SPY drifted up
            
            needed, analysis = await manager.check_rebalancing_needed(portfolio_id)
        
        assert needed is True
        
        # Monitor risk
        with patch.object(manager, 'calculate_portfolio_metrics', new_callable=AsyncMock) as mock_calc:
            mock_calc.return_value = metrics
            
            risk_result = await manager.monitor_risk_limits(portfolio_id)
        
        assert 'violations' in risk_result
        assert 'warnings' in risk_result
        
        # Get summary
        summary = manager.get_portfolio_summary(portfolio_id)
        assert summary['portfolio_info']['portfolio_id'] == portfolio_id
        assert len(summary['allocations']) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])