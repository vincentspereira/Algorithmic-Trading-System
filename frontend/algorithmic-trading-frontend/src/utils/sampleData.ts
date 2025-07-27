import { subDays } from 'date-fns';
import { MarketData, Order, Trade } from '@/types/trading';

export const generateSampleMarketData = (count = 100): MarketData[] => {
  const data: MarketData[] = [];
  let lastClose = 100;
  for (let i = 0; i < count; i++) {
    const date = subDays(new Date(), count - i - 1);
    const open = lastClose;
    const close = open + (Math.random() - 0.5) * 5;
    const high = Math.max(open, close) + Math.random() * 2;
    const low = Math.min(open, close) - Math.random() * 2;
    const volume = Math.random() * 1000000;
    data.push({ date, open, high, low, close, volume });
    lastClose = close;
  }
  return data;
};

export const sampleOrders: Order[] = [
  { id: '1', symbol: 'AAPL', quantity: 100, orderType: 'Limit', price: 150.0, status: 'Filled', timestamp: new Date().toISOString() },
  { id: '2', symbol: 'GOOG', quantity: 50, orderType: 'Market', status: 'Open', timestamp: new Date().toISOString() },
  { id: '3', symbol: 'TSLA', quantity: 200, orderType: 'Limit', price: 300.0, status: 'Cancelled', timestamp: new Date().toISOString() },
];

export const sampleTrades: Trade[] = [
  { id: '1', symbol: 'AAPL', quantity: 100, price: 150.0, side: 'Buy', timestamp: new Date().toISOString() },
  { id: '2', symbol: 'MSFT', quantity: 75, price: 250.0, side: 'Sell', timestamp: new Date().toISOString() },
];