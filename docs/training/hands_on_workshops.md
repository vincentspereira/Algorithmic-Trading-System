# Hands-On Workshops - Algorithmic Trading System

## Workshop Overview

This document contains comprehensive materials for hands-on workshops designed to provide practical, interactive learning experiences with the Algorithmic Trading System. Each workshop includes detailed lesson plans, exercises, datasets, and assessment materials.

## Workshop Catalog

### Beginner Workshops

1. **Getting Started with Algorithmic Trading** (Half-day)
2. **Building Your First Strategy** (Full-day)
3. **Understanding Market Data and Backtesting** (Half-day)

### Intermediate Workshops

4. **Advanced Strategy Development** (Full-day)
5. **Risk Management and Portfolio Optimization** (Full-day)
6. **API Integration and Automation** (Full-day)

### Advanced Workshops

7. **Machine Learning for Trading** (2-day intensive)
8. **Multi-Asset and Cross-Market Strategies** (Full-day)
9. **Production Trading Systems** (2-day intensive)

---

## Workshop 1: Getting Started with Algorithmic Trading

**Duration:** 4 hours  
**Capacity:** 20 participants  
**Prerequisites:** None  
**Materials:** Laptop, internet access, sandbox account

### Learning Objectives

By the end of this workshop, participants will be able to:
- Understand fundamental concepts of algorithmic trading
- Navigate the trading platform interface
- Create a basic trading strategy
- Interpret basic performance metrics

### Workshop Schedule

#### Session 1: Introduction and Platform Overview (90 minutes)

**Time:** 9:00 AM - 10:30 AM

**Content:**
- Welcome and introductions (15 minutes)
- Algorithmic trading fundamentals (30 minutes)
- Platform tour and navigation (30 minutes)
- Account setup and sandbox access (15 minutes)

**Activities:**
- Interactive platform exploration
- Q&A session
- Hands-on navigation exercise

**Materials Provided:**
- Workshop handbook
- Platform quick reference guide
- Sandbox account credentials

#### Break (15 minutes)

#### Session 2: Strategy Concepts and Creation (90 minutes)

**Time:** 10:45 AM - 12:15 PM

**Content:**
- Trading strategy fundamentals (20 minutes)
- Technical indicators overview (25 minutes)
- Strategy builder walkthrough (25 minutes)
- Hands-on strategy creation (20 minutes)

**Exercise 1: Create a Simple Moving Average Strategy**
```
Objective: Build a basic trend-following strategy
Time: 45 minutes

Instructions:
1. Open the strategy builder
2. Create a new strategy named "My First MA Strategy"
3. Add two moving averages (10-day and 30-day)
4. Set buy condition: 10-day MA crosses above 30-day MA
5. Set sell condition: 10-day MA crosses below 30-day MA
6. Configure basic risk management (2% position size)
7. Save the strategy

Expected Outcome:
- Functional moving average crossover strategy
- Understanding of strategy logic flow
- Familiarity with strategy builder interface
```

#### Lunch Break (60 minutes)

#### Session 3: Backtesting and Analysis (90 minutes)

**Time:** 1:15 PM - 2:45 PM

**Content:**
- Backtesting concepts and importance (20 minutes)
- Setting up a backtest (20 minutes)
- Interpreting results (25 minutes)
- Performance metrics explanation (25 minutes)

**Exercise 2: Backtest Your Strategy**
```
Objective: Test the created strategy on historical data
Time: 60 minutes

Instructions:
1. Select your MA strategy for backtesting
2. Set date range: January 1, 2022 to December 31, 2023
3. Choose test assets: AAPL, MSFT, GOOGL
4. Set initial capital: $100,000
5. Run the backtest
6. Analyze results:
   - Total return
   - Sharpe ratio
   - Maximum drawdown
   - Number of trades
7. Compare with buy-and-hold benchmark

Deliverable:
- Completed backtest report
- Written analysis of results (1 page)
```

#### Break (15 minutes)

#### Session 4: Results Review and Next Steps (60 minutes)

**Time:** 3:00 PM - 4:00 PM

**Content:**
- Group discussion of backtest results (20 minutes)
- Strategy improvement ideas (15 minutes)
- Platform resources and support (10 minutes)
- Next steps and advanced workshops (15 minutes)

**Group Activity: Strategy Showcase**
- Each participant presents their strategy results (2 minutes each)
- Group discussion on different outcomes
- Identification of best practices

