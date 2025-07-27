import { create } from 'zustand';
import { Portfolio, Order, MarketData } from '../types/api';
import { getPortfolio, getOrderHistory, submitOrder, getMarketData } from '../lib/api';

interface AppState {
  portfolio: Portfolio | null;
  orders: Order[];
  marketData: { [symbol: string]: MarketData[] };
  isLoading: boolean;
  error: Error | null;
  actions: {
    fetchPortfolio: () => Promise<void>;
    fetchOrderHistory: () => Promise<void>;
    submitOrder: (orderData: Omit<Order, 'id' | 'timestamp' | 'status'>) => Promise<void>;
    fetchMarketData: (symbol: string) => Promise<void>;
  };
}

export const useStore = create<AppState>((set, get) => ({
  portfolio: null,
  orders: [],
  marketData: {},
  isLoading: false,
  error: null,
  actions: {
    fetchPortfolio: async () => {
      try {
        set({ isLoading: true, error: null });
        const portfolio = await getPortfolio();
        set({ portfolio, isLoading: false });
      } catch (error) {
        set({ error: error instanceof Error ? error : new Error('Failed to fetch portfolio'), isLoading: false });
      }
    },
    fetchOrderHistory: async () => {
      try {
        set({ isLoading: true, error: null });
        const orders = await getOrderHistory();
        set({ orders, isLoading: false });
      } catch (error) {
        set({ error: error instanceof Error ? error : new Error('Failed to fetch order history'), isLoading: false });
      }
    },
    submitOrder: async (orderData) => {
        try {
            set({ isLoading: true, error: null});
            const newOrder = await submitOrder(orderData);
            set((state) => ({
                orders: [newOrder, ...state.orders],
                isLoading: false,
            }));
        } catch (error) {
            set({ error: error instanceof Error ? error : new Error('Failed to submit order'), isLoading: false});
            throw error;
        }
    },
    fetchMarketData: async (symbol) => {
        try {
            set({ isLoading: true, error: null });
            const data = await getMarketData(symbol);
            set((state) => ({
                marketData: {
                    ...state.marketData,
                    [symbol]: [...(state.marketData[symbol] || []), data],
                },
                isLoading: false,
            }));
        } catch (error) {
            set({ error: error instanceof Error ? error : new Error('Failed to fetch market data'), isLoading: false});
        }
    },
  },
}));