-- PostgreSQL initialization script for Algorithmic Trading System
-- This script sets up the database schema and extensions for Phase 1

-- Create the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas for different data types
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS ai_embeddings;
CREATE SCHEMA IF NOT EXISTS risk_management;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path to include all schemas
ALTER DATABASE trading_system SET search_path TO trading, market_data, ai_embeddings, risk_management, audit, public;

-- Create basic tables for Phase 1

-- Market data tables
CREATE TABLE IF NOT EXISTS market_data.instruments (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255),
    asset_class VARCHAR(50) NOT NULL,
    exchange VARCHAR(100),
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_data.price_data (
    id BIGSERIAL PRIMARY KEY,
    instrument_id INTEGER REFERENCES market_data.instruments(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price DECIMAL(20,8),
    high_price DECIMAL(20,8),
    low_price DECIMAL(20,8),
    close_price DECIMAL(20,8),
    volume BIGINT,
    vwap DECIMAL(20,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI embeddings table for vector search
CREATE TABLE IF NOT EXISTS ai_embeddings.document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) NOT NULL,
    document_type VARCHAR(100),
    content_hash VARCHAR(64),
    embedding vector(1536), -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trading tables
CREATE TABLE IF NOT EXISTS trading.strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    strategy_type VARCHAR(100),
    parameters JSONB,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trading.backtests (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES trading.strategies(id),
    name VARCHAR(255),
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(20,2),
    final_capital DECIMAL(20,2),
    total_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    parameters JSONB,
    results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Risk management tables
CREATE TABLE IF NOT EXISTS risk_management.risk_limits (
    id SERIAL PRIMARY KEY,
    limit_type VARCHAR(100) NOT NULL,
    limit_value DECIMAL(20,8),
    currency VARCHAR(10) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail table for compliance
CREATE TABLE IF NOT EXISTS audit.system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address INET,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_price_data_instrument_timestamp ON market_data.price_data(instrument_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON market_data.price_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON ai_embeddings.document_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON audit.system_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON audit.system_events(event_type);

-- Insert some initial data
INSERT INTO market_data.instruments (symbol, name, asset_class, exchange, currency) VALUES
    ('AAPL', 'Apple Inc.', 'EQUITY', 'NASDAQ', 'USD'),
    ('GOOGL', 'Alphabet Inc.', 'EQUITY', 'NASDAQ', 'USD'),
    ('MSFT', 'Microsoft Corporation', 'EQUITY', 'NASDAQ', 'USD'),
    ('TSLA', 'Tesla Inc.', 'EQUITY', 'NASDAQ', 'USD'),
    ('SPY', 'SPDR S&P 500 ETF Trust', 'ETF', 'NYSE', 'USD')
ON CONFLICT (symbol) DO NOTHING;

INSERT INTO risk_management.risk_limits (limit_type, limit_value, currency) VALUES
    ('MAX_POSITION_SIZE', 100000.00, 'USD'),
    ('MAX_DAILY_LOSS', 10000.00, 'USD'),
    ('MAX_LEVERAGE', 2.0, 'USD'),
    ('MAX_CONCENTRATION', 0.20, 'USD')
ON CONFLICT DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_instruments_updated_at BEFORE UPDATE ON market_data.instruments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON trading.strategies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_risk_limits_updated_at BEFORE UPDATE ON risk_management.risk_limits FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed for your security requirements)
GRANT USAGE ON SCHEMA trading, market_data, ai_embeddings, risk_management, audit TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading, market_data, ai_embeddings, risk_management, audit TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trading, market_data, ai_embeddings, risk_management, audit TO PUBLIC;

-- Log successful initialization
INSERT INTO audit.system_events (event_type, event_data) VALUES 
    ('DATABASE_INITIALIZED', '{"message": "PostgreSQL database initialized successfully with pgvector extension", "phase": "1"}');

COMMIT;