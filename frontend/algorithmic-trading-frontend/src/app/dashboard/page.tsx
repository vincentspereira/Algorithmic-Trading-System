"use client";

import React, { useState } from 'react';
import { usePredictions } from '@/components/predictions/usePredictions';

// Import prediction components
import PredictionWidget from '@/components/predictions/PredictionWidget';
import PredictionChart from '@/components/predictions/PredictionChart';
import PredictionAlerts from '@/components/predictions/PredictionAlerts';

// Mock components for other parts of the dashboard
const MockPriceChart = ({ symbol }: { symbol: string }) => (
  <div className="bg-gray-800 p-4 rounded-lg shadow-lg h-96 flex items-center justify-center">
    <h3 className="text-white text-2xl">{symbol} Price Chart</h3>
  </div>
);

const MockOrderBook = ({ symbol }: { symbol: string }) => (
  <div className="bg-gray-800 p-4 rounded-lg shadow-lg h-full">
    <h3 className="text-white text-lg font-bold mb-4">{symbol} Order Book</h3>
    <p className="text-gray-400">Order book data...</p>
  </div>
);

const DashboardPage: React.FC = () => {
  const [showPredictions, setShowPredictions] = useState(true);
  const trackedSymbols = ['AAPL', 'GOOGL']; // Symbols to track for predictions
  
  const { realtimeData, historicalData, isConnected } = usePredictions(trackedSymbols);

  // For alerts, we would filter high-confidence predictions from realtimeData
  // This is a simplified mock representation.
  const highConfidenceAlerts = Object.values(realtimeData)
    .filter(p => p.predictions['1min'].confidence > 0.8)
    .map(p => ({
      id: `${p.symbol}-${p.timestamp}`,
      symbol: p.symbol,
      message: `High confidence prediction for 1min horizon.`,
      timestamp: p.timestamp,
      confidence: p.predictions['1min'].confidence,
    }));

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold">Algorithmic Trading Dashboard</h1>
        <div className="flex items-center space-x-4">
            <span className={`text-sm ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                Prediction Service: {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            <label className="flex items-center cursor-pointer">
                <span className="mr-2">Show Predictions</span>
                <div className="relative">
                    <input type="checkbox" className="sr-only" checked={showPredictions} onChange={() => setShowPredictions(!showPredictions)} />
                    <div className="w-10 h-4 bg-gray-600 rounded-full shadow-inner"></div>
                    <div className={`dot absolute w-6 h-6 bg-white rounded-full shadow -left-1 -top-1 transition-transform ${showPredictions ? 'transform translate-x-full bg-blue-400' : ''}`}></div>
                </div>
            </label>
        </div>
      </header>
      
      <main className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-8">
        {/* Main Chart */}
        <div className="col-span-1 md:col-span-2 lg:col-span-3">
          <MockPriceChart symbol="AAPL" />
        </div>

        {/* Side Panel */}
        <div className="col-span-1">
          <MockOrderBook symbol="AAPL" />
        </div>

        {/* Predictions Section */}
        {showPredictions && (
          <>
            <div className="col-span-1 md:col-span-3 lg:col-span-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {trackedSymbols.map(symbol => (
                    <PredictionWidget
                        key={symbol}
                        symbol={symbol}
                        predictions={realtimeData[symbol]?.predictions}
                        lastUpdated={realtimeData[symbol]?.timestamp}
                    />
                ))}
            </div>

            <div className="col-span-1 md:col-span-3 lg:col-span-4">
                <PredictionChart symbol="AAPL" data={historicalData['AAPL'] || []} />
            </div>

            <div className="col-span-1 md:col-span-3 lg:col-span-4">
                <PredictionAlerts alerts={highConfidenceAlerts} />
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default DashboardPage;