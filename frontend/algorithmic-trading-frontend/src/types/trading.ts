export interface Order {
  id: string;
  symbol: string;
  quantity: number;
  orderType: 'Market' | 'Limit';
  price?: number;
  status: 'Open' | 'Filled' | 'Cancelled';
  timestamp: string;
}

export interface Trade {
  id: string;
  symbol: string;
  quantity: number;
  price: number;
  side: 'Buy' | 'Sell';
  timestamp: string;
}

export interface MarketData {
  date: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Portfolio {
  cash: number;
  positions: Position[];
  totalValue: number;
}

export interface Position {
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentValue: number;
}