### Assessment Structure

#### Formative Assessment (Ongoing)
**Exercise Completion Tracking:**
- Exercise 1: Strategy Creation (Pass/Fail)
- Exercise 2: Backtesting Analysis (Scored 1-10)
- Participation in discussions (Qualitative feedback)

#### Summative Assessment (End of Workshop)
**Portfolio Submission:**
- Completed strategy with documentation
- Backtest results analysis
- Written reflection on learning outcomes

**Assessment Criteria:**
- **Technical Competency (40%)**
  - Correct use of platform features
  - Proper strategy implementation
  - Accurate backtesting setup
- **Analysis Quality (35%)**
  - Interpretation of results
  - Understanding of performance metrics
  - Risk assessment accuracy
- **Communication (25%)**
  - Clear documentation
  - Effective presentation
  - Constructive participation

**Grading Scale:**
- Excellent (90-100%): Demonstrates mastery of all concepts
- Proficient (80-89%): Shows solid understanding with minor gaps
- Developing (70-79%): Basic understanding, needs improvement
- Novice (Below 70%): Requires additional support and practice

### Workshop Materials

#### Participant Handbook

**Section 1: Algorithmic Trading Basics**
- What is algorithmic trading?
- Benefits and risks
- Common strategy types
- Market structure overview

**Section 2: Platform Guide**
- Interface navigation
- Key features overview
- Account management
- Support resources

**Section 3: Strategy Development**
- Strategy design principles
- Technical indicators guide
- Risk management basics
- Testing and validation

**Section 4: Exercises and Solutions**
- Step-by-step exercise guides
- Solution examples
- Troubleshooting tips
- Additional practice problems

#### Dataset Package

**Historical Data Included:**
- Daily OHLCV data for 50 major stocks (2020-2024)
- Market indices (S&P 500, NASDAQ, Dow Jones)
- Sector ETFs for diversification testing
- Economic indicators and events

**Data Format:**
```csv
Date,Symbol,Open,High,Low,Close,Volume,Adjusted_Close
2024-01-01,AAPL,185.50,187.25,184.75,186.80,45234567,186.80
2024-01-02,AAPL,186.90,188.15,186.20,187.45,38567234,187.45
...
```

#### Assessment Rubric

**Strategy Creation (40 points)**
- Correct implementation of moving average logic (15 points)
- Appropriate risk management settings (10 points)
- Clear strategy documentation (10 points)
- Successful strategy execution (5 points)

**Backtesting Analysis (40 points)**
- Proper backtest configuration (10 points)
- Accurate results interpretation (15 points)
- Meaningful performance analysis (10 points)
- Benchmark comparison (5 points)

**Participation and Engagement (20 points)**
- Active participation in discussions (10 points)
- Quality of questions asked (5 points)
- Collaboration with other participants (5 points)

---

## Workshop 2: Building Your First Strategy

**Duration:** 8 hours (Full day)  
**Capacity:** 15 participants  
**Prerequisites:** Workshop 1 or equivalent experience

### Learning Objectives

Participants will:
- Design and implement a complete trading strategy
- Apply advanced technical indicators
- Implement comprehensive risk management
- Optimize strategy parameters
- Prepare strategies for live trading

### Detailed Schedule

#### Morning Session (4 hours)

**9:00 AM - 9:30 AM: Welcome and Review**
- Recap of fundamental concepts
- Introduction to advanced features
- Workshop objectives and agenda

**9:30 AM - 11:00 AM: Advanced Strategy Design**

**Content:**
- Multi-indicator strategies
- Signal confirmation techniques
- Market regime detection
- Adaptive parameters

**Exercise 3: Design a Multi-Indicator Strategy**
```
Objective: Create a strategy using multiple technical indicators
Time: 75 minutes

Strategy Requirements:
1. Primary signal: RSI oversold/overbought conditions
2. Confirmation: MACD histogram direction
3. Filter: Price above/below 200-day moving average
4. Volume confirmation: Above average volume

Implementation Steps:
1. Add RSI indicator (14-period)
2. Add MACD indicator (12,26,9)
3. Add 200-day simple moving average
4. Add volume moving average (20-period)
5. Create compound entry conditions:
   - Buy: RSI < 30 AND MACD histogram rising AND Price > MA200 AND Volume > Volume_MA
   - Sell: RSI > 70 AND MACD histogram falling AND Price < MA200 AND Volume > Volume_MA
6. Test logic with sample data

Expected Outcome:
- Complex multi-indicator strategy
- Understanding of signal confirmation
- Experience with compound conditions
```

