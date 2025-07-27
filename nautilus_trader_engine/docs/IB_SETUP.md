# Interactive Brokers (IB) Integration Setup Guide

This document provides instructions for configuring and running the NautilusTrader engine with Interactive Brokers (IB) for both paper and live trading.

## 1. TWS/IB Gateway Setup

Before running the engine, you must have either Trader Workstation (TWS) or the IB Gateway running.

### Prerequisites:
- An Interactive Brokers account (either a paper or live account).
- TWS or IB Gateway installed on your machine.

### Configuration Steps:
1.  **Launch TWS or IB Gateway.**
2.  **Enable API Access:**
    - In TWS, go to `File > Global Configuration > API > Settings`.
    - In IB Gateway, the API settings are available on the main configuration screen.
    - Check `Enable ActiveX and Socket Clients`.
    - Make sure `Read-Only API` is **UNCHECKED** if you want to place trades.
    - Note the `Socket port` number. The default for paper trading is `7497`, and for live trading is `7496`.
3.  **Trusted IP Addresses:**
    - For security, it is recommended to add `127.0.0.1` to the list of `Trusted IP Addresses`. This allows the engine running on your local machine to connect without additional confirmations.

## 2. Engine Configuration

The engine's configuration for the IB adapter is located in `nautilus_trader_engine/config/ib_config.py`.

### Paper vs. Live Trading:
You can select the trading mode (paper or live) when launching the engine using a command-line argument.

-   **Paper Trading (Default):**
    ```bash
    python nautilus_trader_engine/main.py --mode paper
    ```
    This will use the `IBPaperConfig` settings, which connect to port `7497` by default.

-   **Live Trading:**
    ```bash
    python nautilus_trader_engine/main.py --mode live
    ```
    This will use the `IBLiveConfig` settings, connecting to port `7496`.

### Account Configuration:
You **MUST** update the `ACCOUNT_ID` in `ib_config.py` to match your IB account numbers:
-   `IBPaperConfig.ACCOUNT_ID`: Set this to your paper trading account ID (e.g., "DU1234567").
-   `IBLiveConfig.ACCOUNT_ID`: Set this to your live trading account ID (e.g., "U1234567").

### Symbol Mapping:
The `SYMBOL_MAP` in `IBCommonConfig` allows you to map the symbols used within NautilusTrader to the specific symbols used by IB.
Example:
```python
SYMBOL_MAP = {
    "EUR/USD": "EUR.CASH",
    "AAPL-STK-SMART": "AAPL",
}
```

## 3. Running the Integration Tests

To ensure your setup is working correctly, you can run the integration tests.

**Prerequisites:**
- A running TWS/Gateway instance connected to a **paper trading account**.
- The test dependencies installed (`pip install -r requirements.txt`).

**Running the tests:**
```bash
python -m unittest nautilus_trader_engine/tests/test_ib_integration.py
```

## 4. Troubleshooting

### Connection Refused Errors
- **Verify TWS/Gateway is running:** Ensure the application is active and you are logged in.
- **Check API Settings:** Confirm that `Enable ActiveX and Socket Clients` is enabled.
- **Firewall:** Make sure your system's firewall is not blocking the connection on the specified socket port.
- **Correct Port:** Double-check that the port in your `ib_config.py` matches the port in the TWS/Gateway API settings.

### Order Rejections
- **Account Permissions:** Ensure your account has the necessary trading permissions for the instruments you are trading.
- **Market Data Subscriptions:** Live accounts may require market data subscriptions for the instruments.
- **Symbol Correctness:** Verify that the symbol in your strategy is correctly mapped in `SYMBOL_MAP` if needed.

### Other Issues
- **Check Logs:** The engine provides detailed logs. Review the console output for any error messages from the IB adapter.
- **ib_insync Logs:** For more detailed debugging, you can increase the logging level for the `ib_insync` library.