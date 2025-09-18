# NautilusTrader Engine Integration

This module provides a complete integration of NautilusTrader with Interactive Brokers for both paper and live trading. The integration is designed to be production-ready with comprehensive error handling, monitoring, and testing capabilities.

## 🚀 Quick Start

### Prerequisites

1. **Interactive Brokers Account**: You need either a paper trading or live trading account
2. **TWS or IB Gateway**: Interactive Brokers Trader Workstation or IB Gateway must be running
3. **Python Dependencies**: Install required packages

```bash
pip install nautilus_trader fastapi uvicorn pydantic
```

### Basic Usage

```bash
# Check system status
python start_nautilus.py --status

# Start in paper trading mode (default)
python start_nautilus.py

# Start in live trading mode
python start_nautilus.py --live

# Run integration tests
python start_nautilus.py --test
```

## 📁 Project Structure

```
nautilus_trader_engine/
├── main.py                    # Main engine service
├── test_integration.py        # Comprehensive test suite
├── README.md                  # This file
├── config/
│   └── ib_config.py          # Interactive Brokers configuration
├── services/
│   ├── trading_gateway.py    # Trading gateway service
│   └── risk_management_service.py  # Risk management
└── adapters/                 # Custom adapters (if needed)
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Interactive Brokers Configuration
IB_HOST=127.0.0.1
IB_PAPER_PORT=7497
IB_LIVE_PORT=7496
IB_PAPER_CLIENT_ID=1
IB_LIVE_CLIENT_ID=2
IB_PAPER_ACCOUNT=DU123456
IB_LIVE_ACCOUNT=U123456
```

### Interactive Brokers Setup

1. **Install TWS or IB Gateway**
   - Download from Interactive Brokers website
   - Configure API settings

2. **Enable API Access**
   - In TWS: Configure → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set Socket port (7497 for paper, 7496 for live)
   - Add trusted IP addresses (127.0.0.1 for local)

3. **Paper Trading Setup**
   - Use paper trading account credentials
   - Connect to port 7497
   - No real money at risk

4. **Live Trading Setup**
   - Use live trading account credentials
   - Connect to port 7496
   - **⚠️ Real money at risk - use with caution**

## 🏃‍♂️ Running the Engine

### Method 1: Using the Startup Script (Recommended)

```bash
# Check system status first
python start_nautilus.py --status

# Start paper trading
python start_nautilus.py --paper

# Start live trading
python start_nautilus.py --live

# Run tests
python start_nautilus.py --test --full
```

### Method 2: Direct Engine Execution

```bash
# Paper trading
python nautilus_trader_engine/main.py --mode paper

# Live trading
python nautilus_trader_engine/main.py --mode live

# With custom configuration
python nautilus_trader_engine/main.py --mode paper --config custom_config.json
```

### Method 3: Integration Tests

```bash
# Test paper trading
python nautilus_trader_engine/test_integration.py --mode paper

# Test live trading
python nautilus_trader_engine/test_integration.py --mode live

# Full test suite
python nautilus_trader_engine/test_integration.py --full
```

## 🧪 Testing

### Integration Test Suite

The integration test suite validates:

- ✅ Configuration loading
- ✅ Engine initialization
- ✅ Interactive Brokers connection
- ✅ Market data feeds
- ✅ Order validation
- ✅ Risk management
- ✅ Health monitoring
- ✅ Graceful shutdown

```bash
# Run all tests
python start_nautilus.py --test --full

# Test specific mode
python start_nautilus.py --test --paper
python start_nautilus.py --test --live

# Save test results
python nautilus_trader_engine/test_integration.py --mode paper --save-results
```

### Test Results

Test results are saved as JSON files with detailed information:
- Test execution times
- Pass/fail status
- Error details
- System health metrics

## 📊 Monitoring and Health Checks

### Health Check Endpoint

The engine provides comprehensive health monitoring:

```python
# Programmatic health check
engine = NautilusTraderEngine(mode="paper")
health = await engine.health_check()
print(health)
```

### Logging

Comprehensive logging is configured:
- Console output for real-time monitoring
- File logging for historical analysis
- Structured log format with timestamps