**11:00 AM - 11:15 AM: Break**

**11:15 AM - 12:30 PM: Risk Management Deep Dive**

**Content:**
- Position sizing methods
- Stop-loss strategies
- Profit-taking techniques
- Portfolio-level risk controls

**Exercise 4: Implement Advanced Risk Management**
```
Objective: Add sophisticated risk controls to your strategy
Time: 60 minutes

Risk Management Components:
1. Dynamic position sizing based on volatility
2. Multiple stop-loss levels
3. Trailing profit targets
4. Maximum correlation limits
5. Drawdown-based position reduction

Implementation:
1. Calculate 20-day volatility for each asset
2. Set position size = 1% / (2 * volatility)
3. Add initial stop-loss at 2 * ATR below entry
4. Add trailing stop at 1.5 * ATR
5. Set profit target at 3 * ATR above entry
6. Limit total portfolio exposure to 20%
7. Reduce position sizes if drawdown > 5%

Validation:
- Test risk controls with extreme market scenarios
- Verify position sizing calculations
- Confirm stop-loss and profit-taking logic
```

**12:30 PM - 1:30 PM: Lunch Break**

#### Afternoon Session (4 hours)

**1:30 PM - 3:00 PM: Strategy Optimization**

**Content:**
- Parameter optimization techniques
- Walk-forward analysis
- Overfitting prevention
- Robustness testing

**Exercise 5: Optimize Strategy Parameters**
```
Objective: Find optimal parameters for your strategy
Time: 75 minutes

Optimization Process:
1. Identify key parameters to optimize:
   - RSI period (10-20)
   - MACD parameters (fast: 8-16, slow: 20-30)
   - Stop-loss multiplier (1.5-3.0)
   - Profit target multiplier (2.0-4.0)

2. Set up parameter ranges and steps
3. Run optimization on training data (2020-2022)
4. Select best parameter set based on Sharpe ratio
5. Validate on out-of-sample data (2023)
6. Compare optimized vs. original performance

Tools Used:
- Built-in optimization engine
- Parameter sweep functionality
- Statistical significance testing

Deliverable:
- Optimized strategy with documented parameters
- Performance comparison report
- Robustness analysis summary
```

**3:00 PM - 3:15 PM: Break**

**3:15 PM - 4:30 PM: Backtesting and Validation**

**Content:**
- Comprehensive backtesting setup
- Multiple timeframe analysis
- Market regime testing
- Transaction cost modeling

**Exercise 6: Comprehensive Strategy Validation**
```
Objective: Thoroughly test your optimized strategy
Time: 60 minutes

Validation Tests:
1. Long-term backtest (2018-2024)
2. Different market conditions:
   - Bull market (2020-2021)
   - Bear market (2022)
   - Sideways market (2015-2016)
3. Multiple asset classes:
   - Large-cap stocks
   - Small-cap stocks
   - International stocks
4. Transaction cost sensitivity analysis
5. Slippage impact assessment

Analysis Requirements:
- Performance metrics comparison
- Drawdown analysis
- Trade distribution analysis
- Risk-adjusted returns calculation

Expected Results:
- Comprehensive performance report
- Strategy strengths and weaknesses identification
- Recommendations for improvement
```

**4:30 PM - 5:00 PM: Results Presentation and Wrap-up**

**Activities:**
- Participant strategy presentations (3 minutes each)
- Group discussion on findings
- Best practices sharing
- Next steps and resources

### Advanced Exercises

#### Bonus Exercise: Market Regime Detection

```
Objective: Enhance strategy with market regime awareness
Time: 45 minutes (optional)

Implementation:
1. Create market regime indicator using:
   - VIX levels (low/medium/high volatility)
   - Market trend (bull/bear/sideways)
   - Economic indicators (recession/expansion)

2. Modify strategy behavior based on regime:
   - High volatility: Reduce position sizes
   - Bear market: Increase cash allocation
   - Low volatility: Increase position sizes

3. Test regime-aware vs. static strategy
4. Analyze performance differences

Advanced Concepts:
- Hidden Markov Models for regime detection
- Machine learning classification
- Dynamic parameter adjustment
```

