/**
 * Nautilus Trader JavaScript/TypeScript SDK Client
 * 
 * Main client class for interacting with the Nautilus Trader Engine.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import WebSocket from 'ws';
import { EventEmitter } from 'events';

import {
  Order,
  Position,
  Trade,
  Portfolio,
  MarketData,
  Strategy,
  Backtest,
  RiskMetrics,
  Analytics
} from './models';

import {
  OrderSide,
  OrderType,
  OrderStatus,
  TimeInForce,
  ClientConfig,
  CreateOrderRequest,
  WebSocketMessage,
  SubscriptionCallback
} from './types';

import {
  NautilusTraderError,
  APIError,
  NetworkError,
  ValidationError,
  WebSocketError
} from './exceptions';

import { validateOrderParams, formatSymbol, createHMACSignature } from './utils';

/**
 * Main client for Nautilus Trader Engine
 */
export class NautilusTraderClient extends EventEmitter {
  private httpClient: AxiosInstance;
  private wsClient?: WebSocket;
  private config: Required<ClientConfig>;
  private subscriptions: Map<string, SubscriptionCallback> = new Map();
  private isConnected = false;

  constructor(config: ClientConfig = {}) {
    super();

    this.config = {
      baseUrl: config.baseUrl || 'http://localhost:8000',
      apiKey: config.apiKey || '',
      secret: config.secret || '',
      timeout: config.timeout || 30000,
      maxRetries: config.maxRetries || 3,
      enableLogging: config.enableLogging !== false
    };

    // Initialize HTTP client
    this.httpClient = axios.create({
      baseURL: `${this.config.baseUrl}/api/v1`,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'nautilus-trader-sdk-js/1.0.0',
        ...(this.config.apiKey && { 'X-API-Key': this.config.apiKey })
      }
    });

