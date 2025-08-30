"use client";

import { MarketData } from '@/types/trading';

interface MarketDataGridProps {
  marketData: MarketData[];
}

export default function MarketDataGrid({ marketData }: MarketDataGridProps) {
  const formatPrice = (price: number) => price.toFixed(2);
  const formatChange = (change: number) => `${change >= 0 ? '+' : ''}${change.toFixed(2)}`;
  const formatPercent = (percent: number) => `${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          📊 Real-Time Market Data
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Live prices from IBKR Gateway
        </p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Last
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Bid
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Ask
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Change
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Volume
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {marketData.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  <div className="flex flex-col items-center space-y-2">
                    <div className="animate-pulse text-2xl">📡</div>
                    <p>Waiting for market data...</p>
                  </div>
                </td>
              </tr>
            ) : (
              marketData.map((data, index) => (
                <tr 
                  key={data.symbol} 
                  className={`hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                    index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-750'
                  }`}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {data.symbol}
                      </div>
                      <div className="ml-2 w-2 h-2 bg-green-400 rounded-full animate-pulse" 
                           title="Live data" />
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900 dark:text-white">
                    ${formatPrice(data.last)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-blue-600 dark:text-blue-400">
                    ${formatPrice(data.bid)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-red-600 dark:text-red-400">
                    ${formatPrice(data.ask)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <div className={`flex flex-col ${
                      data.change >= 0 
                        ? 'text-green-600 dark:text-green-400' 
                        : 'text-red-600 dark:text-red-400'
                    }`}>
                      <span className="font-medium">{formatChange(data.change)}</span>
                      <span className="text-xs">{formatPercent(data.changePercent)}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-600 dark:text-gray-400">
                    {data.volume.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-xs text-gray-500 dark:text-gray-400">
                    {new Date(data.timestamp).toLocaleTimeString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}