### Workshop Resources

#### Code Templates

**Python Strategy Template:**
```python
import pandas as pd
import numpy as np
from trading_system import Strategy, Indicator

class MultiIndicatorStrategy(Strategy):
    def __init__(self, rsi_period=14, macd_fast=12, macd_slow=26, 
                 ma_period=200, volume_period=20):
        super().__init__()
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.ma_period = ma_period
        self.volume_period = volume_period
        
    def initialize(self):
        self.rsi = Indicator.RSI(period=self.rsi_period)
        self.macd = Indicator.MACD(fast=self.macd_fast, slow=self.macd_slow)
        self.ma200 = Indicator.SMA(period=self.ma_period)
        self.volume_ma = Indicator.SMA(period=self.volume_period, field='volume')
        
    def on_data(self, data):
        # Calculate indicators
        rsi_value = self.rsi.calculate(data)
        macd_hist = self.macd.histogram(data)
        ma200_value = self.ma200.calculate(data)
        volume_ma_value = self.volume_ma.calculate(data)
        
        # Entry conditions
        buy_signal = (rsi_value < 30 and 
                     macd_hist > macd_hist.shift(1) and
                     data.close > ma200_value and
                     data.volume > volume_ma_value)
                     
        sell_signal = (rsi_value > 70 and
                      macd_hist < macd_hist.shift(1) and
                      data.close < ma200_value and
                      data.volume > volume_ma_value)
        
        # Execute trades
        if buy_signal and not self.position:
            self.buy(size=self.calculate_position_size(data))
        elif sell_signal and self.position:
            self.sell()
            
    def calculate_position_size(self, data):
        volatility = data.close.pct_change().rolling(20).std()
        risk_per_trade = 0.01  # 1% risk per trade
        return risk_per_trade / (2 * volatility)
```

#### Performance Analysis Template

```python
def analyze_strategy_performance(results):
    """
    Comprehensive performance analysis function
    """
    metrics = {}
    
    # Basic metrics
    metrics['total_return'] = results.total_return()
    metrics['annual_return'] = results.annual_return()
    metrics['volatility'] = results.volatility()
    metrics['sharpe_ratio'] = results.sharpe_ratio()
    
    # Risk metrics
    metrics['max_drawdown'] = results.max_drawdown()
    metrics['calmar_ratio'] = results.calmar_ratio()
    metrics['var_95'] = results.value_at_risk(0.95)
    
    # Trade metrics
    metrics['total_trades'] = results.total_trades()
    metrics['win_rate'] = results.win_rate()
    metrics['profit_factor'] = results.profit_factor()
    metrics['avg_trade'] = results.average_trade()
    
    return metrics
```

### Assessment and Certification

#### Final Project Requirements

**Project:** Complete Strategy Development
**Deadline:** End of workshop day
**Deliverables:**
1. Fully implemented strategy with documentation
2. Comprehensive backtest results
3. Performance analysis report
4. Risk assessment summary
5. Strategy presentation (5 minutes)

### Assessment Structure

#### Continuous Assessment (40%)
**Exercise Completion:**
- Exercise 3: Multi-Indicator Strategy (15%)
- Exercise 4: Risk Management Implementation (15%)
- Exercise 5: Parameter Optimization (10%)

#### Final Project Assessment (60%)
**Project Requirements:**
- Complete strategy implementation with documentation
- Comprehensive backtest results and analysis
- Performance comparison report
- Strategy presentation

#### Grading Criteria

**Technical Implementation (40%)**
- Strategy logic correctness
- Risk management implementation
- Code quality and documentation
- Parameter optimization

**Analysis Quality (35%)**
- Backtest comprehensiveness
- Performance interpretation
- Risk assessment accuracy
- Benchmark comparison

**Presentation (25%)**
- Clear communication of strategy concept
- Effective use of visualizations
- Professional presentation style
- Ability to answer questions

#### Certification Levels

**Bronze Level:** Basic strategy implementation with standard risk management
**Silver Level:** Multi-indicator strategy with advanced risk controls and optimization
**Gold Level:** Regime-aware strategy with comprehensive validation and professional presentation

---

## Workshop 3: API Integration and Automation

**Duration:** 8 hours  
**Prerequisites:** Programming experience (Python/JavaScript/Java)  
**Capacity:** 12 participants

### Learning Objectives