```bash
# View logs
tail -f nautilus_trader_engine.log

# View test logs
tail -f integration_test.log
```

## 🔒 Risk Management

### Built-in Risk Controls

- **Position Limits**: Maximum position sizes
- **Order Validation**: Pre-trade risk checks
- **Real-time Monitoring**: Continuous risk assessment
- **Emergency Stops**: Automatic position closure

### Risk Configuration

```python
# Risk management settings
risk_config = {
    "max_position_size": 1000,
    "max_daily_loss": 5000,
    "max_orders_per_minute": 10,
    "enable_emergency_stop": True
}
```

## 🚨 Error Handling

### Graceful Degradation

- **Connection Failures**: Automatic reconnection attempts
- **Missing Dependencies**: Fallback to simulation mode
- **Configuration Errors**: Clear error messages and guidance
- **Market Data Issues**: Fallback data sources

### Error Recovery

```python
# The engine handles various error scenarios:
# - Network disconnections
# - Invalid orders
# - Market data interruptions
# - Risk limit breaches
```

## 📈 Performance Optimization

### High-Performance Features

- **Asynchronous Architecture**: Non-blocking operations
- **Connection Pooling**: Efficient resource usage
- **Caching**: Reduced latency for frequent operations
- **Batch Processing**: Optimized order handling

### Performance Monitoring

```python
# Monitor performance metrics
metrics = {
    "order_latency": "< 10ms",
    "market_data_latency": "< 5ms",
    "memory_usage": "< 500MB",
    "cpu_usage": "< 20%"
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Connection refused to IB Gateway
   Solution: Ensure TWS/IB Gateway is running and API is enabled
   ```

2. **Authentication Failed**
   ```
   Error: Invalid client ID or account
   Solution: Check client ID and account settings in configuration
   ```

3. **Market Data Issues**
   ```
   Error: No market data permissions
   Solution: Ensure market data subscriptions are active
   ```

4. **Order Rejection**
   ```
   Error: Order rejected by broker
   Solution: Check account permissions and order parameters
   ```

### Debug Mode

```bash
# Enable debug logging
python start_nautilus.py --log-level DEBUG

# Validate configuration
python start_nautilus.py --validate

# Check system status
python start_nautilus.py --status
```

## 🔄 Development Workflow

### Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd algorithmic-trading-system
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run Tests**
   ```bash
   python start_nautilus.py --test --full
   ```

### Code Quality

- **Type Hints**: Full type annotation
- **Documentation**: Comprehensive docstrings
- **Error Handling**: Robust exception management
- **Testing**: Comprehensive test coverage

## 📚 API Reference

### NautilusTraderEngine

```python
class NautilusTraderEngine:
    def __init__(self, mode: str = "paper", config_path: Optional[str] = None)
    async def initialize(self) -> None
    async def start(self) -> None
    async def stop(self) -> None
    async def health_check(self) -> Dict[str, Any]
```

### TradingGateway

```python
class TradingGateway:
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def place_order(self, order: Dict[str, Any]) -> str
    async def cancel_order(self, order_id: str) -> bool
    async def get_positions(self) -> Dict[str, Any]
```

## 🛡️ Security Considerations

### Best Practices

- **Environment Variables**: Store sensitive data in .env files
- **Access Control**: Limit API access to trusted IPs
- **Encryption**: Use secure connections (SSL/TLS)
- **Audit Logging**: Comprehensive activity logging

### Production Deployment

- **Firewall Configuration**: Restrict network access
- **Monitoring**: Real-time system monitoring
- **Backup**: Regular configuration backups
- **Updates**: Keep dependencies updated

## 📞 Support

### Getting Help

1. **Check Documentation**: Review this README and code comments
2. **Run Diagnostics**: Use `--status` and `--validate` flags
3. **Check Logs**: Review log files for error details
4. **Test Suite**: Run integration tests to identify issues

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is part of the Algorithmic Trading System and follows the project's licensing terms.

---

**⚠️ Important Disclaimer**: This software is for educational and research purposes. Trading involves substantial risk of loss. Always test thoroughly with paper trading before using real money. The authors are not responsible for any financial losses.