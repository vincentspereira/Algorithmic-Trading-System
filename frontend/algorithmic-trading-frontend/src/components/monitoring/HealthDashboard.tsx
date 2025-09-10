"use client";

import React, { useState } from 'react';
import { useMonitoring } from '@/hooks/useMonitoring';
import DependencyStatus from './DependencyStatus';
import VulnerabilityCard from './VulnerabilityCard';
import SystemMetrics from './SystemMetrics';
import { HealthDashboardData } from '@/types/monitoring';

const HealthDashboard: React.FC = () => {
  const { dashboardData, loading, error, refresh } = useMonitoring();
  const [filter, setFilter] = useState<string>('all'); // all, critical, warning, healthy

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded relative" role="alert">
        <strong className="font-bold">Error: </strong>
        <span className="block sm:inline">{error}</span>
        <button 
          onClick={refresh}
          className="mt-2 bg-red-800 hover:bg-red-700 text-white font-bold py-1 px-2 rounded"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="bg-yellow-900 border border-yellow-700 text-yellow-100 px-4 py-3 rounded relative" role="alert">
        <strong className="font-bold">No Data: </strong>
        <span className="block sm:inline">No dashboard data available</span>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return 'Healthy';
      case 'degraded': return 'Degraded';
      case 'critical': return 'Critical';
      default: return 'Unknown';
    }
  };

  const filteredDependencies = dashboardData.dependencies.filter(dep => {
    if (filter === 'all') return true;
    return dep.status === filter;
  });

  const criticalVulns = dashboardData.vulnerabilities.filter(v => v.severity === 'critical' || v.severity === 'high');
  const mediumVulns = dashboardData.vulnerabilities.filter(v => v.severity === 'medium');
  const lowVulns = dashboardData.vulnerabilities.filter(v => v.severity === 'low');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Health Dashboard</h1>
          <p className="text-gray-400">Real-time system status and monitoring</p>
        </div>
        <div className="mt-4 md:mt-0 flex items-center space-x-4">
          <div className="flex items-center">
            <span className={`w-3 h-3 rounded-full ${getStatusColor(dashboardData.system_status)} mr-2`}></span>
            <span className="text-white font-medium">{getStatusText(dashboardData.system_status)}</span>
          </div>
          <button 
            onClick={refresh}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded flex items-center"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* System Metrics */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">System Metrics</h2>
        <SystemMetrics metrics={dashboardData.system_metrics} />
      </div>

      {/* Dependencies Section */}
      <div>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Dependencies</h2>
          <div className="mt-2 md:mt-0 flex space-x-2">
            <button 
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded text-sm ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}
            >
              All
            </button>
            <button 
              onClick={() => setFilter('healthy')}
              className={`px-3 py-1 rounded text-sm ${filter === 'healthy' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300'}`}
            >
              Healthy
            </button>
            <button 
              onClick={() => setFilter('warning')}
              className={`px-3 py-1 rounded text-sm ${filter === 'warning' ? 'bg-yellow-600 text-white' : 'bg-gray-700 text-gray-300'}`}
            >
              Warning
            </button>
            <button 
              onClick={() => setFilter('critical')}
              className={`px-3 py-1 rounded text-sm ${filter === 'critical' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-300'}`}
            >
              Critical
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDependencies.map((dependency, index) => (
            <DependencyStatus key={index} dependency={dependency} />
          ))}
        </div>
      </div>

      {/* Vulnerabilities Section */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Security Vulnerabilities</h2>
        
        {criticalVulns.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-medium text-red-400 mb-2">Critical & High Severity</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {criticalVulns.map((vuln, index) => (
                <VulnerabilityCard key={index} vulnerability={vuln} />
              ))}
            </div>
          </div>
        )}
        
        {mediumVulns.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-medium text-yellow-400 mb-2">Medium Severity</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {mediumVulns.map((vuln, index) => (
                <VulnerabilityCard key={index} vulnerability={vuln} />
              ))}
            </div>
          </div>
        )}
        
        {lowVulns.length > 0 && (
          <div>
            <h3 className="text-lg font-medium text-blue-400 mb-2">Low Severity</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {lowVulns.map((vuln, index) => (
                <VulnerabilityCard key={index} vulnerability={vuln} />
              ))}
            </div>
          </div>
        )}
        
        {dashboardData.vulnerabilities.length === 0 && (
          <div className="bg-green-900 border border-green-700 text-green-100 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Good News! </strong>
            <span className="block sm:inline">No vulnerabilities detected</span>
          </div>
        )}
      </div>

      {/* Last Scan Info */}
      <div className="text-center text-gray-500 text-sm">
        <p>Last scan: {new Date(dashboardData.last_scan).toLocaleString()}</p>
      </div>
    </div>
  );
};

export default HealthDashboard;