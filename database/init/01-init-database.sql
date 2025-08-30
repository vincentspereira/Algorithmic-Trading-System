-- Create the trading_system database
CREATE DATABASE IF NOT EXISTS trading_system;

-- Create the user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_user') THEN
        CREATE USER trading_user WITH PASSWORD 'trading_user_password_2024';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_system TO trading_user;

-- Connect to the trading_system database
\c trading_system;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant schema permissions
GRANT ALL ON SCHEMA trading TO trading_user;
GRANT ALL ON SCHEMA audit TO trading_user;
GRANT ALL ON SCHEMA analytics TO trading_user;

-- Users table
CREATE TABLE IF NOT EXISTS trading.users (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    roles TEXT[] DEFAULT '{}',
    permissions TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    failed_login_attempts INTEGER DEFAULT 0,
    account_locked BOOLEAN DEFAULT FALSE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}'::jsonb,
    risk_score DECIMAL(3,2) DEFAULT 0.0
);

-- Trading accounts table
CREATE TABLE IF NOT EXISTS trading.accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES trading.users(user_id),
    broker VARCHAR(20) NOT NULL,
    account_type VARCHAR(20) DEFAULT 'paper',
    balance DECIMAL(15,2) DEFAULT 0.00,
    buying_power DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Orders table
CREATE TABLE IF NOT EXISTS trading.orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES trading.users(user_id),
    account_id VARCHAR(50) REFERENCES trading.accounts(account_id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    quantity DECIMAL(15,6) NOT NULL,
    price DECIMAL(15,6),
    stop_price DECIMAL(15,6),
    status VARCHAR(20) DEFAULT 'pending',
    filled_quantity DECIMAL(15,6) DEFAULT 0,
    avg_fill_price DECIMAL(15,6),
    commission DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Strategies table with vector embeddings
CREATE TABLE IF NOT EXISTS trading.strategies (
    id SERIAL PRIMARY KEY,
    strategy_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES trading.users(user_id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    code TEXT,
    embedding vector(1536),
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1
);

-- Audit events table
CREATE TABLE IF NOT EXISTS audit.events (
    id SERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,
    session_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(200) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    outcome VARCHAR(20) NOT NULL,
    risk_score INTEGER DEFAULT 0,
    compliance_tags TEXT[] DEFAULT '{}',
    correlation_id UUID,
    service_name VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON trading.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON trading.users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON trading.users(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON trading.orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON trading.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON trading.orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON trading.orders(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON trading.strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_strategy_id ON trading.strategies(strategy_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit.events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_user_id ON audit.events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit.events(event_type);

-- Vector similarity index for strategies (using ivfflat)
CREATE INDEX IF NOT EXISTS idx_strategies_embedding ON trading.strategies 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON trading.users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON trading.accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON trading.orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON trading.strategies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user
INSERT INTO trading.users (username, email, password_hash, roles, permissions, is_active, mfa_enabled)
VALUES (
    'admin',
    'admin@trading-system.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj.UHR7aBkQa', -- 'admin123'
    ARRAY['admin', 'trader'],
    ARRAY['admin.access', 'trade.execute', 'view_dashboard', 'manage_users'],
    true,
    false
) ON CONFLICT (username) DO NOTHING;

-- Insert test trader user
INSERT INTO trading.users (username, email, password_hash, roles, permissions, is_active, mfa_enabled)
VALUES (
    'trader',
    'trader@trading-system.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj.UHR7aBkQa', -- 'trader123'
    ARRAY['trader'],
    ARRAY['trade.execute', 'view_dashboard', 'view_portfolio'],
    true,
    false
) ON CONFLICT (username) DO NOTHING;