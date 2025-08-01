/**
 * Nautilus Trader JavaScript/TypeScript SDK
 * 
 * A comprehensive SDK for interacting with the Nautilus Trader Engine.
 * Provides easy access to REST APIs, GraphQL, WebSocket connections, and webhook management.
 */

export { NautilusTraderClient } from './client';
export * from './models';
export * from './exceptions';
export * from './types';
export * from './utils';

// Re-export commonly used types
export type {
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

export type {
  OrderSide,
  OrderType,
  OrderStatus,
  TimeInForce,
  PositionSide,
  StrategyStatus
} from './types';

// Version
export const VERSION = '1.0.0';