- Master API authentication and security
- Implement automated strategy execution
- Build real-time data processing systems
- Create monitoring and alerting systems
- Deploy production-ready trading systems

### Workshop Structure

#### Module 1: API Fundamentals (2 hours)

**Content:**
- REST API architecture
- Authentication methods
- Rate limiting and best practices
- Error handling and retry logic

**Hands-on Lab 1: API Setup and Authentication**
```python
# Lab Exercise: Implement robust API client
import requests
import time
from typing import Optional, Dict, Any

class TradingAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def make_request(self, method: str, endpoint: str, 
                    data: Optional[Dict] = None, 
                    retries: int = 3) -> Dict[Any, Any]:
        """
        Robust API request with retry logic and error handling
        """
        for attempt in range(retries):
            try:
                response = self.session.request(
                    method, f"{self.base_url}{endpoint}", json=data
                )
                
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("Max retries exceeded")

# Exercise: Implement and test the client
client = TradingAPIClient("https://api.trading-system.com", "your-api-key")

# Test authentication
user_info = client.make_request("GET", "/user/profile")
print(f"Authenticated as: {user_info['username']}")

# Test error handling
try:
    invalid_response = client.make_request("GET", "/invalid-endpoint")
except Exception as e:
    print(f"Error handled correctly: {e}")
```

#### Module 2: Real-time Data Processing (2 hours)

**Content:**
- WebSocket connections
- Data streaming and processing
- Real-time indicator calculations
- Event-driven architecture

**Hands-on Lab 2: Real-time Market Data Stream**
```python
import asyncio
import websockets
import json
from collections import deque
import pandas as pd

class RealTimeDataProcessor:
    def __init__(self, symbols: list):
        self.symbols = symbols
        self.data_buffer = {symbol: deque(maxlen=1000) for symbol in symbols}
        self.indicators = {}
        
    async def connect_and_stream(self):
        uri = "wss://api.trading-system.com/ws/market-data"
        
        async with websockets.connect(uri) as websocket:
            # Authenticate
            await websocket.send(json.dumps({
                "action": "authenticate",
                "token": "your-access-token"
            }))
            
            # Subscribe to symbols
            await websocket.send(json.dumps({
                "action": "subscribe",
                "symbols": self.symbols,
                "data_types": ["quotes", "trades"]
            }))
            
            # Process incoming data
            async for message in websocket:
                data = json.loads(message)
                await self.process_market_data(data)
    
    async def process_market_data(self, data):
        if data['type'] == 'quote':
            symbol = data['symbol']
            
            # Add to buffer
            self.data_buffer[symbol].append({
                'timestamp': data['timestamp'],
                'price': data['last'],
                'volume': data['volume']
            })
            
            # Calculate real-time indicators
            await self.update_indicators(symbol)
            
            # Check for trading signals
            await self.check_signals(symbol)
    
    async def update_indicators(self, symbol):
        if len(self.data_buffer[symbol]) < 20:
            return
            
        # Convert to DataFrame for calculations
        df = pd.DataFrame(list(self.data_buffer[symbol]))
        
        # Calculate moving averages
        df['ma_10'] = df['price'].rolling(10).mean()
        df['ma_20'] = df['price'].rolling(20).mean()
        
        # Calculate RSI
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Store latest indicators
        latest = df.iloc[-1]
        self.indicators[symbol] = {
            'ma_10': latest['ma_10'],
            'ma_20': latest['ma_20'],
            'rsi': latest['rsi'],
            'price': latest['price']
        }
    
    async def check_signals(self, symbol):
        if symbol not in self.indicators:
            return
            
        indicators = self.indicators[symbol]
        
        # Simple crossover strategy
        if (indicators['ma_10'] > indicators['ma_20'] and 
            indicators['rsi'] < 70):
            await self.send_buy_signal(symbol, indicators['price'])
        elif (indicators['ma_10'] < indicators['ma_20'] and 
              indicators['rsi'] > 30):
            await self.send_sell_signal(symbol, indicators['price'])
    
    async def send_buy_signal(self, symbol, price):
        print(f"BUY SIGNAL: {symbol} at {price}")
        # Implement order placement logic here
    
    async def send_sell_signal(self, symbol, price):
        print(f"SELL SIGNAL: {symbol} at {price}")
        # Implement order placement logic here

# Exercise: Run the real-time processor
processor = RealTimeDataProcessor(['AAPL', 'GOOGL', 'MSFT'])
asyncio.run(processor.connect_and_stream())
```

