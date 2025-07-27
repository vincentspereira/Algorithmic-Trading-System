-- Production Database Schema Initialization
-- This script creates the necessary tables for the trading system.

CREATE TABLE IF NOT EXISTS trading_strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    python_code TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_orders (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES trading_strategies(id),
    symbol VARCHAR(50) NOT NULL,
    order_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    price NUMERIC,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    trade_order_id INTEGER REFERENCES trade_orders(id),
    risk_level VARCHAR(50) NOT NULL,
    is_approved BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add any other necessary tables here.