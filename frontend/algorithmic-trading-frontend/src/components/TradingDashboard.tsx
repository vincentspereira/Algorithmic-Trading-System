"use client";

import { useState, useEffect } from 'react';
import { TradingMode, DashboardData, MarketData, TradingSignal, Order, Position } from '@/types/trading';
import MarketDataGrid from './MarketDataGrid';
import SignalsPanel from './SignalsPanel';
import { OrdersPanel, PositionsPanel, AccountSummary, PipelineMetrics } from './DashboardComponents';

interface TradingDashboardProps {
  tradingMode: TradingMode;
  setIsConnected: (connected: boolean) => void;
}

export default function TradingDashboard({ tradingMode, setIsConnected }: TradingDashboardProps) {
  const [dashboardData, setDashboardData] = useState<DashboardData>({
    connectionStatus: {
      isConnected: false
    },
    marketData: [],
    signals: [],
    orders: [],
    positions: [],
    accountInfo: {
      accountId: 'DUK221396',
      totalCashValue: 100000,
      netLiquidation: 100000,
      equity: 100000,
      availableFunds: 100000,
      buyingPower: 400000,
      dayTradesRemaining: -1,
      currency: 'USD',
      timestamp: new Date().toISOString()
    },
    pipelineMetrics: {
      dataIngestionLatency: 0,
      algorithmExecutionTime: 0,
      orderRoutingLatency: 0,
      endToEndLatency: 0,
      signalsPerSecond: 0,
      ordersPerSecond: 0,
      eventsPerSecond: 0,
      successRate: 100,
      timestamp: new Date().toISOString()
    }
  });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulate connection to IBKR
  useEffect(() => {
    const connectToIBKR = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Simulate connection delay
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Simulate successful connection
        const connectionSuccess = Math.random() > 0.1; // 90% success rate
        
        if (connectionSuccess) {
          setIsConnected(true);
          setDashboardData(prev => ({
            ...prev,
            connectionStatus: {
              isConnected: true,
              serverVersion: '176',
              accountId: 'DUK221396',
              marketDataFarms: ['usfarm.nj', 'hfarm', 'usfuture', 'cashfarm'],
              lastUpdate: new Date().toISOString()
            }
          }));
        } else {
          throw new Error('Failed to connect to IBKR Gateway');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Connection failed');
        setIsConnected(false);
      } finally {
        setIsLoading(false);
      }
    };

    connectToIBKR();
  }, [tradingMode, setIsConnected]);

  // Simulate real-time data updates
  useEffect(() => {
    if (!dashboardData.connectionStatus.isConnected) return;

    const interval = setInterval(() => {
      // Update market data
      const symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'];
      const newMarketData: MarketData[] = symbols.map(symbol => {
        const basePrice = {
          'AAPL': 232.56,
          'MSFT': 415.23,
          'GOOGL': 174.32,
          'TSLA': 248.87,
          'AMZN': 186.45
        }[symbol] || 100;
        
        const change = (Math.random() - 0.5) * 2; // -1 to +1
        const price = basePrice + change;
        const changePercent = (change / basePrice) * 100;
        
        return {
          symbol,
          bid: price - 0.01,
          ask: price + 0.01,
          last: price,
          volume: Math.floor(Math.random() * 1000000),
          change,
          changePercent,
          timestamp: new Date().toISOString()
        };
      });

      // Generate trading signals (simulate algorithm)
      const newSignals: TradingSignal[] = [];
      if (Math.random() > 0.7) { // 30% chance of new signal
        const symbol = symbols[Math.floor(Math.random() * symbols.length)];
        const signal = Math.random() > 0.5 ? 'BUY' : 'SELL';
        const marketDataPoint = newMarketData.find(m => m.symbol === symbol);
        
        if (marketDataPoint) {
          newSignals.push({
            id: `signal_${Date.now()}`,
            symbol,
            signal,
            price: marketDataPoint.last,
            strength: Math.random() * 0.8 + 0.2, // 0.2 to 1.0
            timestamp: new Date().toISOString(),
            indicators: {
              sma_20: marketDataPoint.last * (0.98 + Math.random() * 0.04),
              sma_50: marketDataPoint.last * (0.96 + Math.random() * 0.08),
              rsi: Math.random() * 100,
              macd: (Math.random() - 0.5) * 2
            }
          });
        }
      }

      // Update pipeline metrics
      const newMetrics = {
        dataIngestionLatency: Math.random() * 50 + 10, // 10-60ms
        algorithmExecutionTime: Math.random() * 200 + 50, // 50-250ms
        orderRoutingLatency: Math.random() * 100 + 20, // 20-120ms
        endToEndLatency: Math.random() * 300 + 100, // 100-400ms
        signalsPerSecond: Math.random() * 5 + 1, // 1-6 signals/sec
        ordersPerSecond: Math.random() * 3 + 0.5, // 0.5-3.5 orders/sec
        eventsPerSecond: Math.random() * 10 + 5, // 5-15 events/sec
        successRate: 95 + Math.random() * 5, // 95-100%
        timestamp: new Date().toISOString()
      };

      setDashboardData(prev => ({
        ...prev,
        marketData: newMarketData,
        signals: [...newSignals, ...prev.signals].slice(0, 20), // Keep last 20 signals
        pipelineMetrics: newMetrics
      }));
    }, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [dashboardData.connectionStatus.isConnected]);

  // Handle order placement
  const placeOrder = (signal: TradingSignal, quantity: number) => {
    const newOrder: Order = {
      id: `order_${Date.now()}`,
      symbol: signal.symbol,
      action: signal.signal,
      quantity,
      orderType: 'MARKET',
      status: 'SUBMITTED',
      timestamp: new Date().toISOString(),
      orderId: Math.floor(Math.random() * 10000) + 1000
    };

    setDashboardData(prev => ({
      ...prev,
      orders: [newOrder, ...prev.orders].slice(0, 50) // Keep last 50 orders
    }));

    // Simulate order fill after delay
    setTimeout(() => {
      setDashboardData(prev => ({
        ...prev,
        orders: prev.orders.map(order => 
          order.id === newOrder.id 
            ? { ...order, status: 'FILLED' as const }
            : order
        )
      }));
    }, 2000 + Math.random() * 3000); // 2-5 seconds
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600 dark:text-gray-400">
            Connecting to IBKR {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-red-600 dark:text-red-400 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Connection Failed
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Row - Account & Pipeline Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AccountSummary 
          accountInfo={dashboardData.accountInfo} 
          tradingMode={tradingMode}
        />
        <PipelineMetrics metrics={dashboardData.pipelineMetrics} />
      </div>

      {/* Second Row - Market Data & Signals */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <MarketDataGrid marketData={dashboardData.marketData} />
        </div>
        <div>
          <SignalsPanel 
            signals={dashboardData.signals} 
            onPlaceOrder={placeOrder}
            tradingMode={tradingMode}
          />
        </div>
      </div>

      {/* Third Row - Orders & Positions */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <OrdersPanel orders={dashboardData.orders} />
        <PositionsPanel positions={dashboardData.positions} />
      </div>
    </div>
  );
}