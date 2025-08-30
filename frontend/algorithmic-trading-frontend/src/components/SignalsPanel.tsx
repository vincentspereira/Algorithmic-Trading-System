"use client";

import { TradingSignal, TradingMode } from '@/types/trading';

interface SignalsPanelProps {
  signals: TradingSignal[];
  onPlaceOrder: (signal: TradingSignal, quantity: number) => void;
  tradingMode: TradingMode;
}

export default function SignalsPanel({ signals, onPlaceOrder, tradingMode }: SignalsPanelProps) {
  const getSignalColor = (signal: 'BUY' | 'SELL') => {
    return signal === 'BUY' 
      ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900' 
      : 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900';
  };

  const getStrengthColor = (strength: number) => {
    if (strength >= 0.7) return 'text-green-600 dark:text-green-400';
    if (strength >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              🧠 Algorithm Signals
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Latest trading signals from technical analysis
            </p>
          </div>
          <div className="text-sm">
            <span className="text-gray-500 dark:text-gray-400">Total: </span>
            <span className="font-medium text-gray-900 dark:text-white">{signals.length}</span>
          </div>
        </div>
      </div>
      
      <div className="max-h-96 overflow-y-auto">
        {signals.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
            <div className="flex flex-col items-center space-y-2">
              <div className="text-2xl">🤖</div>
              <p>No signals generated yet</p>
              <p className="text-xs">Algorithm is analyzing market conditions...</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {signals.map((signal) => (
              <div key={signal.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {signal.symbol}
                    </span>
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getSignalColor(signal.signal)}`}>
                      {signal.signal}
                    </span>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      @ ${signal.price.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${getStrengthColor(signal.strength)}`}>
                      {(signal.strength * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      strength
                    </div>
                  </div>
                </div>
                
                {/* Indicators */}
                <div className="grid grid-cols-2 gap-2 mb-3 text-xs text-gray-600 dark:text-gray-400">
                  {signal.indicators.rsi && (
                    <div>RSI: {signal.indicators.rsi.toFixed(1)}</div>
                  )}
                  {signal.indicators.macd && (
                    <div>MACD: {signal.indicators.macd.toFixed(3)}</div>
                  )}
                  {signal.indicators.sma_20 && (
                    <div>SMA20: ${signal.indicators.sma_20.toFixed(2)}</div>
                  )}
                  {signal.indicators.sma_50 && (
                    <div>SMA50: ${signal.indicators.sma_50.toFixed(2)}</div>
                  )}
                </div>
                
                {/* Action Button */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {new Date(signal.timestamp).toLocaleTimeString()}
                  </span>
                  <button
                    onClick={() => onPlaceOrder(signal, 100)}
                    className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                      tradingMode === 'paper'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800'
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 hover:bg-red-200 dark:hover:bg-red-800'
                    }`}
                  >
                    {tradingMode === 'paper' ? '📄 Paper Order' : '🔴 Live Order'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}