#### Module 3: Automated Strategy Execution (2 hours)

**Content:**
- Order management systems
- Position tracking
- Risk monitoring
- Trade execution optimization

**Hands-on Lab 3: Automated Trading System**
```python
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import logging

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Optional[float]
    status: OrderStatus
    filled_quantity: int = 0

class AutomatedTradingSystem:
    def __init__(self, api_client, initial_capital: float):
        self.api_client = api_client
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.max_position_size = 0.05  # 5% max per position
        self.max_daily_loss = 0.02     # 2% max daily loss
        self.daily_pnl = 0.0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def place_order(self, symbol: str, side: OrderSide, 
                         quantity: int, price: Optional[float] = None):
        """
        Place an order with risk checks
        """
        # Pre-trade risk checks
        if not await self.risk_check(symbol, side, quantity, price):
            self.logger.warning(f"Risk check failed for {symbol} {side} {quantity}")
            return None
        
        # Calculate position size
        position_value = quantity * (price or await self.get_current_price(symbol))
        if position_value > self.current_capital * self.max_position_size:
            quantity = int(self.current_capital * self.max_position_size / price)
            self.logger.info(f"Adjusted quantity to {quantity} for risk management")
        
        # Place order via API
        order_data = {
            "symbol": symbol,
            "side": side.value,
            "quantity": quantity,
            "order_type": "market" if price is None else "limit",
            "price": price
        }
        
        try:
            response = await self.api_client.make_request("POST", "/orders", order_data)
            order = Order(
                id=response['id'],
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                status=OrderStatus(response['status'])
            )
            
            self.orders[order.id] = order
            self.logger.info(f"Order placed: {order}")
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            return None
    
    async def risk_check(self, symbol: str, side: OrderSide, 
                        quantity: int, price: Optional[float]) -> bool:
        """
        Comprehensive risk checks before placing orders
        """
        # Check daily loss limit
        if self.daily_pnl < -self.current_capital * self.max_daily_loss:
            self.logger.warning("Daily loss limit exceeded")
            return False
        
        # Check position concentration
        current_price = price or await self.get_current_price(symbol)
        position_value = quantity * current_price
        
        if position_value > self.current_capital * self.max_position_size:
            self.logger.warning(f"Position size too large: {position_value}")
            return False
        
        # Check available capital
        if side == OrderSide.BUY and position_value > self.current_capital * 0.95:
            self.logger.warning("Insufficient capital")
            return False
        
        # Check if we have the position to sell
        if side == OrderSide.SELL:
            current_position = self.positions.get(symbol)
            if not current_position or current_position.quantity < quantity:
                self.logger.warning(f"Insufficient position to sell: {symbol}")
                return False
        
        return True
    
    async def update_positions(self):
        """
        Update positions and P&L from API
        """
        try:
            positions_data = await self.api_client.make_request("GET", "/positions")
            
            for pos_data in positions_data['positions']:
                symbol = pos_data['symbol']
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=pos_data['quantity'],
                    avg_price=pos_data['avg_price'],
                    unrealized_pnl=pos_data['unrealized_pnl'],
                    realized_pnl=pos_data['realized_pnl']
                )
            
            # Update daily P&L
            self.daily_pnl = sum(pos.unrealized_pnl + pos.realized_pnl 
                               for pos in self.positions.values())
            
        except Exception as e:
            self.logger.error(f"Failed to update positions: {e}")
    
    async def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for a symbol
        """
        try:
            quote = await self.api_client.make_request("GET", f"/market-data/quotes/{symbol}")
            return quote['last']
        except Exception as e:
            self.logger.error(f"Failed to get price for {symbol}: {e}")
            return 0.0
    
    async def monitor_orders(self):
        """
        Monitor and update order status
        """
        for order_id, order in self.orders.items():
            if order.status in [OrderStatus.PENDING]:
                try:
                    order_data = await self.api_client.make_request("GET", f"/orders/{order_id}")
                    order.status = OrderStatus(order_data['status'])
                    order.filled_quantity = order_data['filled_quantity']
                    
                    if order.status == OrderStatus.FILLED:
                        self.logger.info(f"Order filled: {order}")
                        await self.update_positions()
                        
                except Exception as e:
                    self.logger.error(f"Failed to update order {order_id}: {e}")
    
    async def run_strategy(self):
        """
        Main strategy execution loop
        """
        while True:
            try:
                # Update positions and orders
                await self.update_positions()
                await self.monitor_orders()
                
                # Strategy logic would go here
                # This is where you'd implement your trading signals
                
                # Example: Simple momentum strategy
                for symbol in ['AAPL', 'GOOGL', 'MSFT']:
                    await self.check_momentum_signals(symbol)
                
                # Wait before next iteration
                await asyncio.sleep(1)  # 1 second intervals
                
            except Exception as e:
                self.logger.error(f"Strategy execution error: {e}")
                await asyncio.sleep(5)  # Wait longer on errors
    
    async def check_momentum_signals(self, symbol: str):
        """
        Example momentum strategy implementation
        """
        # This would contain your actual strategy logic
        # For demonstration purposes only
        pass

# Exercise: Initialize and test the trading system
api_client = TradingAPIClient("https://api.trading-system.com", "your-api-key")
trading_system = AutomatedTradingSystem(api_client, initial_capital=100000)

# Test order placement
# order = await trading_system.place_order("AAPL", OrderSide.BUY, 10, 150.0)
```

