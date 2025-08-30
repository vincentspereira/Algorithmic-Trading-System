# PostgreSQL initialization script for Phase 1

# Create extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS btree_gist;

# Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS risk;
CREATE SCHEMA IF NOT EXISTS audit;

-- Core trading tables
CREATE TABLE IF NOT EXISTS trading.instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    asset_class VARCHAR(50),
    exchange VARCHAR(50),
    currency VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange)
);

CREATE TABLE IF NOT EXISTS trading.orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    instrument_id INTEGER REFERENCES trading.instruments(id),
    side VARCHAR(10) CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20),
    quantity DECIMAL(18,8),
    price DECIMAL(18,8),
    stop_price DECIMAL(18,8),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trading.positions (
    id SERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES trading.instruments(id),
    quantity DECIMAL(18,8),
    avg_price DECIMAL(18,8),
    market_value DECIMAL(18,2),
    unrealized_pnl DECIMAL(18,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market data tables
CREATE TABLE IF NOT EXISTS analytics.market_data (
    id SERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES trading.instruments(id),
    timestamp TIMESTAMP NOT NULL,
    open_price DECIMAL(18,8),
    high_price DECIMAL(18,8),
    low_price DECIMAL(18,8),
    close_price DECIMAL(18,8),
    volume BIGINT,
    interval_type VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_market_data_instrument_timestamp 
ON analytics.market_data(instrument_id, timestamp);

-- Vector embeddings for AI/ML
CREATE TABLE IF NOT EXISTS analytics.embeddings (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    embedding vector(384),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk management tables
CREATE TABLE IF NOT EXISTS risk.risk_limits (
    id SERIAL PRIMARY KEY,
    limit_type VARCHAR(50),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    limit_value DECIMAL(18,2),
    current_value DECIMAL(18,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail
CREATE TABLE IF NOT EXISTS audit.events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    user_id VARCHAR(100),
    event_data JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some sample instruments
INSERT INTO trading.instruments (symbol, name, asset_class, exchange, currency) 
VALUES 
    ('AAPL', 'Apple Inc.', 'STOCK', 'NASDAQ', 'USD'),
    ('MSFT', 'Microsoft Corp.', 'STOCK', 'NASDAQ', 'USD'),
    ('SPY', 'SPDR S&P 500 ETF', 'ETF', 'ARCA', 'USD'),
    ('QQQ', 'Invesco QQQ Trust', 'ETF', 'NASDAQ', 'USD'),
    ('EURUSD', 'Euro/US Dollar', 'FOREX', 'IDEALPRO', 'USD'),
    ('GBPUSD', 'British Pound/US Dollar', 'FOREX', 'IDEALPRO', 'USD')
ON CONFLICT (symbol, exchange) DO NOTHING;