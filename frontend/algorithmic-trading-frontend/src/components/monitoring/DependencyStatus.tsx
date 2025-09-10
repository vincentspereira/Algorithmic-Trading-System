import React from 'react';
import { DependencyHealth } from '@/types/monitoring';

interface DependencyStatusProps {
  dependency: DependencyHealth;
}

const DependencyStatus: React.FC<DependencyStatusProps> = ({ dependency }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return 'Healthy';
      case 'warning': return 'Warning';
      case 'critical': return 'Critical';
      default: return 'Unknown';
    }
  };

  const formatLastUpdate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 shadow-md hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold text-white">{dependency.name}</h3>
          <p className="text-gray-400 text-sm">Tier {dependency.tier}</p>
        </div>
        <div className="flex items-center">
          <span className={`w-3 h-3 rounded-full ${getStatusColor(dependency.status)} mr-2`}></span>
          <span className="text-sm font-medium text-white">{getStatusText(dependency.status)}</span>
        </div>
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-2">
        <div>
          <p className="text-xs text-gray-500">Version</p>
          <p className="text-sm text-white">{dependency.version}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Uptime</p>
          <p className="text-sm text-white">{dependency.uptime.toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Latency</p>
          <p className="text-sm text-white">{dependency.latency.toFixed(1)}ms</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Errors</p>
          <p className="text-sm text-white">{dependency.error_count}</p>
        </div>
      </div>
      
      <div className="mt-3 pt-3 border-t border-gray-700">
        <p className="text-xs text-gray-500">Last Update</p>
        <p className="text-sm text-white">{formatLastUpdate(dependency.last_update)}</p>
      </div>
      
      {dependency.last_error && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <p className="text-xs text-gray-500">Last Error</p>
          <p className="text-sm text-red-400 truncate">{dependency.last_error}</p>
        </div>
      )}
    </div>
  );
};

export default DependencyStatus;