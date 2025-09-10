import React from 'react';
import { SystemMetrics } from '@/types/monitoring';

interface SystemMetricsProps {
  metrics: SystemMetrics;
}

const SystemMetrics: React.FC<SystemMetricsProps> = ({ metrics }) => {
  const getMetricColor = (value: number, threshold: number) => {
    if (value > threshold * 0.9) return 'text-red-400';
    if (value > threshold * 0.7) return 'text-yellow-400';
    return 'text-green-400';
  };

  const MetricCard: React.FC<{ title: string; value: number | string; unit?: string; threshold?: number; decimalPlaces?: number }> = 
  ({ title, value, unit = '', threshold = 80, decimalPlaces = 1 }) => {
    const displayValue = typeof value === 'number' ? value.toFixed(decimalPlaces) : value;
    const colorClass = typeof value === 'number' ? getMetricColor(value, threshold) : 'text-white';
    
    return (
      <div className="bg-gray-800 rounded-lg p-4 shadow-md">
        <p className="text-gray-400 text-sm">{title}</p>
        <p className={`text-2xl font-bold ${colorClass}`}>{displayValue}{unit}</p>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <MetricCard 
        title="CPU Usage" 
        value={metrics.cpu_usage} 
        unit="%" 
        threshold={80} 
      />
      <MetricCard 
        title="Memory Usage" 
        value={metrics.memory_usage} 
        unit="%" 
        threshold={85} 
      />
      <MetricCard 
        title="Disk Usage" 
        value={metrics.disk_usage} 
        unit="%" 
        threshold={90} 
      />
      <MetricCard 
        title="Network In" 
        value={metrics.network_in} 
        unit=" Mbps" 
        threshold={100} 
        decimalPlaces={2}
      />
      <MetricCard 
        title="Network Out" 
        value={metrics.network_out} 
        unit=" Mbps" 
        threshold={100} 
        decimalPlaces={2}
      />
      <MetricCard 
        title="Connections" 
        value={metrics.active_connections} 
      />
    </div>
  );
};

export default SystemMetrics;