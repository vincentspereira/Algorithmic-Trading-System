// OrdersPanel.tsx
"use client";

import { Order } from '@/types/trading';

interface OrdersPanelProps {
  orders: Order[];
}

export function OrdersPanel({ orders }: OrdersPanelProps) {
  const getStatusColor = (status: Order['status']) => {
    switch (status) {
      case 'FILLED': return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900';
      case 'SUBMITTED': return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900';
      case 'PENDING': return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900';
      case 'CANCELLED': return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900';
      default: return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          📈 Recent Orders
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Order execution history
        </p>
      </div>
      
      <div className="max-h-64 overflow-y-auto">
        {orders.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
            <div className="text-2xl mb-2">📋</div>
            <p>No orders placed yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {orders.map((order) => (
              <div key={order.id} className="px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="font-medium text-gray-900 dark:text-white">{order.symbol}</span>
                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                      order.action === 'BUY' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                                             : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {order.action}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {order.quantity} shares
                    </span>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(order.status)}`}>
                    {order.status}
                  </span>
                </div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {new Date(order.timestamp).toLocaleString()}
                  {order.orderId && ` • ID: ${order.orderId}`}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// PositionsPanel.tsx
export function PositionsPanel({ positions }: { positions: any[] }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          💼 Positions
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Current portfolio positions
        </p>
      </div>
      
      <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
        <div className="text-2xl mb-2">📊</div>
        <p>No open positions</p>
        <p className="text-xs">Positions will appear after order fills</p>
      </div>
    </div>
  );
}

// AccountSummary.tsx
export function AccountSummary({ accountInfo, tradingMode }: { accountInfo: any, tradingMode: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            💰 Account Summary
          </h2>
          <span className={`px-2 py-1 text-xs font-medium rounded ${
            tradingMode === 'paper' 
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
          }`}>
            {tradingMode === 'paper' ? '📄 Paper' : '🔴 Live'} • {accountInfo.accountId}
          </span>
        </div>
      </div>
      
      <div className="px-6 py-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Net Liquidation</div>
            <div className="text-xl font-semibold text-gray-900 dark:text-white">
              ${accountInfo.netLiquidation.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Available Funds</div>
            <div className="text-xl font-semibold text-gray-900 dark:text-white">
              ${accountInfo.availableFunds.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Buying Power</div>
            <div className="text-lg font-medium text-gray-900 dark:text-white">
              ${accountInfo.buyingPower.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Day Trades</div>
            <div className="text-lg font-medium text-gray-900 dark:text-white">
              {accountInfo.dayTradesRemaining === -1 ? 'Unlimited' : accountInfo.dayTradesRemaining}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// PipelineMetrics.tsx
export function PipelineMetrics({ metrics }: { metrics: any }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          ⚡ Pipeline Performance
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Real-time system metrics
        </p>
      </div>
      
      <div className="px-6 py-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">End-to-End Latency</div>
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              {metrics.endToEndLatency.toFixed(1)}ms
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Success Rate</div>
            <div className="text-lg font-semibold text-green-600 dark:text-green-400">
              {metrics.successRate.toFixed(1)}%
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Signals/sec</div>
            <div className="text-lg font-medium text-gray-900 dark:text-white">
              {metrics.signalsPerSecond.toFixed(1)}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Events/sec</div>
            <div className="text-lg font-medium text-gray-900 dark:text-white">
              {metrics.eventsPerSecond.toFixed(1)}
            </div>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Data Ingestion: {metrics.dataIngestionLatency.toFixed(1)}ms</span>
            <span>Algorithm: {metrics.algorithmExecutionTime.toFixed(1)}ms</span>
            <span>Order Routing: {metrics.orderRoutingLatency.toFixed(1)}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OrdersPanel;