#### Module 4: Monitoring and Production Deployment (2 hours)

**Content:**
- System monitoring and alerting
- Performance tracking
- Error handling and recovery
- Production deployment best practices

**Hands-on Lab 4: Production Monitoring System**
```python
import asyncio
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import psutil
import logging

class TradingSystemMonitor:
    def __init__(self, trading_system, alert_email: str):
        self.trading_system = trading_system
        self.alert_email = alert_email
        self.metrics = {
            'uptime': datetime.now(),
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'api_errors': 0,
            'last_heartbeat': datetime.now()
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def monitor_system_health(self):
        """
        Monitor system health metrics
        """
        while True:
            try:
                # Check system resources
                cpu_usage = psutil.cpu_percent()
                memory_usage = psutil.virtual_memory().percent
                disk_usage = psutil.disk_usage('/').percent
                
                # Log system metrics
                self.logger.info(f"System Health - CPU: {cpu_usage}%, "
                               f"Memory: {memory_usage}%, Disk: {disk_usage}%")
                
                # Check for alerts
                if cpu_usage > 80:
                    await self.send_alert("High CPU Usage", f"CPU usage at {cpu_usage}%")
                
                if memory_usage > 85:
                    await self.send_alert("High Memory Usage", f"Memory usage at {memory_usage}%")
                
                # Check trading system health
                await self.check_trading_health()
                
                # Update heartbeat
                self.metrics['last_heartbeat'] = datetime.now()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def check_trading_health(self):
        """
        Check trading system specific health metrics
        """
        try:
            # Check API connectivity
            await self.trading_system.api_client.make_request("GET", "/health")
            
            # Check position updates
            last_update = datetime.now() - timedelta(minutes=5)
            if self.metrics['last_heartbeat'] < last_update:
                await self.send_alert("Trading System Unresponsive", 
                                    "No heartbeat received in 5 minutes")
            
            # Check error rates
            total_operations = self.metrics['total_trades'] + self.metrics['api_errors']
            if total_operations > 0:
                error_rate = self.metrics['api_errors'] / total_operations
                if error_rate > 0.1:  # 10% error rate threshold
                    await self.send_alert("High Error Rate", 
                                        f"Error rate: {error_rate:.2%}")
            
        except Exception as e:
            self.logger.error(f"Trading health check failed: {e}")
            await self.send_alert("API Connectivity Issue", str(e))
    
    async def send_alert(self, subject: str, message: str):
        """
        Send email alert for critical issues
        """
        try:
            msg = MIMEText(f"""
            Alert: {subject}
            
            Message: {message}
            
            System Metrics:
            - Uptime: {datetime.now() - self.metrics['uptime']}
            - Total Trades: {self.metrics['total_trades']}
            - Success Rate: {self.metrics['successful_trades'] / max(1, self.metrics['total_trades']):.2%}
            - API Errors: {self.metrics['api_errors']}
            
            Time: {datetime.now()}
            """)
            
            msg['Subject'] = f"Trading System Alert: {subject}"
            msg['From'] = "trading-system@yourcompany.com"
            msg['To'] = self.alert_email
            
            # Send email (configure SMTP settings)
            # smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            # smtp_server.starttls()
            # smtp_server.login('your-email@gmail.com', 'your-password')
            # smtp_server.send_message(msg)
            # smtp_server.quit()
            
            self.logger.warning(f"ALERT SENT: {subject} - {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    def log_trade(self, success: bool):
        """
        Log trade execution results
        """
        self.metrics['total_trades'] += 1
        if success:
            self.metrics['successful_trades'] += 1
        else:
            self.metrics['failed_trades'] += 1
    
    def log_api_error(self):
        """
        Log API errors
        """
        self.metrics['api_errors'] += 1
    
    async def generate_daily_report(self):
        """
        Generate daily performance report
        """
        while True:
            try:
                # Wait until end of trading day
                now = datetime.now()
                next_report = now.replace(hour=16, minute=0, second=0, microsecond=0)
                if next_report <= now:
                    next_report += timedelta(days=1)
                
                wait_seconds = (next_report - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Generate report
                report = f"""
                Daily Trading Report - {datetime.now().date()}
                
                Performance Metrics:
                - Total Trades: {self.metrics['total_trades']}
                - Successful Trades: {self.metrics['successful_trades']}
                - Success Rate: {self.metrics['successful_trades'] / max(1, self.metrics['total_trades']):.2%}
                - API Errors: {self.metrics['api_errors']}
                
                System Metrics:
                - Uptime: {datetime.now() - self.metrics['uptime']}
                - Current P&L: ${self.trading_system.daily_pnl:.2f}
                - Active Positions: {len(self.trading_system.positions)}
                
                Portfolio Status:
                """
                
                for symbol, position in self.trading_system.positions.items():
                    report += f"- {symbol}: {position.quantity} shares, P&L: ${position.unrealized_pnl:.2f}\n"
                
                self.logger.info("Daily Report Generated")
                await self.send_alert("Daily Trading Report", report)
                
                # Reset daily metrics
                self.metrics['total_trades'] = 0
                self.metrics['successful_trades'] = 0
                self.metrics['failed_trades'] = 0
                self.metrics['api_errors'] = 0
                
            except Exception as e:
                self.logger.error(f"Daily report generation failed: {e}")

# Exercise: Setup monitoring system
# monitor = TradingSystemMonitor(trading_system, "alerts@yourcompany.com")
# asyncio.create_task(monitor.monitor_system_health())
# asyncio.create_task(monitor.generate_daily_report())
```

