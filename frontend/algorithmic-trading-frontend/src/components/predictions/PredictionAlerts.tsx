import React, { useState, useEffect } from 'react';

// A simple Bell icon for notifications
const BellIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
);

interface Alert {
  id: string;
  symbol: string;
  message: string;
  timestamp: string;
  confidence: number;
}

interface PredictionAlertsProps {
  alerts: Alert[];
}

const PredictionAlerts: React.FC<PredictionAlertsProps> = ({ alerts }) => {
  const getAlertColor = (confidence: number) => {
    if (confidence > 0.9) return 'border-yellow-400 bg-yellow-500 bg-opacity-10';
    if (confidence > 0.8) return 'border-blue-400 bg-blue-500 bg-opacity-10';
    return 'border-gray-600';
  };

  if (alerts.length === 0) {
    return (
      <div className="bg-gray-800 p-4 rounded-lg shadow-lg text-center text-gray-400">
        No high-confidence alerts at the moment.
      </div>
    );
  }

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-lg max-h-80 overflow-y-auto">
      <h3 className="text-lg font-bold text-white mb-4">High-Confidence Alerts</h3>
      <div className="space-y-3">
        {alerts.map(alert => (
          <div
            key={alert.id}
            className={`flex items-center p-3 rounded-md border-l-4 ${getAlertColor(alert.confidence)}`}
          >
            <BellIcon />
            <div className="flex-grow">
              <p className="font-semibold text-white">{alert.symbol}: <span className="font-normal">{alert.message}</span></p>
              <p className="text-xs text-gray-400">
                {new Date(alert.timestamp).toLocaleTimeString()} - Confidence: {(alert.confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Mock data and component for demonstration
export const MockPredictionAlerts: React.FC = () => {
    const [mockAlerts, setMockAlerts] = useState<Alert[]>([]);

    useEffect(() => {
        // Initial mock alerts
        const initialAlerts: Alert[] = [
            { id: '1', symbol: 'NVDA', message: 'Strong buy signal predicted in 5min.', timestamp: new Date().toISOString(), confidence: 0.92 },
            { id: '2', symbol: 'BTC-USD', message: 'Potential upward trend in 15min.', timestamp: new Date().toISOString(), confidence: 0.85 },
        ];
        setMockAlerts(initialAlerts);

        // Simulate new alerts coming in
        const interval = setInterval(() => {
            const newAlert: Alert = {
                id: Math.random().toString(36).substr(2, 9),
                symbol: ['AAPL', 'GOOGL', 'AMZN'][Math.floor(Math.random() * 3)],
                message: 'Price surge expected.',
                timestamp: new Date().toISOString(),
                confidence: 0.8 + Math.random() * 0.15,
            };
            setMockAlerts(prev => [newAlert, ...prev].slice(0, 10)); // Keep last 10 alerts
        }, 8000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="p-8 bg-gray-900">
            <PredictionAlerts alerts={mockAlerts} />
        </div>
    );
};

export default PredictionAlerts;