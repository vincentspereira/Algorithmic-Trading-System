import React from 'react';
import { useHealthDashboard } from '@/hooks/useHealthDashboard';
import { MetricCard } from '@/components/molecules/MetricCard';
import { DependencyTable } from '@/components/molecules/DependencyTable';
import { VulnerabilityChart } from '@/components/molecules/VulnerabilityChart';
import { StatusIndicator } from '@/components/atoms/StatusIndicator';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const HealthDashboard = () => {
  const { data, loading, error } = useHealthDashboard();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p>Loading health dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-red-500">
          <p>Error loading dashboard data: {error}</p>
          <button 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-96">
        <p>No data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* System Overview */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Health Dashboard</h1>
        <p className="text-muted-foreground">Real-time status of the Algorithmic Trading System</p>
      </div>

      {/* Status Bar */}
      <div className="flex items-center p-4 rounded-lg border bg-card">
        <StatusIndicator 
          variant={data.systemStatus === 'healthy' ? 'healthy' : data.systemStatus === 'warning' ? 'warning' : 'critical'} 
          size="lg" 
          className="mr-3"
        />
        <div>
          <h2 className="text-lg font-semibold">
            System Status: <span className="capitalize">{data.systemStatus}</span>
          </h2>
          <p className="text-sm text-muted-foreground">
            Overall health score: {data.overallHealth}%
          </p>
        </div>
        <div className="ml-auto flex items-center space-x-4">
          <div className="text-right">
            <p className="text-sm font-medium">Vulnerabilities</p>
            <p className="text-2xl font-bold text-red-600">{data.totalVulnerabilities}</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-medium">Dependencies</p>
            <p className="text-2xl font-bold">{data.dependencies.length}</p>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU Usage"
          value={data.metrics.cpuUsage}
          unit="%"
          status={data.metrics.cpuUsage < 80 ? 'healthy' : data.metrics.cpuUsage < 90 ? 'warning' : 'critical'}
          trend="down"
        />
        <MetricCard
          title="Memory Usage"
          value={data.metrics.memoryUsage}
          unit="%"
          status={data.metrics.memoryUsage < 80 ? 'healthy' : data.metrics.memoryUsage < 90 ? 'warning' : 'critical'}
          trend="neutral"
        />
        <MetricCard
          title="Disk Usage"
          value={data.metrics.diskUsage}
          unit="%"
          status={data.metrics.diskUsage < 80 ? 'healthy' : data.metrics.diskUsage < 90 ? 'warning' : 'critical'}
          trend="down"
        />
        <MetricCard
          title="Services Up"
          value={data.metrics.servicesUp}
          unit="/ 24"
          status="healthy"
          trend="neutral"
        />
      </div>

      {/* Charts and Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Chart */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Dependency Performance by Tier</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data.performanceData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis unit="%" domain={[80, 100]} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="tier1" 
                  stroke="#3b82f6" 
                  activeDot={{ r: 8 }} 
                  name="Tier 1" 
                />
                <Line 
                  type="monotone" 
                  dataKey="tier2" 
                  stroke="#10b981" 
                  name="Tier 2" 
                />
                <Line 
                  type="monotone" 
                  dataKey="tier3" 
                  stroke="#f59e0b" 
                  name="Tier 3" 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Vulnerability Chart */}
        <VulnerabilityChart 
          data={data.vulnerabilityData} 
          title="Vulnerabilities by Severity"
        />
      </div>

      {/* Dependency Table */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Dependency Status Overview</h3>
        <DependencyTable dependencies={data.dependencies} />
      </div>
    </div>
  );
};

export { HealthDashboard };