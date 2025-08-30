/**
 * Trading Types for Phase 1 Dashboard
 * 
 * Author: Vincent S. Pereira
 * Version: 1.0.0
 */

export type TradingMode = 'paper' | 'live';

export interface ConnectionStatus {
  isConnected: boolean;
  serverVersion?: string;
  accountId?: string;
  marketDataFarms?: string[];
  lastUpdate?: string;
}

export interface MarketData {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  volume: number;
  change: number;
  changePercent: number;
  timestamp: string;
}

export interface TradingSignal {
  id: string;
  symbol: string;
  signal: 'BUY' | 'SELL';
  price: number;
  strength: number;
  timestamp: string;
  indicators: {
    sma_20?: number;
    sma_50?: number;
    rsi?: number;
    macd?: number;
  };
}

export interface Order {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL';
  quantity: number;
  orderType: 'MARKET' | 'LIMIT';
  price?: number;
  status: 'PENDING' | 'SUBMITTED' | 'FILLED' | 'CANCELLED';
  timestamp: string;
  orderId?: number;
}

export interface Position {
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  marketValue: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  timestamp: string;
}

export interface AccountInfo {
  accountId: string;
  totalCashValue: number;
  netLiquidation: number;
  equity: number;
  availableFunds: number;
  buyingPower: number;
  dayTradesRemaining: number;
  currency: string;
  timestamp: string;
}

export interface PipelineMetrics {
  dataIngestionLatency: number;
  algorithmExecutionTime: number;
  orderRoutingLatency: number;
  endToEndLatency: number;
  signalsPerSecond: number;
  ordersPerSecond: number;
  eventsPerSecond: number;
  successRate: number;
  timestamp: string;
}

export interface DashboardData {
  connectionStatus: ConnectionStatus;
  marketData: MarketData[];
  signals: TradingSignal[];
  orders: Order[];
  positions: Position[];
  accountInfo: AccountInfo;
  pipelineMetrics: PipelineMetrics;
}