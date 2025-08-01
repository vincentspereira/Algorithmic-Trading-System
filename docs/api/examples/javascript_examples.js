/**
 * JavaScript/Node.js Examples for Algorithmic Trading System API
 * 
 * This file contains comprehensive examples for interacting with the
 * Algorithmic Trading System API using JavaScript/Node.js.
 */

const axios = require('axios');
const WebSocket = require('ws');

class TradingSystemClient {
    constructor(baseUrl = 'https://api.trading-system.com', sandbox = false) {
        this.baseUrl = sandbox ? 'https://sandbox-api.trading-system.com' : baseUrl;
        this.accessToken = null;
        this.refreshToken = null;
        
        // Create axios instance with default config
        this.api = axios.create({
            baseURL: this.baseUrl,
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'TradingSystem-JS-Client/1.0'
            }
        });
        
        // Add request interceptor for authentication
        this.api.interceptors.request.use((config) => {
            if (this.accessToken) {
                config.headers.Authorization = `Bearer ${this.accessToken}`;
            }
            return config;
        });
        
        // Add response interceptor for error handling
        this.api.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401 && this.refreshToken) {
                    try {
                        await this.refreshAccessToken();
                        // Retry the original request
                        return this.api.request(error.config);
                    } catch (refreshError) {
                        console.error('Token refresh failed:', refreshError);
                        throw error;
                    }
                }
                throw error;
            }
        );
    }
    
    /**
     * Authenticate with the API
     */
    async login(username, password, rememberMe = false) {
        try {
            const response = await this.api.post('/auth/login', {
                username,
                password,
                remember_me: rememberMe
            });
            
            const { access_token, refresh_token, expires_in } = response.data;
            this.accessToken = access_token;
            this.refreshToken = refresh_token;
            
            console.log(`Login successful. Token expires in ${expires_in} seconds`);
            return response.data;
        } catch (error) {
            console.error('Login failed:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Refresh access token
     */
    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }
        
        try {
            const response = await this.api.post('/auth/refresh', {
                refresh_token: this.refreshToken
            });
            
            const { access_token, refresh_token } = response.data;
            this.accessToken = access_token;
            if (refresh_token) {
                this.refreshToken = refresh_token;
            }
            
            console.log('Token refreshed successfully');
            return response.data;
        } catch (error) {
            console.error('Token refresh failed:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Strategy Management Methods
     */
    
    async getStrategies(options = {}) {
        const params = {
            page: options.page || 1,
            limit: options.limit || 20,
            ...(options.status && { status: options.status }),
            ...(options.asset_class && { asset_class: options.asset_class })
        };
        
        try {
            const response = await this.api.get('/strategies', { params });
            return response.data;
        } catch (error) {
            console.error('Failed to get strategies:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async createStrategy(strategyData) {
        try {
            const response = await this.api.post('/strategies', strategyData);
            console.log(`Strategy created with ID: ${response.data.id}`);
            return response.data;
        } catch (error) {
            console.error('Failed to create strategy:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async getStrategy(strategyId) {
        try {
            const response = await this.api.get(`/strategies/${strategyId}`);
            return response.data;
        } catch (error) {
            console.error('Failed to get strategy:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async updateStrategy(strategyId, updateData) {
        try {
            const response = await this.api.put(`/strategies/${strategyId}`, updateData);
            console.log(`Strategy ${strategyId} updated successfully`);
            return response.data;
        } catch (error) {
            console.error('Failed to update strategy:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async deleteStrategy(strategyId) {
        try {
            await this.api.delete(`/strategies/${strategyId}`);
            console.log(`Strategy ${strategyId} deleted successfully`);
        } catch (error) {
            console.error('Failed to delete strategy:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Market Data Methods
     */
    
    async getQuote(symbol, fields = null) {
        const params = {};
        if (fields) {
            params.fields = Array.isArray(fields) ? fields.join(',') : fields;
        }
        
        try {
            const response = await this.api.get(`/market-data/quotes/${symbol}`, { params });
            return response.data;
        } catch (error) {
            console.error('Failed to get quote:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async getHistoricalData(symbol, startDate, endDate, interval = '1d') {
        const params = {
            start_date: startDate,
            end_date: endDate,
            interval
        };
        
        try {
            const response = await this.api.get(`/market-data/historical/${symbol}`, { params });
            return response.data;
        } catch (error) {
            console.error('Failed to get historical data:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Backtesting Methods
     */
    
    async runBacktest(backtestData) {
        try {
            const response = await this.api.post('/backtesting/run', backtestData);
            console.log(`Backtest started with ID: ${response.data.backtest_id}`);
            return response.data;
        } catch (error) {
            console.error('Failed to run backtest:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async getBacktestResults(backtestId) {
        try {
            const response = await this.api.get(`/backtesting/${backtestId}`);
            return response.data;
        } catch (error) {
            console.error('Failed to get backtest results:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * Trading Methods
     */
    
    async getOrders(options = {}) {
        const params = {
            ...(options.status && { status: options.status }),
            ...(options.symbol && { symbol: options.symbol })
        };
        
        try {
            const response = await this.api.get('/orders', { params });
            return response.data;
        } catch (error) {
            console.error('Failed to get orders:', error.response?.data || error.message);
            throw error;
        }
    }
    
    async placeOrder(orderData) {
        try {
            const response = await this.api.post('/orders', orderData);
            console.log(`Order placed with ID: ${response.data.id}`);
            return response.data;
        } catch (error) {
            console.error('Failed to place order:', error.response?.data || error.message);
            throw error;
        }
    }
    
    /**
     * WebSocket Methods
     */
    
    createMarketDataStream() {
        const wsUrl = this.baseUrl.replace('https://', 'wss://') + '/ws/market-data';
        const ws = new WebSocket(wsUrl);
        
        ws.on('open', () => {
            console.log('WebSocket connected');
            
            // Authenticate
            if (this.accessToken) {
                ws.send(JSON.stringify({
                    action: 'authenticate',
                    token: this.accessToken
                }));
            }
        });
        
        ws.on('message', (data) => {
            try {
                const message = JSON.parse(data.toString());
                console.log('WebSocket message:', message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        });
        
        ws.on('error', (error) => {
            console.error('WebSocket error:', error);
        });
        
        ws.on('close', () => {
            console.log('WebSocket disconnected');
        });
        
        // Add helper methods to the WebSocket instance
        ws.subscribe = (symbols, dataTypes = ['quotes']) => {
            ws.send(JSON.stringify({
                action: 'subscribe',
                symbols: Array.isArray(symbols) ? symbols : [symbols],
                data_types: dataTypes
            }));
        };
        
        ws.unsubscribe = (symbols) => {
            ws.send(JSON.stringify({
                action: 'unsubscribe',
                symbols: Array.isArray(symbols) ? symbols : [symbols]
            }));
        };
        
        return ws;
    }
}

/**
 * Example Usage Functions
 */

async function basicExample() {
    console.log('=== Basic API Usage Example ===');
    
    const client = new TradingSystemClient('https://api.trading-system.com', true); // sandbox
    
    try {
        // Login
        await client.login('demo@example.com', 'demo_password');
        
        // Get strategies
        const strategies = await client.getStrategies({ status: 'active' });
        console.log(`Found ${strategies.strategies.length} active strategies`);
        
        // Get market data
        const quote = await client.getQuote('AAPL');
        console.log(`AAPL: $${quote.last} (${quote.change_percent > 0 ? '+' : ''}${quote.change_percent.toFixed(2)}%)`);
        
        // Get historical data
        const endDate = new Date().toISOString().split('T')[0];
        const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        
        const historical = await client.getHistoricalData('AAPL', startDate, endDate);
        console.log(`Retrieved ${historical.data.length} historical data points`);
        
    } catch (error) {
        console.error('Example failed:', error.message);
    }
}

async function strategyManagementExample() {
    console.log('=== Strategy Management Example ===');
    
    const client = new TradingSystemClient('https://api.trading-system.com', true);
    
    try {
        await client.login('demo@example.com', 'demo_password');
        
        // Create a new strategy
        const newStrategy = await client.createStrategy({
            name: `Momentum Strategy ${Date.now()}`,
            description: 'A momentum-based trading strategy',
            asset_class: 'stocks',
            strategy_type: 'momentum',
            parameters: {
                lookback_period: 20,
                threshold: 0.02,
                stop_loss: 0.05,
                take_profit: 0.10
            },
            risk_management: {
                max_position_size: 0.05,
                max_daily_loss: 0.02
            }
        });
        
        console.log(`Created strategy: ${newStrategy.name} (ID: ${newStrategy.id})`);
        
        // Update the strategy
        const updatedStrategy = await client.updateStrategy(newStrategy.id, {
            description: 'Updated momentum strategy with enhanced parameters',
            status: 'active'
        });
        
        console.log(`Updated strategy status: ${updatedStrategy.status}`);
        
        // Get strategy details
        const strategy = await client.getStrategy(newStrategy.id);
        console.log(`Strategy details: ${JSON.stringify(strategy, null, 2)}`);
        
        // Clean up - delete the strategy
        await client.deleteStrategy(newStrategy.id);
        console.log('Strategy deleted successfully');
        
    } catch (error) {
        console.error('Strategy management example failed:', error.message);
    }
}

async function backtestingExample() {
    console.log('=== Backtesting Example ===');
    
    const client = new TradingSystemClient('https://api.trading-system.com', true);
    
    try {
        await client.login('demo@example.com', 'demo_password');
        
        // First, create a strategy for backtesting
        const strategy = await client.createStrategy({
            name: `Backtest Strategy ${Date.now()}`,
            description: 'Strategy for backtesting example',
            asset_class: 'stocks',
            strategy_type: 'momentum',
            parameters: {
                lookback_period: 20,
                threshold: 0.02
            }
        });
        
        // Run backtest
        const backtestRequest = {
            strategy_id: strategy.id,
            start_date: '2023-01-01',
            end_date: '2023-12-31',
            initial_capital: 100000,
            benchmark: 'SPY',
            parameters: {
                commission: 0.001,
                slippage: 0.0005
            }
        };
        
        const backtestResponse = await client.runBacktest(backtestRequest);
        console.log(`Backtest started: ${backtestResponse.backtest_id}`);
        
        // Poll for results (in a real application, you might use webhooks)
        let results;
        let attempts = 0;
        const maxAttempts = 10;
        
        do {
            await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
            results = await client.getBacktestResults(backtestResponse.backtest_id);
            attempts++;
            
            console.log(`Backtest status: ${results.status}`);
            
        } while (results.status === 'running' && attempts < maxAttempts);
        
        if (results.status === 'completed') {
            console.log('Backtest Results:');
            console.log(`Total Return: ${results.performance.total_return}%`);
            console.log(`Sharpe Ratio: ${results.performance.sharpe_ratio}`);
            console.log(`Max Drawdown: ${results.performance.max_drawdown}%`);
            console.log(`Win Rate: ${(results.performance.win_rate * 100).toFixed(2)}%`);
        }
        
        // Clean up
        await client.deleteStrategy(strategy.id);
        
    } catch (error) {
        console.error('Backtesting example failed:', error.message);
    }
}

async function webSocketExample() {
    console.log('=== WebSocket Real-time Data Example ===');
    
    const client = new TradingSystemClient('https://api.trading-system.com', true);
    
    try {
        await client.login('demo@example.com', 'demo_password');
        
        const ws = client.createMarketDataStream();
        
        ws.on('open', () => {
            console.log('Connected to market data stream');
            
            // Subscribe to symbols
            ws.subscribe(['AAPL', 'GOOGL', 'MSFT'], ['quotes', 'trades']);
        });
        
        ws.on('message', (data) => {
            const message = JSON.parse(data.toString());
            
            if (message.type === 'quote') {
                console.log(`${message.symbol}: $${message.last} (${message.change_percent > 0 ? '+' : ''}${message.change_percent.toFixed(2)}%)`);
            } else if (message.type === 'trade') {
                console.log(`Trade: ${message.symbol} - ${message.quantity} @ $${message.price}`);
            }
        });
        
        // Keep connection alive for 30 seconds
        setTimeout(() => {
            console.log('Closing WebSocket connection');
            ws.close();
        }, 30000);
        
    } catch (error) {
        console.error('WebSocket example failed:', error.message);
    }
}

async function errorHandlingExample() {
    console.log('=== Error Handling Example ===');
    
    const client = new TradingSystemClient('https://api.trading-system.com', true);
    
    try {
        // Try to access protected endpoint without authentication
        await client.getStrategies();
    } catch (error) {
        if (error.response?.status === 401) {
            console.log('✓ Correctly handled 401 Unauthorized error');
        }
    }
    
    try {
        // Login with invalid credentials
        await client.login('invalid@example.com', 'wrong_password');
    } catch (error) {
        if (error.response?.status === 401) {
            console.log('✓ Correctly handled login failure');
        }
    }
    
    try {
        await client.login('demo@example.com', 'demo_password');
        
        // Try to get non-existent strategy
        await client.getStrategy('non-existent-id');
    } catch (error) {
        if (error.response?.status === 404) {
            console.log('✓ Correctly handled 404 Not Found error');
        }
    }
    
    try {
        // Try to create strategy with invalid data
        await client.createStrategy({
            name: '', // Invalid: empty name
            asset_class: 'invalid_class' // Invalid asset class
        });
    } catch (error) {
        if (error.response?.status === 422) {
            console.log('✓ Correctly handled 422 Validation error');
            console.log('Validation errors:', error.response.data.error.details);
        }
    }
}

/**
 * Utility Functions
 */

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatPercentage(value) {
    return `${(value * 100).toFixed(2)}%`;
}

function calculatePerformanceMetrics(trades) {
    const totalTrades = trades.length;
    const winningTrades = trades.filter(trade => trade.pnl > 0);
    const losingTrades = trades.filter(trade => trade.pnl < 0);
    
    const totalPnL = trades.reduce((sum, trade) => sum + trade.pnl, 0);
    const winRate = winningTrades.length / totalTrades;
    
    const avgWin = winningTrades.length > 0 
        ? winningTrades.reduce((sum, trade) => sum + trade.pnl, 0) / winningTrades.length 
        : 0;
    
    const avgLoss = losingTrades.length > 0 
        ? losingTrades.reduce((sum, trade) => sum + trade.pnl, 0) / losingTrades.length 
        : 0;
    
    const profitFactor = avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : Infinity;
    
    return {
        totalTrades,
        winningTrades: winningTrades.length,
        losingTrades: losingTrades.length,
        totalPnL,
        winRate,
        avgWin,
        avgLoss,
        profitFactor
    };
}

/**
 * Main execution
 */
async function main() {
    console.log('🚀 JavaScript API Examples for Algorithmic Trading System');
    console.log('=' * 60);
    
    // Run examples
    await basicExample();
    await strategyManagementExample();
    await backtestingExample();
    await webSocketExample();
    await errorHandlingExample();
    
    console.log('\n✅ All examples completed!');
}

// Export for use as module
module.exports = {
    TradingSystemClient,
    formatCurrency,
    formatPercentage,
    calculatePerformanceMetrics
};

// Run examples if this file is executed directly
if (require.main === module) {
    main().catch(console.error);
}