-- Create the trading analytics database
CREATE DATABASE IF NOT EXISTS trading_analytics;

-- Use the trading analytics database
USE trading_analytics;

-- Market data table with partitioning by date and symbol
CREATE TABLE IF NOT EXISTS market_data (
    timestamp DateTime64(3, 'UTC'),
    symbol String,
    price Decimal(15, 6),
    volume UInt64,
    bid_price Decimal(15, 6),
    ask_price Decimal(15, 6),
    bid_size UInt32,
    ask_size UInt32,
    data_source String,
    exchange String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(timestamp), symbol)
ORDER BY (symbol, timestamp)
SETTINGS index_granularity = 8192;

-- Order execution metrics table
CREATE TABLE IF NOT EXISTS order_executions (
    timestamp DateTime64(3, 'UTC'),
    order_id String,
    symbol String,
    side Enum8('BUY' = 1, 'SELL' = 2),
    quantity Decimal(15, 6),
    price Decimal(15, 6),
    execution_time_ms UInt32,
    latency_ms UInt32,
    broker String,
    account_id String,
    strategy_id String,
    commission Decimal(10, 4),
    slippage Decimal(10, 6),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY (toYYYYMM(timestamp), symbol)
ORDER BY (symbol, timestamp)
SETTINGS index_granularity = 8192;

-- Performance metrics table for system monitoring
CREATE TABLE IF NOT EXISTS performance_metrics (
    timestamp DateTime64(3, 'UTC'),
    metric_type String,
    metric_name String,
    value Float64,
    labels Map(String, String),
    source String,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (metric_type, metric_name, timestamp)
SETTINGS index_granularity = 8192;

-- Strategy performance table
CREATE TABLE IF NOT EXISTS strategy_performance (
    timestamp DateTime64(3, 'UTC'),
    strategy_id String,
    backtest_id String,
    symbol String,
    total_return Decimal(10, 4),
    annual_return Decimal(10, 4),
    volatility Decimal(10, 4),
    sharpe_ratio Decimal(10, 4),
    sortino_ratio Decimal(10, 4),
    max_drawdown Decimal(10, 4),
    win_rate Decimal(10, 4),
    profit_factor Decimal(10, 4),
    total_trades UInt32,
    winning_trades UInt32,
    losing_trades UInt32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (strategy_id, timestamp)
SETTINGS index_granularity = 8192;

-- Portfolio analytics table
CREATE TABLE IF NOT EXISTS portfolio_analytics (
    timestamp DateTime64(3, 'UTC'),
    user_id String,
    account_id String,
    total_value Decimal(15, 2),
    cash_balance Decimal(15, 2),
    positions_value Decimal(15, 2),
    daily_pnl Decimal(15, 2),
    total_return Decimal(10, 4),
    sharpe_ratio Decimal(10, 4),
    max_drawdown Decimal(10, 4),
    risk_score Decimal(3, 2),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (user_id, timestamp)
SETTINGS index_granularity = 8192;

-- Risk metrics table
CREATE TABLE IF NOT EXISTS risk_metrics (
    timestamp DateTime64(3, 'UTC'),
    portfolio_id String,
    var_95 Decimal(15, 2),
    var_99 Decimal(15, 2),
    cvar_95 Decimal(15, 2),
    beta Float64,
    correlation_sp500 Float64,
    volatility_30d Decimal(10, 6),
    risk_level Enum8('LOW' = 1, 'MEDIUM' = 2, 'HIGH' = 3, 'CRITICAL' = 4),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (portfolio_id, timestamp)
SETTINGS index_granularity = 8192;

-- Create materialized views for real-time analytics

-- Real-time market data aggregations
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_1min_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(window_start)
ORDER BY (symbol, window_start)
AS SELECT
    symbol,
    toStartOfMinute(timestamp) as window_start,
    first_value(price) as open_price,
    max(price) as high_price,
    min(price) as low_price,
    last_value(price) as close_price,
    sum(volume) as total_volume,
    count() as tick_count
FROM market_data
GROUP BY symbol, window_start;

-- Order execution performance metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS execution_performance_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(window_start)
ORDER BY (broker, window_start)
AS SELECT
    broker,
    toStartOfHour(timestamp) as window_start,
    avg(execution_time_ms) as avg_execution_time,
    quantile(0.95)(execution_time_ms) as p95_execution_time,
    avg(latency_ms) as avg_latency,
    quantile(0.95)(latency_ms) as p95_latency,
    count() as total_orders
FROM order_executions
GROUP BY broker, window_start;

-- Insert sample data for testing
INSERT INTO market_data VALUES
('2024-08-29 15:30:00.000', 'AAPL', 150.25, 1000, 150.24, 150.26, 500, 600, 'IBKR', 'NASDAQ', now()),
('2024-08-29 15:30:01.000', 'AAPL', 150.27, 1500, 150.26, 150.28, 400, 700, 'IBKR', 'NASDAQ', now()),
('2024-08-29 15:30:02.000', 'MSFT', 330.45, 800, 330.44, 330.46, 300, 400, 'IBKR', 'NASDAQ', now()),
('2024-08-29 15:30:03.000', 'TSLA', 235.67, 2000, 235.66, 235.68, 600, 800, 'IBKR', 'NASDAQ', now());

INSERT INTO order_executions VALUES
('2024-08-29 15:30:00.000', 'ORD_001', 'AAPL', 'BUY', 100, 150.25, 45, 2, 'IBKR', 'ACC_001', 'STRAT_001', 1.25, 0.01, now()),
('2024-08-29 15:30:05.000', 'ORD_002', 'MSFT', 'SELL', 50, 330.45, 38, 1, 'IBKR', 'ACC_001', 'STRAT_002', 0.75, 0.02, now()),
('2024-08-29 15:30:10.000', 'ORD_003', 'TSLA', 'BUY', 25, 235.67, 52, 3, 'IBKR', 'ACC_002', 'STRAT_001', 0.50, 0.01, now());

INSERT INTO performance_metrics VALUES
('2024-08-29 15:30:00.000', 'system', 'api_latency_ms', 8.5, {'endpoint': '/api/v1/orders', 'method': 'POST'}, 'api_gateway', now()),
('2024-08-29 15:30:00.000', 'system', 'memory_usage_percent', 65.2, {'service': 'trading_engine'}, 'prometheus', now()),
('2024-08-29 15:30:00.000', 'trading', 'orders_per_second', 125.0, {'broker': 'IBKR', 'type': 'market'}, 'trading_engine', now());