    // Add response interceptor for error handling
    this.httpClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          const { status, data } = error.response;
          const message = data?.message || data?.error || `HTTP ${status}`;
          throw new APIError(message, status, data);
        } else if (error.request) {
          throw new NetworkError('Network error: No response received');
        } else {
          throw new NetworkError(`Request error: ${error.message}`);
        }
      }
    );

    if (this.config.enableLogging) {
      console.log(`Nautilus Trader SDK initialized for ${this.config.baseUrl}`);
    }
  }

  /**
   * Check API health status
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await this.httpClient.get('/health');
      return response.data;
    } catch (error) {
      throw new APIError('Health check failed', 0, { originalError: error });
    }
  }

  // Order Management

  /**
   * Create a new order
   */
  async createOrder(request: CreateOrderRequest): Promise<Order> {
    validateOrderParams(request);

    const response = await this.httpClient.post('/orders', request);
    return new Order(response.data.data);
  }

  /**
   * Get order by ID
   */
  async getOrder(orderId: string): Promise<Order> {
    const response = await this.httpClient.get(`/orders/${orderId}`);
    return new Order(response.data.data);
  }

  /**
   * Get orders with optional filtering
   */
  async getOrders(params: {
    symbol?: string;
    status?: OrderStatus;
    limit?: number;
    offset?: number;
  } = {}): Promise<Order[]> {
    const response = await this.httpClient.get('/orders', { params });
    return response.data.data.map((orderData: any) => new Order(orderData));
  }

  /**
   * Cancel an order
   */
  async cancelOrder(orderId: string): Promise<boolean> {
    const response = await this.httpClient.delete(`/orders/${orderId}`);
    return response.data.success;
  }

  /**
   * Modify an existing order
   */
  async modifyOrder(
    orderId: string,
    updates: Partial<CreateOrderRequest>
  ): Promise<Order> {
    const response = await this.httpClient.put(`/orders/${orderId}`, updates);
    return new Order(response.data.data);
  }

  // Position Management

  /**
   * Get all positions
   */
  async getPositions(): Promise<Position[]> {
    const response = await this.httpClient.get('/positions');
    return response.data.data.map((posData: any) => new Position(posData));
  }

  /**
   * Get position for specific symbol
   */
  async getPosition(symbol: string): Promise<Position> {
    const response = await this.httpClient.get(`/positions/${formatSymbol(symbol)}`);
    return new Position(response.data.data);
  }

  /**
   * Close position (partially or fully)
   */
  async closePosition(symbol: string, quantity?: number): Promise<boolean> {
    const data = quantity ? { quantity } : {};
    const response = await this.httpClient.post(
      `/positions/${formatSymbol(symbol)}/close`,
      data
    );
    return response.data.success;
  }

  // Portfolio Management

  /**
   * Get portfolio summary
   */
  async getPortfolio(): Promise<Portfolio> {
    const response = await this.httpClient.get('/portfolio');
    return new Portfolio(response.data.data);
  }

  /**
   * Get account balance
   */
  async getAccountBalance(): Promise<Record<string, number>> {
    const response = await this.httpClient.get('/account/balance');
    return response.data.data;
  }

  // Market Data

  /**
   * Get current market data for symbol
   */
  async getMarketData(symbol: string): Promise<MarketData> {
    const response = await this.httpClient.get(`/market-data/${formatSymbol(symbol)}`);
    return new MarketData(response.data.data);
  }

  /**
   * Get historical market data
   */
  async getHistoricalData(params: {
    symbol: string;
    timeframe?: string;
    startDate?: Date;
    endDate?: Date;
    limit?: number;
  }): Promise<any[]> {
    const queryParams: any = {
      timeframe: params.timeframe || '1m',
      limit: params.limit || 1000
    };

    if (params.startDate) {
      queryParams.start_date = params.startDate.toISOString();
    }
    if (params.endDate) {
      queryParams.end_date = params.endDate.toISOString();
    }

    const response = await this.httpClient.get(
      `/market-data/${formatSymbol(params.symbol)}/historical`,
      { params: queryParams }
    );
    return response.data.data;
  }

  // Strategy Management

  /**
   * Get all strategies
   */
  async getStrategies(): Promise<Strategy[]> {
    const response = await this.httpClient.get('/strategies');
    return response.data.data.map((stratData: any) => new Strategy(stratData));
  }

  /**
   * Get strategy by ID
   */
  async getStrategy(strategyId: string): Promise<Strategy> {
    const response = await this.httpClient.get(`/strategies/${strategyId}`);
    return new Strategy(response.data.data);
  }

  /**
   * Create new strategy
   */
  async createStrategy(config: Record<string, any>): Promise<Strategy> {
    const response = await this.httpClient.post('/strategies', config);
    return new Strategy(response.data.data);
  }

  /**
   * Start strategy
   */
  async startStrategy(strategyId: string): Promise<boolean> {
    const response = await this.httpClient.post(`/strategies/${strategyId}/start`);
    return response.data.success;
  }

  /**
   * Stop strategy
   */
  async stopStrategy(strategyId: string): Promise<boolean> {
    const response = await this.httpClient.post(`/strategies/${strategyId}/stop`);
    return response.data.success;
  }

  // Backtesting

  /**
   * Run backtest
   */
  async runBacktest(config: Record<string, any>): Promise<Backtest> {
    const response = await this.httpClient.post('/backtests', config);
    return new Backtest(response.data.data);
  }

  /**
   * Get backtest results
   */
  async getBacktest(backtestId: string): Promise<Backtest> {
    const response = await this.httpClient.get(`/backtests/${backtestId}`);
    return new Backtest(response.data.data);
  }

  /**
   * Get backtest history
   */
  async getBacktests(limit: number = 50): Promise<Backtest[]> {
    const response = await this.httpClient.get('/backtests', {
      params: { limit }
    });
    return response.data.data.map((btData: any) => new Backtest(btData));
  }

  // Risk Management

  /**
   * Get current risk metrics
   */
  async getRiskMetrics(): Promise<RiskMetrics> {
    const response = await this.httpClient.get('/risk/metrics');
    return new RiskMetrics(response.data.data);
  }

  /**
   * Set risk limits
   */
  async setRiskLimits(limits: Record<string, any>): Promise<boolean> {
    const response = await this.httpClient.post('/risk/limits', limits);
    return response.data.success;
  }

  // Analytics

  /**
   * Get trading analytics
   */
  async getAnalytics(): Promise<Analytics> {
    const response = await this.httpClient.get('/analytics');
    return new Analytics(response.data.data);
  }

  /**
   * Get performance metrics
   */
  async getPerformanceMetrics(params: {
    startDate?: Date;
    endDate?: Date;
  } = {}): Promise<Record<string, any>> {
    const queryParams: any = {};
    if (params.startDate) {
      queryParams.start_date = params.startDate.toISOString();
    }
    if (params.endDate) {
      queryParams.end_date = params.endDate.toISOString();
    }

    const response = await this.httpClient.get('/analytics/performance', {
      params: queryParams
    });
    return response.data.data;
  }

  // WebSocket Methods

  /**
   * Connect to WebSocket
   */
  async connectWebSocket(): Promise<void> {
    if (this.isConnected) {
      return;
    }

    const wsUrl = this.config.baseUrl.replace('http', 'ws') + '/ws';
    const headers: Record<string, string> = {};

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    return new Promise((resolve, reject) => {
      this.wsClient = new WebSocket(wsUrl, { headers });

      this.wsClient.on('open', () => {
        this.isConnected = true;
        if (this.config.enableLogging) {
          console.log('WebSocket connected');
        }
        this.emit('connected');
        resolve();
      });

      this.wsClient.on('message', (data: WebSocket.Data) => {
        try {
          const message: WebSocketMessage = JSON.parse(data.toString());
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });

      this.wsClient.on('close', () => {
        this.isConnected = false;
        if (this.config.enableLogging) {
          console.log('WebSocket disconnected');
        }
        this.emit('disconnected');
      });

      this.wsClient.on('error', (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', new WebSocketError(`WebSocket error: ${error.message}`));
        reject(new WebSocketError(`Failed to connect: ${error.message}`));
      });
    });
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsClient) {
      this.wsClient.close();
      this.wsClient = undefined;
    }
    this.isConnected = false;
    this.subscriptions.clear();
  }

  /**
   * Subscribe to order updates
   */
  async subscribeToOrders(callback: (order: Order) => void): Promise<void> {
    await this.subscribe('order_update', (data) => {
      callback(new Order(data));
    });
  }

  /**
   * Subscribe to position updates
   */
  async subscribeToPositions(callback: (position: Position) => void): Promise<void> {
    await this.subscribe('position_update', (data) => {
      callback(new Position(data));
    });
  }

  /**
   * Subscribe to market data updates
   */
  async subscribeToMarketData(
    symbols: string[],
    callback: (marketData: MarketData) => void
  ): Promise<void> {
    await this.subscribe('market_data_update', (data) => {
      callback(new MarketData(data));
    }, { symbols });
  }

  /**
   * Subscribe to portfolio updates
   */
  async subscribeToPortfolio(callback: (portfolio: Portfolio) => void): Promise<void> {
    await this.subscribe('portfolio_update', (data) => {
      callback(new Portfolio(data));
    });
  }

  private async subscribe(
    type: string,
    callback: SubscriptionCallback,
    params?: Record<string, any>
  ): Promise<void> {
    if (!this.isConnected) {
      await this.connectWebSocket();
    }

    this.subscriptions.set(type, callback);

    const message = {
      action: 'subscribe',
      type,
      params: params || {}
    };

    this.wsClient?.send(JSON.stringify(message));
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    const callback = this.subscriptions.get(message.type);
    if (callback) {
      callback(message.data);
    }
  }

  // GraphQL Methods

  /**
   * Execute GraphQL query
   */
  async graphqlQuery(
    query: string,
    variables?: Record<string, any>
  ): Promise<any> {
    const response = await this.httpClient.post('/graphql', {
      query,
      variables: variables || {}
    });

    if (response.data.errors) {
      throw new APIError('GraphQL query failed', 400, response.data.errors);
    }

    return response.data.data;
  }

  /**
   * Execute GraphQL mutation
   */
  async graphqlMutation(
    mutation: string,
    variables?: Record<string, any>
  ): Promise<any> {
    return this.graphqlQuery(mutation, variables);
  }

  // Webhook Management

  /**
   * Create webhook endpoint
   */
  async createWebhook(params: {
    url: string;
    events: string[];
    name: string;
    secret?: string;
    securityType?: string;
  }): Promise<string> {
    const response = await this.httpClient.post('/webhooks', params);
    return response.data.data.id;
  }

  /**
   * Get all webhook endpoints
   */
  async getWebhooks(): Promise<any[]> {
    const response = await this.httpClient.get('/webhooks');
    return response.data.data;
  }

  /**
   * Delete webhook endpoint
   */
  async deleteWebhook(webhookId: string): Promise<boolean> {
    const response = await this.httpClient.delete(`/webhooks/${webhookId}`);
    return response.status === 200;
  }

  /**
   * Test webhook endpoint
   */
  async testWebhook(webhookId: string, testData?: Record<string, any>): Promise<boolean> {
    const response = await this.httpClient.post(`/webhooks/${webhookId}/test`, {
      test_data: testData
    });
    return response.status === 200;
  }

  // Utility Methods

  /**
   * Get server time
   */
  async getServerTime(): Promise<Date> {
    const response = await this.httpClient.get('/time');
    return new Date(response.data.timestamp);
  }

  /**
   * Validate order parameters
   */
  validateOrder(request: CreateOrderRequest): boolean {
    return validateOrderParams(request);
  }

  /**
   * Format symbol
   */
  formatSymbol(symbol: string): string {
    return formatSymbol(symbol);
  }
}