### Workshop Deliverables

### Assessment Structure

#### Lab Exercise Assessment (40%)
**Module Assessments:**
- Lab 1: API Setup and Authentication (10%)
- Lab 2: Real-time Data Processing (15%)
- Lab 3: Automated Trading System (15%)

#### Final Project Assessment (60%)
**Project Requirements:**
1. **API Integration:** Fully functional API client with error handling
2. **Real-time Processing:** Live data stream processing with indicators
3. **Automated Execution:** Order management with risk controls
4. **Monitoring System:** Health monitoring with alerting
5. **Documentation:** Complete system documentation
6. **Testing:** Unit tests and integration tests

#### Assessment Criteria

**Technical Implementation (50%)**
- Code quality and architecture
- Error handling and robustness
- Performance optimization
- Security best practices

**System Design (30%)**
- Scalability considerations
- Monitoring and observability
- Risk management implementation
- Production readiness

**Documentation and Testing (20%)**
- Code documentation quality
- Test coverage and quality
- Deployment instructions
- User manual

#### Pass/Fail Criteria
**Pass Requirements:**
- All lab exercises completed successfully
- Final project meets minimum technical requirements
- Code passes security and quality checks
- Documentation is complete and accurate

**Excellence Criteria:**
- Innovative implementation approaches
- Superior error handling and edge case coverage
- Comprehensive testing suite
- Production-ready deployment configuration

### Resources and Support

#### Code Repository
- Complete workshop code examples
- Additional utility functions
- Testing frameworks and examples
- Deployment scripts and configurations

#### Documentation
- API reference documentation
- Best practices guide
- Troubleshooting manual
- Performance optimization guide

#### Ongoing Support
- Workshop alumni Slack channel
- Monthly office hours with instructors
- Code review sessions
- Advanced workshop opportunities

---

*These workshop materials are designed to provide comprehensive, hands-on learning experiences that prepare participants for real-world algorithmic trading system development and deployment.*