"use client";

import { useEffect, useState } from 'react';
import { ConnectionStatus as ConnectionStatusType } from '@/types/trading';

interface ConnectionStatusProps {
  isConnected: boolean;
}

export default function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  const [status, setStatus] = useState<ConnectionStatusType>({
    isConnected: false
  });

  useEffect(() => {
    // Simulate connection status updates
    const interval = setInterval(() => {
      setStatus({
        isConnected,
        serverVersion: isConnected ? '176' : undefined,
        accountId: isConnected ? 'DUK221396' : undefined,
        marketDataFarms: isConnected ? ['usfarm.nj', 'hfarm', 'usfuture', 'cashfarm'] : undefined,
        lastUpdate: new Date().toLocaleTimeString()
      });
    }, 5000);

    return () => clearInterval(interval);
  }, [isConnected]);

  return (
    <div className="flex items-center space-x-2">
      {/* Connection Indicator */}
      <div className="flex items-center space-x-2">
        <div 
          className={`w-3 h-3 rounded-full ${
            status.isConnected 
              ? 'bg-green-500 animate-pulse' 
              : 'bg-red-500'
          }`}
        />
        <span className={`text-sm font-medium ${
          status.isConnected 
            ? 'text-green-700 dark:text-green-400' 
            : 'text-red-700 dark:text-red-400'
        }`}>
          {status.isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Connection Details */}
      {status.isConnected && (
        <div className="hidden lg:flex items-center space-x-4 text-xs text-gray-600 dark:text-gray-400">
          {status.serverVersion && (
            <span>Server: v{status.serverVersion}</span>
          )}
          {status.accountId && (
            <span>Account: {status.accountId}</span>
          )}
          {status.lastUpdate && (
            <span>Updated: {status.lastUpdate}</span>
          )}
        </div>
      )}

      {/* Market Data Farms Status */}
      {status.isConnected && status.marketDataFarms && (
        <div className="hidden xl:flex items-center space-x-1">
          <span className="text-xs text-gray-500 dark:text-gray-400">Farms:</span>
          <div className="flex space-x-1">
            {status.marketDataFarms.slice(0, 3).map((farm, index) => (
              <span 
                key={index}
                className="w-2 h-2 bg-green-400 rounded-full"
                title={`${farm} - Connected`}
              />
            ))}
            {status.marketDataFarms.length > 3 && (
              <span className="text-xs text-gray-500">
                +{status.marketDataFarms.length - 3}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}