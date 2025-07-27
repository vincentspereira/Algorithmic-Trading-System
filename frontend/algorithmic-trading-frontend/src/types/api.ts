export interface PortfolioPosition {
  symbol: string;
  quantity: number;
  average_price: number;
  market_value: number;
}

export interface Portfolio {
  total_value: number;
  cash: number;
  positions: PortfolioPosition[];
}

export interface Order {
  id: string;
  symbol: string;
  quantity: number;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  limit_price?: number;
  timestamp: string;
  status: 'open' | 'filled' | 'cancelled';
}

export interface MarketData {
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
}

export interface RiskMetric {
  name: string;
  value: number;
  description: string;
}

export interface RiskSnapshot {
  timestamp: string;
  metrics: RiskMetric[];
}