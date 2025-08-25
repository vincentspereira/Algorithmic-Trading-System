-- Market Data Table
CREATE TABLE IF NOT EXISTS market_data
(
    symbol String,
    timeframe String,
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (symbol, timeframe, timestamp);

-- Backtest Results Table
CREATE TABLE IF NOT EXISTS backtest_results
(
    request_id UUID,
    timestamp DateTime,
    strategy_name String,
    symbol String,
    parameters String, -- JSON
    metrics String,   -- JSON
    trades String,    -- JSON
    equity_curve String, -- JSON
    status String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (request_id, timestamp);

-- Trades Table
CREATE TABLE IF NOT EXISTS backtest_trades
(
    request_id UUID,
    trade_id UUID,
    timestamp DateTime,
    symbol String,
    side String,
    quantity Float64,
    price Float64,
    pnl Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (request_id, timestamp);

-- Equity Points Table
CREATE TABLE IF NOT EXISTS backtest_equity
(
    request_id UUID,
    timestamp DateTime,
    equity Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (request_id, timestamp);
