# Algorithmic Trading Service

This service provides an API and a CLI for algorithmic trading.

## Running the service

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Start the API:

   ```
   uvicorn algorithmic_trading_service.api.main:app --reload
   ```

## Running the CLI

1. Make sure the API is running.

2. Run the CLI:

   ```
   python -m algorithmic_trading_service.cli.cli
   ```
