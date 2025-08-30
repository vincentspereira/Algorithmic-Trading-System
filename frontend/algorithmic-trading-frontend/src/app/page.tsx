"use client";

import { useState, useEffect } from 'react';
import TradingDashboard from '@/components/TradingDashboard';
import ConnectionStatus from '@/components/ConnectionStatus';
import { TradingMode } from '@/types/trading';

export default function Home() {
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  const [isConnected, setIsConnected] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                Algorithmic Trading System
              </h1>
              <span className="ml-3 text-sm text-gray-500 dark:text-gray-400">
                Phase 1 - Core System
              </span>
            </div>
            
            {/* Trading Mode Toggle */}
            <div className="flex items-center space-x-4">
              <ConnectionStatus isConnected={isConnected} />
              
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Trading Mode:
                </label>
                <select
                  value={tradingMode}
                  onChange={(e) => setTradingMode(e.target.value as TradingMode)}
                  className={`
                    px-3 py-1 rounded-md text-sm font-medium border transition-colors
                    ${tradingMode === 'paper' 
                      ? 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900 dark:text-green-200 dark:border-green-700'
                      : 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700'
                    }
                    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                  `}
                >
                  <option value="paper">📄 Paper Trading</option>
                  <option value="live">🔴 Live Trading</option>
                </select>
              </div>
              
              {/* Safety Warning for Live Mode */}
              {tradingMode === 'live' && (
                <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 px-2 py-1 rounded text-xs font-medium">
                  ⚠️ LIVE MODE
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <TradingDashboard 
          tradingMode={tradingMode} 
          setIsConnected={setIsConnected}
        />
      </main>
    </div>
  );
}
