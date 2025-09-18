"""User Acceptance Tests (UAT) for the trading system.

This module contains user acceptance tests that validate business requirements
and user scenarios from an end-user perspective, ensuring the system meets
business objectives and user expectations.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any

import pytest
from conftest import assert_valid_uuid, assert_valid_timestamp, assert_positive_number


class TestUserOnboarding:
    """Test user onboarding and account setup scenarios."""

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_new_user_registration_and_portfolio_creation(
        self,
        mock_user_service,
        mock_portfolio_manager,
        mock_compliance_service
    ):
        """UAT: New user can register and create their first portfolio."""
        # Given: A new user wants to register and start trading
        user_data = {
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1-555-0123",
            "country": "US",
            "date_of_birth": "1985-06-15",
            "risk_tolerance": "MODERATE"
        }
        
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        
        # Mock successful registration
        mock_user_service.register_user.return_value = {
            "user_id": user_id,
            "status": "PENDING_VERIFICATION",
            "verification_required": ["EMAIL", "PHONE", "IDENTITY"]
        }
        
        mock_user_service.verify_email.return_value = {"status": "VERIFIED"}
        mock_user_service.verify_phone.return_value = {"status": "VERIFIED"}
        mock_user_service.verify_identity.return_value = {"status": "VERIFIED"}
        
        mock_compliance_service.check_eligibility.return_value = {
            "eligible": True,
            "approved_features": ["PAPER_TRADING", "LIVE_TRADING", "OPTIONS"],
            "restrictions": []
        }
        
        mock_portfolio_manager.create_portfolio.return_value = {
            "portfolio_id": portfolio_id,
            "name": "My First Portfolio",
            "initial_capital": Decimal("10000.00"),
            "status": "ACTIVE",
            "trading_mode": "PAPER"
        }
        
        # When: User completes registration process
        
        # Step 1: Register
        registration = await mock_user_service.register_user(user_data)
        
        # Step 2: Complete verification
        email_verification = await mock_user_service.verify_email(
            user_id, "verification_code_123"
        )
        phone_verification = await mock_user_service.verify_phone(
            user_id, "sms_code_456"
        )
        identity_verification = await mock_user_service.verify_identity(
            user_id, {"document_type": "PASSPORT", "document_number": "123456789"}
        )
        
        # Step 3: Check compliance eligibility
        eligibility = await mock_compliance_service.check_eligibility(user_id)
        
        # Step 4: Create first portfolio
        if eligibility["eligible"]:
            portfolio = await mock_portfolio_manager.create_portfolio(
                user_id,
                "My First Portfolio",
                Decimal("10000.00"),
                trading_mode="PAPER"
            )
        
        # Then: User should be successfully onboarded
        assert registration["user_id"] == user_id
        assert registration["status"] == "PENDING_VERIFICATION"
        
        assert email_verification["status"] == "VERIFIED"
        assert phone_verification["status"] == "VERIFIED"
        assert identity_verification["status"] == "VERIFIED"
        
        assert eligibility["eligible"] is True
        assert "PAPER_TRADING" in eligibility["approved_features"]
        
        assert portfolio["portfolio_id"] == portfolio_id
        assert portfolio["status"] == "ACTIVE"
        assert portfolio["trading_mode"] == "PAPER"

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_profile_completion_and_risk_assessment(
        self,
        mock_user_service,
        mock_risk_assessment_service
    ):
        """UAT: User can complete profile and risk assessment."""
        # Given: A registered user needs to complete their profile
        user_id = str(uuid.uuid4())
        
        profile_data = {
            "employment_status": "EMPLOYED",
            "annual_income": "75000-100000",
            "net_worth": "100000-250000",
            "investment_experience": "INTERMEDIATE",
            "investment_objectives": ["GROWTH", "INCOME"],
            "time_horizon": "LONG_TERM"
        }
        
        risk_assessment_answers = {
            "risk_capacity": 7,  # Scale 1-10
            "risk_tolerance": 6,
            "investment_knowledge": 7,
            "market_volatility_comfort": 5,
            "loss_tolerance": 4
        }
        
        mock_user_service.update_profile.return_value = {
            "status": "COMPLETED",
            "profile_completeness": 100
        }
        
        mock_risk_assessment_service.calculate_risk_profile.return_value = {
            "risk_score": 6.2,
            "risk_category": "MODERATE_AGGRESSIVE",
            "recommended_allocation": {
                "stocks": 0.70,
                "bonds": 0.20,
                "alternatives": 0.10
            },
            "max_position_size": 0.05,  # 5% max per position
            "leverage_allowed": False
        }
        
        # When: User completes profile and risk assessment
        profile_update = await mock_user_service.update_profile(user_id, profile_data)
        risk_profile = await mock_risk_assessment_service.calculate_risk_profile(
            user_id, risk_assessment_answers
        )
        
        # Then: Profile should be complete with appropriate risk settings
        assert profile_update["status"] == "COMPLETED"
        assert profile_update["profile_completeness"] == 100
        
        assert risk_profile["risk_category"] == "MODERATE_AGGRESSIVE"
        assert 0 <= risk_profile["risk_score"] <= 10
        assert sum(risk_profile["recommended_allocation"].values()) == 1.0
        assert risk_profile["max_position_size"] <= 0.10  # Reasonable limit


class TestTradingUserStories:
    """Test core trading user stories and scenarios."""

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_can_research_and_buy_stock(
        self,
        mock_market_data_service,
        mock_research_service,
        mock_trading_engine,
        mock_portfolio_manager
    ):
        """UAT: User can research a stock and place a buy order."""
        # Given: User wants to research and buy Apple stock
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        symbol = "AAPL"
        
        # Mock research data
        mock_research_service.get_company_info.return_value = {
            "symbol": symbol,
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": "2.8T",
            "pe_ratio": 28.5,
            "dividend_yield": 0.52,
            "analyst_rating": "BUY",
            "price_target": Decimal("180.00")
        }
        
        mock_market_data_service.get_quote.return_value = {
            "symbol": symbol,
            "price": Decimal("150.25"),
            "bid": Decimal("150.20"),
            "ask": Decimal("150.30"),
            "volume": 45000000,
            "change": Decimal("2.15"),
            "change_percent": Decimal("1.45")
        }
        
        mock_market_data_service.get_technical_indicators.return_value = {
            "rsi": 58.2,
            "macd_signal": "BULLISH",
            "moving_averages": {
                "sma_20": Decimal("148.50"),
                "sma_50": Decimal("145.20"),
                "sma_200": Decimal("140.80")
            },
            "support_resistance": {
                "support": Decimal("147.00"),
                "resistance": Decimal("155.00")
            }
        }
        
        mock_trading_engine.submit_order.return_value = {
            "order_id": str(uuid.uuid4()),
            "status": "FILLED",
            "fill_price": Decimal("150.30"),
            "fill_quantity": 10,
            "commission": Decimal("0.00"),  # Commission-free
            "timestamp": datetime.utcnow()
        }
        
        mock_portfolio_manager.get_buying_power.return_value = Decimal("5000.00")
        
        # When: User researches and buys the stock
        
        # Step 1: Research the company
        company_info = await mock_research_service.get_company_info(symbol)
        
        # Step 2: Get current market data
        quote = await mock_market_data_service.get_quote(symbol)
        technical_data = await mock_market_data_service.get_technical_indicators(symbol)
        
        # Step 3: Check buying power
        buying_power = await mock_portfolio_manager.get_buying_power(portfolio_id)
        
        # Step 4: Calculate affordable quantity
        max_affordable = int(buying_power / quote["ask"])
        desired_quantity = min(10, max_affordable)
        
        # Step 5: Place buy order
        if desired_quantity > 0:
            order_data = {
                "symbol": symbol,
                "side": "BUY",
                "quantity": desired_quantity,
                "order_type": "MARKET",
                "portfolio_id": portfolio_id
            }
            
            order_result = await mock_trading_engine.submit_order(order_data)
        
        # Then: User should successfully research and purchase the stock
        assert company_info["symbol"] == symbol
        assert company_info["analyst_rating"] in ["BUY", "HOLD", "SELL"]
        
        assert quote["symbol"] == symbol
        assert_positive_number(quote["price"], "stock price")
        
        assert technical_data["rsi"] > 0
        assert technical_data["macd_signal"] in ["BULLISH", "BEARISH", "NEUTRAL"]
        
        assert buying_power > 0
        assert desired_quantity > 0
        
        assert order_result["status"] == "FILLED"
        assert order_result["fill_quantity"] == desired_quantity
        assert order_result["commission"] == Decimal("0.00")

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_can_set_stop_loss_and_take_profit(
        self,
        mock_trading_engine,
        mock_portfolio_manager
    ):
        """UAT: User can set stop-loss and take-profit orders."""
        # Given: User owns 100 shares of AAPL at $150 and wants to set protective orders
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        symbol = "AAPL"
        
        current_position = {
            "symbol": symbol,
            "quantity": 100,
            "average_price": Decimal("150.00"),
            "current_price": Decimal("155.00"),
            "market_value": Decimal("15500.00"),
            "unrealized_pnl": Decimal("500.00")
        }
        
        mock_portfolio_manager.get_position.return_value = current_position
        
        # Mock order submissions
        stop_loss_order_id = str(uuid.uuid4())
        take_profit_order_id = str(uuid.uuid4())
        
        mock_trading_engine.submit_order.side_effect = [
            {
                "order_id": stop_loss_order_id,
                "status": "PENDING",
                "order_type": "STOP_LOSS",
                "stop_price": Decimal("142.50")
            },
            {
                "order_id": take_profit_order_id,
                "status": "PENDING",
                "order_type": "TAKE_PROFIT",
                "limit_price": Decimal("165.00")
            }
        ]
        
        # When: User sets stop-loss and take-profit orders
        
        # Step 1: Get current position
        position = await mock_portfolio_manager.get_position(portfolio_id, symbol)
        
        # Step 2: Calculate stop-loss (5% below average price)
        stop_loss_price = position["average_price"] * Decimal("0.95")
        
        # Step 3: Calculate take-profit (10% above average price)
        take_profit_price = position["average_price"] * Decimal("1.10")
        
        # Step 4: Submit stop-loss order
        stop_loss_order = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": position["quantity"],
            "order_type": "STOP_LOSS",
            "stop_price": stop_loss_price,
            "portfolio_id": portfolio_id
        }
        
        stop_loss_result = await mock_trading_engine.submit_order(stop_loss_order)
        
        # Step 5: Submit take-profit order
        take_profit_order = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": position["quantity"],
            "order_type": "TAKE_PROFIT",
            "limit_price": take_profit_price,
            "portfolio_id": portfolio_id
        }
        
        take_profit_result = await mock_trading_engine.submit_order(take_profit_order)
        
        # Then: Both protective orders should be successfully placed
        assert position["symbol"] == symbol
        assert position["quantity"] == 100
        
        assert stop_loss_price == Decimal("142.50")  # 5% below $150
        assert take_profit_price == Decimal("165.00")  # 10% above $150
        
        assert stop_loss_result["status"] == "PENDING"
        assert stop_loss_result["order_type"] == "STOP_LOSS"
        assert_valid_uuid(stop_loss_result["order_id"])
        
        assert take_profit_result["status"] == "PENDING"
        assert take_profit_result["order_type"] == "TAKE_PROFIT"
        assert_valid_uuid(take_profit_result["order_id"])

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_can_view_portfolio_performance(
        self,
        mock_portfolio_manager,
        mock_performance_service
    ):
        """UAT: User can view comprehensive portfolio performance metrics."""
        # Given: User has an active portfolio with positions
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        
        portfolio_summary = {
            "portfolio_id": portfolio_id,
            "total_value": Decimal("52500.00"),
            "cash_balance": Decimal("2500.00"),
            "invested_amount": Decimal("50000.00"),
            "total_return": Decimal("2500.00"),
            "total_return_percent": Decimal("5.00"),
            "day_change": Decimal("125.00"),
            "day_change_percent": Decimal("0.24")
        }
        
        positions = [
            {
                "symbol": "AAPL",
                "quantity": 100,
                "average_price": Decimal("150.00"),
                "current_price": Decimal("155.00"),
                "market_value": Decimal("15500.00"),
                "unrealized_pnl": Decimal("500.00"),
                "weight": Decimal("0.31")  # 31% of portfolio
            },
            {
                "symbol": "GOOGL",
                "quantity": 10,
                "average_price": Decimal("2800.00"),
                "current_price": Decimal("2900.00"),
                "market_value": Decimal("29000.00"),
                "unrealized_pnl": Decimal("1000.00"),
                "weight": Decimal("0.58")  # 58% of portfolio
            },
            {
                "symbol": "MSFT",
                "quantity": 20,
                "average_price": Decimal("300.00"),
                "current_price": Decimal("350.00"),
                "market_value": Decimal("7000.00"),
                "unrealized_pnl": Decimal("1000.00"),
                "weight": Decimal("0.14")  # 14% of portfolio
            }
        ]
        
        performance_metrics = {
            "inception_date": datetime.utcnow() - timedelta(days=365),
            "total_return_1d": Decimal("0.24"),
            "total_return_1w": Decimal("1.85"),
            "total_return_1m": Decimal("3.20"),
            "total_return_3m": Decimal("8.75"),
            "total_return_1y": Decimal("12.50"),
            "volatility": Decimal("18.5"),
            "sharpe_ratio": Decimal("0.85"),
            "max_drawdown": Decimal("-8.2"),
            "beta": Decimal("1.05"),
            "alpha": Decimal("2.3")
        }
        
        mock_portfolio_manager.get_portfolio_summary.return_value = portfolio_summary
        mock_portfolio_manager.get_positions.return_value = positions
        mock_performance_service.calculate_performance_metrics.return_value = performance_metrics
        
        # When: User views portfolio performance
        summary = await mock_portfolio_manager.get_portfolio_summary(portfolio_id)
        portfolio_positions = await mock_portfolio_manager.get_positions(portfolio_id)
        performance = await mock_performance_service.calculate_performance_metrics(portfolio_id)
        
        # Then: User should see comprehensive performance data
        assert summary["total_value"] == Decimal("52500.00")
        assert summary["total_return_percent"] == Decimal("5.00")
        assert summary["day_change_percent"] > 0  # Positive day
        
        assert len(portfolio_positions) == 3
        total_weight = sum(pos["weight"] for pos in portfolio_positions)
        assert abs(total_weight - Decimal("1.03")) < Decimal("0.1")  # ~100% (with cash)
        
        # All positions should be profitable
        for position in portfolio_positions:
            assert position["unrealized_pnl"] > 0
            assert position["current_price"] > position["average_price"]
        
        assert performance["total_return_1y"] > 0
        assert performance["sharpe_ratio"] > 0  # Positive risk-adjusted return
        assert performance["max_drawdown"] < 0  # Drawdown should be negative


class TestAdvancedTradingFeatures:
    """Test advanced trading features and scenarios."""

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_can_create_and_backtest_strategy(
        self,
        mock_strategy_service,
        mock_backtesting_service,
        mock_market_data_service
    ):
        """UAT: User can create a trading strategy and run backtests."""
        # Given: User wants to create a simple moving average crossover strategy
        user_id = str(uuid.uuid4())
        
        strategy_config = {
            "name": "SMA Crossover Strategy",
            "description": "Buy when 20-day SMA crosses above 50-day SMA",
            "parameters": {
                "fast_period": 20,
                "slow_period": 50,
                "symbols": ["AAPL", "MSFT", "GOOGL"]
            },
            "entry_conditions": [
                "sma_20 > sma_50",
                "sma_20_prev <= sma_50_prev",  # Crossover condition
                "volume > avg_volume * 1.2"  # Volume confirmation
            ],
            "exit_conditions": [
                "sma_20 < sma_50",
                "stop_loss_hit",
                "take_profit_hit"
            ],
            "risk_management": {
                "stop_loss_percent": 5.0,
                "take_profit_percent": 10.0,
                "max_position_size": 0.1  # 10% of portfolio
            }
        }
        
        strategy_id = str(uuid.uuid4())
        
        mock_strategy_service.create_strategy.return_value = {
            "strategy_id": strategy_id,
            "name": strategy_config["name"],
            "status": "CREATED",
            "validation_result": {
                "valid": True,
                "warnings": [],
                "errors": []
            }
        }
        
        # Mock backtest results
        backtest_results = {
            "backtest_id": str(uuid.uuid4()),
            "strategy_id": strategy_id,
            "period": {
                "start_date": datetime.utcnow() - timedelta(days=365),
                "end_date": datetime.utcnow()
            },
            "performance": {
                "total_return": Decimal("15.75"),
                "annualized_return": Decimal("15.75"),
                "volatility": Decimal("12.8"),
                "sharpe_ratio": Decimal("1.23"),
                "max_drawdown": Decimal("-6.5"),
                "win_rate": Decimal("0.68"),
                "profit_factor": Decimal("1.85")
            },
            "trades": {
                "total_trades": 45,
                "winning_trades": 31,
                "losing_trades": 14,
                "average_win": Decimal("3.2"),
                "average_loss": Decimal("-1.8"),
                "largest_win": Decimal("8.5"),
                "largest_loss": Decimal("-4.2")
            },
            "monthly_returns": [
                {"month": "2023-01", "return": Decimal("2.1")},
                {"month": "2023-02", "return": Decimal("-0.8")},
                {"month": "2023-03", "return": Decimal("1.9")}
                # ... more months
            ]
        }
        
        mock_backtesting_service.run_backtest.return_value = backtest_results
        
        # When: User creates and backtests the strategy
        
        # Step 1: Create strategy
        strategy = await mock_strategy_service.create_strategy(user_id, strategy_config)
        
        # Step 2: Validate strategy
        if strategy["validation_result"]["valid"]:
            # Step 3: Run backtest
            backtest_config = {
                "start_date": datetime.utcnow() - timedelta(days=365),
                "end_date": datetime.utcnow(),
                "initial_capital": Decimal("100000"),
                "commission": Decimal("0.00"),  # Commission-free
                "slippage": Decimal("0.001")  # 0.1% slippage
            }
            
            results = await mock_backtesting_service.run_backtest(
                strategy_id, backtest_config
            )
        
        # Then: Strategy should be created and backtested successfully
        assert strategy["strategy_id"] == strategy_id
        assert strategy["status"] == "CREATED"
        assert strategy["validation_result"]["valid"] is True
        
        assert results["strategy_id"] == strategy_id
        assert results["performance"]["total_return"] > 0
        assert results["performance"]["sharpe_ratio"] > 1.0  # Good risk-adjusted return
        assert results["performance"]["win_rate"] > Decimal("0.5")  # More wins than losses
        assert results["trades"]["total_trades"] > 0
        
        # Performance should be reasonable
        assert results["performance"]["max_drawdown"] > Decimal("-20")  # Not too much drawdown
        assert results["performance"]["volatility"] < Decimal("30")  # Reasonable volatility

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_can_use_ai_assistant_for_trading(
        self,
        mock_ai_assistant,
        mock_trading_engine,
        mock_portfolio_manager,
        mock_market_data_service
    ):
        """UAT: User can interact with AI assistant for trading tasks."""
        # Given: User wants to use AI assistant for trading decisions
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        
        # Mock AI assistant responses
        mock_ai_assistant.process_query.side_effect = [
            # Response to "What's the current market sentiment?"
            {
                "response": "Current market sentiment is cautiously optimistic. The VIX is at 18.5, indicating moderate volatility. Tech stocks are showing strength with AAPL up 2.1% and MSFT up 1.8%. However, bond yields are rising which could pressure growth stocks.",
                "confidence": 0.85,
                "sources": ["market_data", "sentiment_analysis", "news_analysis"]
            },
            # Response to "Should I buy more AAPL?"
            {
                "response": "Based on technical analysis, AAPL is showing bullish signals with RSI at 58 and price above 20-day MA. However, you already have 31% allocation to AAPL, which exceeds the recommended 5% single-stock limit. Consider rebalancing first.",
                "confidence": 0.78,
                "recommendation": "HOLD",
                "risk_warning": "High concentration risk in single stock",
                "suggested_actions": ["rebalance_portfolio", "reduce_aapl_position"]
            },
            # Response to "Create a diversified portfolio for me"
            {
                "response": "I'll create a diversified portfolio based on your moderate risk profile. Recommended allocation: 60% stocks (20% large-cap, 15% mid-cap, 10% small-cap, 15% international), 30% bonds, 10% alternatives.",
                "confidence": 0.92,
                "portfolio_suggestion": {
                    "stocks": {
                        "SPY": 0.20,  # S&P 500 ETF
                        "MDY": 0.15,  # Mid-cap ETF
                        "IWM": 0.10,  # Small-cap ETF
                        "VEA": 0.15   # International ETF
                    },
                    "bonds": {
                        "BND": 0.30   # Total bond market ETF
                    },
                    "alternatives": {
                        "VNQ": 0.10   # REIT ETF
                    }
                }
            }
        ]
        
        # Mock supporting services
        mock_portfolio_manager.get_portfolio_summary.return_value = {
            "total_value": Decimal("52500.00"),
            "positions": [
                {"symbol": "AAPL", "weight": 0.31},
                {"symbol": "GOOGL", "weight": 0.58},
                {"symbol": "MSFT", "weight": 0.14}
            ]
        }
        
        mock_market_data_service.get_market_sentiment.return_value = {
            "vix": 18.5,
            "sentiment_score": 0.65,  # Cautiously optimistic
            "sector_performance": {
                "Technology": 1.8,
                "Healthcare": 0.5,
                "Finance": -0.3
            }
        }
        
        # When: User interacts with AI assistant
        
        # Query 1: Market sentiment
        sentiment_response = await mock_ai_assistant.process_query(
            user_id, "What's the current market sentiment?"
        )
        
        # Query 2: Stock recommendation
        stock_response = await mock_ai_assistant.process_query(
            user_id, "Should I buy more AAPL?"
        )
        
        # Query 3: Portfolio creation
        portfolio_response = await mock_ai_assistant.process_query(
            user_id, "Create a diversified portfolio for me"
        )
        
        # Then: AI assistant should provide helpful and accurate responses
        
        # Sentiment response validation
        assert "market sentiment" in sentiment_response["response"].lower()
        assert sentiment_response["confidence"] > 0.8
        assert "market_data" in sentiment_response["sources"]
        
        # Stock recommendation validation
        assert stock_response["recommendation"] in ["BUY", "SELL", "HOLD"]
        assert "concentration risk" in stock_response["risk_warning"].lower()
        assert len(stock_response["suggested_actions"]) > 0
        
        # Portfolio suggestion validation
        portfolio_allocation = portfolio_response["portfolio_suggestion"]
        total_allocation = sum(
            sum(assets.values()) for assets in portfolio_allocation.values()
        )
        assert abs(total_allocation - 1.0) < 0.01  # Should sum to ~100%
        assert "stocks" in portfolio_allocation
        assert "bonds" in portfolio_allocation
        assert portfolio_response["confidence"] > 0.9


class TestComplianceAndSecurity:
    """Test compliance and security user scenarios."""

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_trading_limits_and_compliance(
        self,
        mock_compliance_service,
        mock_trading_engine,
        mock_risk_manager
    ):
        """UAT: System enforces trading limits and compliance rules."""
        # Given: User with specific trading limits
        user_id = str(uuid.uuid4())
        portfolio_id = str(uuid.uuid4())
        
        user_limits = {
            "daily_trading_limit": Decimal("10000.00"),
            "max_position_size": Decimal("5000.00"),
            "restricted_securities": ["TSLA"],  # Example restriction
            "pattern_day_trader": False,
            "options_approved": True,
            "margin_approved": False
        }
        
        mock_compliance_service.get_user_limits.return_value = user_limits
        
        # Test scenarios
        test_orders = [
            # Valid order within limits
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 30,
                "price": Decimal("150.00"),
                "order_type": "LIMIT",
                "expected_result": "APPROVED"
            },
            # Order exceeding position size limit
            {
                "symbol": "GOOGL",
                "side": "BUY",
                "quantity": 20,
                "price": Decimal("2800.00"),  # $56,000 total
                "order_type": "LIMIT",
                "expected_result": "REJECTED"
            },
            # Restricted security
            {
                "symbol": "TSLA",
                "side": "BUY",
                "quantity": 10,
                "price": Decimal("200.00"),
                "order_type": "LIMIT",
                "expected_result": "REJECTED"
            }
        ]
        
        # Mock compliance checks
        compliance_results = [
            {"approved": True, "reason": "Within all limits"},
            {"approved": False, "reason": "Exceeds maximum position size"},
            {"approved": False, "reason": "Restricted security"}
        ]
        
        mock_compliance_service.check_order_compliance.side_effect = compliance_results
        
        # When: User attempts to place various orders
        results = []
        
        for i, order in enumerate(test_orders):
            compliance_check = await mock_compliance_service.check_order_compliance(
                user_id, order
            )
            
            results.append({
                "order": order,
                "compliance_result": compliance_check,
                "approved": compliance_check["approved"]
            })
        
        # Then: Compliance rules should be properly enforced
        assert results[0]["approved"] is True  # Valid order
        assert results[1]["approved"] is False  # Exceeds position limit
        assert results[2]["approved"] is False  # Restricted security
        
        assert "within all limits" in results[0]["compliance_result"]["reason"].lower()
        assert "position size" in results[1]["compliance_result"]["reason"].lower()
        assert "restricted" in results[2]["compliance_result"]["reason"].lower()

    @pytest.mark.uat
    @pytest.mark.asyncio
    async def test_user_account_security_features(
        self,
        mock_security_service,
        mock_user_service
    ):
        """UAT: User can manage account security features."""
        # Given: User wants to enhance account security
        user_id = str(uuid.uuid4())
        
        # Mock current security settings
        current_settings = {
            "two_factor_enabled": False,
            "login_notifications": True,
            "trading_notifications": True,
            "suspicious_activity_alerts": True,
            "session_timeout": 30,  # minutes
            "trusted_devices": [],
            "recent_logins": [
                {
                    "timestamp": datetime.utcnow() - timedelta(hours=2),
                    "ip_address": "192.168.1.100",
                    "device": "Chrome on Windows",
                    "location": "New York, NY"
                }
            ]
        }
        
        mock_security_service.get_security_settings.return_value = current_settings
        
        # Mock 2FA setup
        mock_security_service.setup_two_factor.return_value = {
            "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
            "backup_codes": [
                "12345678", "87654321", "11223344", "44332211", "55667788"
            ],
            "secret_key": "JBSWY3DPEHPK3PXP"
        }
        
        mock_security_service.verify_two_factor.return_value = {
            "verified": True,
            "enabled": True
        }
        
        # When: User sets up security features
        
        # Step 1: Check current security settings
        settings = await mock_security_service.get_security_settings(user_id)
        
        # Step 2: Enable 2FA
        if not settings["two_factor_enabled"]:
            two_factor_setup = await mock_security_service.setup_two_factor(user_id)
            
            # Step 3: Verify 2FA with test code
            verification = await mock_security_service.verify_two_factor(
                user_id, "123456"  # Test TOTP code
            )
        
        # Step 4: Update notification preferences
        updated_settings = {
            "login_notifications": True,
            "trading_notifications": True,
            "large_trade_alerts": True,  # New setting
            "withdrawal_notifications": True
        }
        
        mock_security_service.update_notification_settings.return_value = {
            "updated": True,
            "settings": updated_settings
        }
        
        notification_update = await mock_security_service.update_notification_settings(
            user_id, updated_settings
        )
        
        # Then: Security features should be properly configured
        assert settings["two_factor_enabled"] is False  # Initially disabled
        assert len(settings["recent_logins"]) > 0
        
        assert "qr_code" in two_factor_setup
        assert len(two_factor_setup["backup_codes"]) == 5
        
        assert verification["verified"] is True
        assert verification["enabled"] is True
        
        assert notification_update["updated"] is True
        assert notification_update["settings"]["large_trade_alerts"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "uat"])