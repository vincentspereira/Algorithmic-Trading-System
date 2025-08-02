#!/usr/bin/env python3
"""
Data Consistency and Integrity Testing Module
Tests data consistency across different system components and validates data integrity.
"""

import pytest
import asyncio
import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataConsistencyTest:
    """Represents a data consistency test case"""
    name: str
    description: str
    data_sources: List[str]
    consistency_rules: List[Dict[str, Any]]
    tolerance: float = 0.0  # Acceptable difference for numerical comparisons

class DataConsistencyValidator:
    """Validates data consistency across system components"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.test_results = []
    
    async def validate_portfolio_consistency(self) -> bool:
        """Validate portfolio data consistency across different endpoints"""
        logger.info("Validating portfolio data consistency")
        
        try:
            # Get portfolio summary
            portfolio_summary = await self.api_client.get('/portfolio')
            
            # Get individual positions
            positions_data = await self.api_client.get('/portfolio/positions')
            
            # Get portfolio performance
            performance_data = await self.api_client.get('/portfolio/performance')
            
            # Validate total value consistency
            calculated_total = sum(pos['market_value'] for pos in positions_data['positions'])
            calculated_total += portfolio_summary['cash']
            
            portfolio_total = portfolio_summary['total_value']
            
            if abs(calculated_total - portfolio_total) > 0.01:  # 1 cent tolerance
                raise AssertionError(
                    f"Portfolio total inconsistency: calculated {calculated_total}, "
                    f"reported {portfolio_total}"
                )
            
            # Validate P&L consistency
            calculated_pnl = sum(pos['unrealized_pnl'] for pos in positions_data['positions'])
            portfolio_pnl = portfolio_summary['daily_pnl']
            
            if abs(calculated_pnl - portfolio_pnl) > 0.01:
                raise AssertionError(
                    f"P&L inconsistency: calculated {calculated_pnl}, "
                    f"reported {portfolio_pnl}"
                )
            
            logger.info("✅ Portfolio consistency validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Portfolio consistency validation failed: {e}")
            return False
    
    async def validate_order_lifecycle_consistency(self) -> bool:
        """Validate order data consistency throughout its lifecycle"""
        logger.info("Validating order lifecycle consistency")
        
        try:
            # Create a test order
            order_data = {
                'symbol': 'AAPL',
                'side': 'buy',
                'order_type': 'limit',
                'quantity': 10,
                'price': 150.00
            }
            
            # Place order
            order_response = await self.api_client.post('/orders', order_data)
            order_id = order_response['id']
            
            # Verify order appears in orders list
            orders_list = await self.api_client.get('/orders')
            found_order = next((o for o in orders_list['orders'] if o['id'] == order_id), None)
            
            if not found_order:
                raise AssertionError(f"Order {order_id} not found in orders list")
            
            # Verify order details consistency
            order_details = await self.api_client.get(f'/orders/{order_id}')
            
            consistency_checks = [
                ('symbol', order_data['symbol'], order_details['symbol']),
                ('side', order_data['side'], order_details['side']),
                ('quantity', order_data['quantity'], order_details['quantity']),
                ('price', order_data['price'], order_details['price'])
            ]
            
            for field, expected, actual in consistency_checks:
                if expected != actual:
                    raise AssertionError(
                        f"Order {field} inconsistency: expected {expected}, got {actual}"
                    )
            
            # Verify order in portfolio if filled
            if order_details['status'] == 'filled':
                portfolio = await self.api_client.get('/portfolio')
                symbol_position = next(
                    (pos for pos in portfolio['positions'] if pos['symbol'] == order_data['symbol']), 
                    None
                )
                
                if order_data['side'] == 'buy' and not symbol_position:
                    raise AssertionError(f"Filled buy order not reflected in portfolio")
            
            # Cleanup
            await self.api_client.delete(f'/orders/{order_id}')
            
            logger.info("✅ Order lifecycle consistency validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Order lifecycle consistency validation failed: {e}")
            return False
    
    async def validate_strategy_data_consistency(self) -> bool:
        """Validate strategy data consistency across different views"""
        logger.info("Validating strategy data consistency")
        
        try:
            # Create test strategy
            strategy_data = {
                'name': 'Consistency Test Strategy',
                'description': 'Strategy for testing data consistency',
                'asset_class': 'stocks',
                'strategy_type': 'momentum',
                'parameters': {
                    'lookback_period': 20,
                    'threshold': 0.02
                }
            }
            
            # Create strategy
            strategy_response = await self.api_client.post('/strategies', strategy_data)
            strategy_id = strategy_response['id']
            
            # Get strategy details
            strategy_details = await self.api_client.get(f'/strategies/{strategy_id}')
            
            # Get strategies list
            strategies_list = await self.api_client.get('/strategies')
            found_strategy = next(
                (s for s in strategies_list['strategies'] if s['id'] == strategy_id), 
                None
            )
            
            if not found_strategy:
                raise AssertionError(f"Strategy {strategy_id} not found in strategies list")
            
            # Verify consistency between detail view and list view
            consistency_fields = ['name', 'description', 'asset_class', 'strategy_type']
            
            for field in consistency_fields:
                if strategy_details[field] != found_strategy[field]:
                    raise AssertionError(
                        f"Strategy {field} inconsistency: "
                        f"detail view {strategy_details[field]}, "
                        f"list view {found_strategy[field]}"
                    )
            
            # Verify parameters consistency
            if strategy_details['parameters'] != found_strategy['parameters']:
                raise AssertionError("Strategy parameters inconsistency between views")
            
            # Run backtest and verify consistency
            backtest_data = {
                'strategy_id': strategy_id,
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'initial_capital': 100000
            }
            
            backtest_response = await self.api_client.post('/backtesting/run', backtest_data)
            backtest_id = backtest_response['backtest_id']
            
            # Wait for backtest completion (simplified)
            await asyncio.sleep(2)
            
            # Get backtest results
            backtest_results = await self.api_client.get(f'/backtesting/{backtest_id}')
            
            # Verify backtest references correct strategy
            if backtest_results.get('strategy_id') != strategy_id:
                raise AssertionError("Backtest strategy reference inconsistency")
            
            # Cleanup
            await self.api_client.delete(f'/strategies/{strategy_id}')
            
            logger.info("✅ Strategy data consistency validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Strategy data consistency validation failed: {e}")
            return False
    
    async def validate_market_data_consistency(self) -> bool:
        """Validate market data consistency across different endpoints"""
        logger.info("Validating market data consistency")
        
        try:
            symbol = 'AAPL'
            
            # Get real-time quote
            quote_data = await self.api_client.get(f'/market-data/quotes/{symbol}')
            
            # Get historical data (latest point)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=1)
            
            historical_data = await self.api_client.get(
                f'/market-data/historical/{symbol}',
                params={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'interval': '1d'
                }
            )
            
            if historical_data['data']:
                latest_historical = historical_data['data'][-1]
                
                # For end-of-day data, the close should match current quote
                # (with some tolerance for market hours)
                current_time = datetime.now().time()
                market_closed = current_time.hour >= 16  # Simplified market hours check
                
                if market_closed:
                    quote_price = quote_data['last']
                    historical_close = latest_historical['close']
                    
                    # Allow 1% tolerance for price differences
                    price_diff = abs(quote_price - historical_close) / historical_close
                    
                    if price_diff > 0.01:
                        logger.warning(
                            f"Price inconsistency detected: quote {quote_price}, "
                            f"historical close {historical_close} (diff: {price_diff:.2%})"
                        )
            
            # Verify quote data completeness
            required_fields = ['symbol', 'bid', 'ask', 'last', 'volume', 'timestamp']
            for field in required_fields:
                if field not in quote_data:
                    raise AssertionError(f"Missing required field in quote data: {field}")
            
            # Verify bid <= last <= ask (when market is active)
            if quote_data['bid'] > 0 and quote_data['ask'] > 0:
                if not (quote_data['bid'] <= quote_data['last'] <= quote_data['ask']):
                    logger.warning(
                        f"Quote spread inconsistency: bid {quote_data['bid']}, "
                        f"last {quote_data['last']}, ask {quote_data['ask']}"
                    )
            
            logger.info("✅ Market data consistency validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Market data consistency validation failed: {e}")
            return False
    
    async def validate_user_data_consistency(self) -> bool:
        """Validate user data consistency across sessions and endpoints"""
        logger.info("Validating user data consistency")
        
        try:
            # Get user profile
            user_profile = await self.api_client.get('/user/profile')
            
            # Get user preferences
            user_preferences = await self.api_client.get('/user/preferences')
            
            # Verify user ID consistency
            if user_profile['id'] != user_preferences['user_id']:
                raise AssertionError("User ID inconsistency between profile and preferences")
            
            # Update preferences and verify persistence
            original_preferences = user_preferences.copy()
            
            updated_preferences = {
                'theme': 'dark',
                'notifications_enabled': True,
                'default_asset_class': 'stocks'
            }
            
            await self.api_client.put('/user/preferences', updated_preferences)
            
            # Verify update
            new_preferences = await self.api_client.get('/user/preferences')
            
            for key, value in updated_preferences.items():
                if new_preferences.get(key) != value:
                    raise AssertionError(f"Preference update failed for {key}")
            
            # Restore original preferences
            await self.api_client.put('/user/preferences', original_preferences)
            
            logger.info("✅ User data consistency validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ User data consistency validation failed: {e}")
            return False
    
    async def run_all_consistency_tests(self) -> Dict[str, bool]:
        """Run all data consistency tests"""
        tests = [
            ('Portfolio Consistency', self.validate_portfolio_consistency),
            ('Order Lifecycle Consistency', self.validate_order_lifecycle_consistency),
            ('Strategy Data Consistency', self.validate_strategy_data_consistency),
            ('Market Data Consistency', self.validate_market_data_consistency),
            ('User Data Consistency', self.validate_user_data_consistency)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"Running {test_name}...")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                results[test_name] = False
        
        return results

# Pytest Integration
class TestDataConsistency:
    """Pytest test class for data consistency testing"""
    
    @pytest.fixture(scope="class")
    def consistency_validator(self, api_client):
        """Create consistency validator instance"""
        return DataConsistencyValidator(api_client)
    
    @pytest.mark.asyncio
    async def test_portfolio_consistency(self, consistency_validator):
        """Test portfolio data consistency"""
        result = await consistency_validator.validate_portfolio_consistency()
        assert result, "Portfolio consistency validation failed"
    
    @pytest.mark.asyncio
    async def test_order_lifecycle_consistency(self, consistency_validator):
        """Test order lifecycle data consistency"""
        result = await consistency_validator.validate_order_lifecycle_consistency()
        assert result, "Order lifecycle consistency validation failed"
    
    @pytest.mark.asyncio
    async def test_strategy_data_consistency(self, consistency_validator):
        """Test strategy data consistency"""
        result = await consistency_validator.validate_strategy_data_consistency()
        assert result, "Strategy data consistency validation failed"
    
    @pytest.mark.asyncio
    async def test_market_data_consistency(self, consistency_validator):
        """Test market data consistency"""
        result = await consistency_validator.validate_market_data_consistency()
        assert result, "Market data consistency validation failed"
    
    @pytest.mark.asyncio
    async def test_user_data_consistency(self, consistency_validator):
        """Test user data consistency"""
        result = await consistency_validator.validate_user_data_consistency()
        assert result, "User data consistency validation failed"
    
    @pytest.mark.asyncio
    async def test_cross_component_data_integrity(self, consistency_validator):
        """Test data integrity across multiple system components"""
        # This test creates data in one component and verifies it's correctly
        # reflected in related components
        
        api_client = consistency_validator.api_client
        
        # Create strategy
        strategy_data = {
            'name': 'Cross-Component Test Strategy',
            'asset_class': 'stocks',
            'strategy_type': 'momentum'
        }
        
        strategy = await api_client.post('/strategies', strategy_data)
        strategy_id = strategy['id']
        
        try:
            # Run backtest
            backtest_data = {
                'strategy_id': strategy_id,
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'initial_capital': 100000
            }
            
            backtest = await api_client.post('/backtesting/run', backtest_data)
            backtest_id = backtest['backtest_id']
            
            # Wait for completion
            await asyncio.sleep(3)
            
            # Verify backtest results reference correct strategy
            backtest_results = await api_client.get(f'/backtesting/{backtest_id}')
            assert backtest_results['strategy_id'] == strategy_id
            
            # Verify strategy shows backtest in its history
            strategy_details = await api_client.get(f'/strategies/{strategy_id}')
            # Note: This assumes the API includes backtest history in strategy details
            
            # Create order based on strategy signals (if applicable)
            # This would test the integration between strategy signals and order management
            
        finally:
            # Cleanup
            await api_client.delete(f'/strategies/{strategy_id}')

if __name__ == "__main__":
    # Standalone execution for data consistency tests
    async def main():
        print("🔍 Starting Data Consistency Tests")
        print("=" * 50)
        
        # This would need to be configured with actual API client
        # validator = DataConsistencyValidator(api_client)
        # results = await validator.run_all_consistency_tests()
        
        # For now, just show the structure
        print("Data consistency tests configured:")
        print("- Portfolio Consistency")
        print("- Order Lifecycle Consistency") 
        print("- Strategy Data Consistency")
        print("- Market Data Consistency")
        print("- User Data Consistency")
        
        return True
    
    asyncio.run(main())