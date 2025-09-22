-- PostgreSQL Initialization Script for Nautilus Trader Engine
-- Creates necessary databases, users, and initial schema

-- Create database for trading data
CREATE DATABASE nautilus_trader;
GRANT ALL PRIVILEGES ON DATABASE nautilus_trader TO nautilus;

-- Connect to the trading database
\c nautilus_trader;

-- Create schema for different data types
CREATE SCHEMA IF NOT EXISTS trading AUTHORIZATION nautilus;
CREATE SCHEMA IF NOT EXISTS market_data AUTHORIZATION nautilus;
CREATE SCHEMA IF NOT EXISTS indicators AUTHORIZATION nautilus;
CREATE SCHEMA IF NOT EXISTS strategies AUTHORIZATION nautilus;
CREATE SCHEMA IF NOT EXISTS backtesting AUTHORIZATION nautilus;
CREATE SCHEMA IF NOT EXISTS performance AUTHORIZATION nautilus;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Set default search path
ALTER DATABASE nautilus_trader SET search_path TO trading, market_data, indicators, strategies, backtesting, performance, public;

-- Create tables for market data
CREATE TABLE IF NOT EXISTS market_data.ohlcv (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open_price DECIMAL(20,8) NOT NULL,
    high_price DECIMAL(20,8) NOT NULL,
    low_price DECIMAL(20,8) NOT NULL,
    close_price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timestamp)
);

-- Create hypertable for time-series data (if TimescaleDB is available)
-- SELECT create_hypertable('market_data.ohlcv', 'timestamp', if_not_exists => TRUE);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timestamp ON market_data.ohlcv (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp ON market_data.ohlcv (timestamp DESC);

-- Create table for trading signals
CREATE TABLE IF NOT EXISTS trading.signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- BUY, SELL, HOLD
    confidence DECIMAL(5,4),
    price DECIMAL(20,8),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create table for orders
CREATE TABLE IF NOT EXISTS trading.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- BUY, SELL
    order_type VARCHAR(20) NOT NULL, -- MARKET, LIMIT, STOP
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    status VARCHAR(20) DEFAULT 'PENDING',
    strategy_name VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    filled_price DECIMAL(20,8),
    fees DECIMAL(20,8) DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create table for positions
CREATE TABLE IF NOT EXISTS trading.positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    average_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'OPEN',
    strategy_name VARCHAR(100),
    entry_time TIMESTAMPTZ DEFAULT NOW(),
    exit_time TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create table for performance metrics
CREATE TABLE IF NOT EXISTS performance.metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20,8),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_signals_strategy_timestamp ON trading.signals (strategy_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON trading.orders (symbol, status);
CREATE INDEX IF NOT EXISTS idx_orders_strategy ON trading.orders (strategy_name);
CREATE INDEX IF NOT EXISTS idx_positions_symbol_status ON trading.positions (symbol, status);
CREATE INDEX IF NOT EXISTS idx_metrics_strategy_timestamp ON performance.metrics (strategy_name, timestamp DESC);

-- Create views for common queries
CREATE OR REPLACE VIEW trading.portfolio_summary AS
SELECT
    symbol,
    SUM(quantity) as total_quantity,
    SUM(quantity * average_price) / NULLIF(SUM(quantity), 0) as avg_price,
    SUM(unrealized_pnl) as total_unrealized_pnl,
    SUM(realized_pnl) as total_realized_pnl,
    COUNT(*) as position_count
FROM trading.positions
WHERE status = 'OPEN'
GROUP BY symbol;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA trading TO nautilus;
GRANT ALL PRIVILEGES ON SCHEMA market_data TO nautilus;
GRANT ALL PRIVILEGES ON SCHEMA indicators TO nautilus;
GRANT ALL PRIVILEGES ON SCHEMA strategies TO nautilus;
GRANT ALL PRIVILEGES ON SCHEMA backtesting TO nautilus;
GRANT ALL PRIVILEGES ON SCHEMA performance TO nautilus;

-- Grant permissions on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO nautilus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA market_data TO nautilus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA indicators TO nautilus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA strategies TO nautilus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA backtesting TO nautilus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA performance TO nautilus;

-- Insert sample data for testing
INSERT INTO market_data.ohlcv (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
VALUES
    ('AAPL', NOW() - INTERVAL '1 day', 150.00, 152.00, 149.00, 151.50, 1000000),
    ('GOOGL', NOW() - INTERVAL '1 day', 2800.00, 2820.00, 2790.00, 2810.00, 500000)
ON CONFLICT (symbol, timestamp) DO NOTHING;

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON trading.orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON trading.positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();