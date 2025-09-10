import { useState, useEffect } from 'react';
import monitoringApi from '@/app/api/monitoring/service';
import { Dependency } from '@/components/molecules/DependencyTable';
import { VulnerabilityData } from '@/components/molecules/VulnerabilityChart';

export interface HealthDashboardData {
  systemStatus: 'healthy' | 'warning' | 'critical';
  overallHealth: number;
  totalVulnerabilities: number;
  dependencies: Dependency[];
  vulnerabilityData: VulnerabilityData[];
  performanceData: Array<{ time: string; tier1: number; tier2: number; tier3: number }>;
  metrics: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    servicesUp: number;
  };
}

export interface HealthDashboardResponse {
  success: boolean;
  data: {
    timestamp: string;
    system_status: string;
    system_metrics: {
      cpu_usage: number;
      memory_usage: number;
      disk_usage: number;
      network_in: number;
      network_out: number;
      active_connections: number;
    };
    dependencies: Array<{
      name: string;
      tier: number;
      status: string;
      version: string;
      last_update: string;
      uptime: number;
      latency: number;
      error_count: number;
    }>;
    vulnerabilities: Array<{
      id: string;
      severity: string;
      component: string;
      description: string;
      published_date: string;
      remediation: string | null;
    }>;
    alerts: Array<any>;
    last_scan: string;
  };
  message: string;
}

export const useHealthDashboard = () => {
  const [data, setData] = useState<HealthDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch health dashboard data from API
        const response: HealthDashboardResponse = await monitoringApi.getHealthDashboard();
        
        if (!response.success) {
          throw new Error(response.message || 'Failed to fetch health dashboard data');
        }

        // Transform API response to component data structure
        const transformedData: HealthDashboardData = {
          systemStatus: response.data.system_status as 'healthy' | 'warning' | 'critical',
          overallHealth: response.data.system_metrics.cpu_usage, // This would be calculated properly in a real implementation
          totalVulnerabilities: response.data.vulnerabilities.length,
          dependencies: response.data.dependencies.map(dep => ({
            name: dep.name,
            tier: dep.tier,
            version: dep.version,
            status: dep.status as 'healthy' | 'warning' | 'critical',
            lastUpdate: new Date(dep.last_update).toLocaleString(),
            uptime: dep.uptime / 100,
            latency: dep.latency / 1000,
            vulnerabilities: dep.error_count
          })),
          vulnerabilityData: [
            { 
              name: 'Critical', 
              value: response.data.vulnerabilities.filter(v => v.severity === 'critical').length, 
              color: '#ef4444' 
            },
            { 
              name: 'High', 
              value: response.data.vulnerabilities.filter(v => v.severity === 'high').length, 
              color: '#f97316' 
            },
            { 
              name: 'Medium', 
              value: response.data.vulnerabilities.filter(v => v.severity === 'medium').length, 
              color: '#eab308' 
            },
            { 
              name: 'Low', 
              value: response.data.vulnerabilities.filter(v => v.severity === 'low').length, 
              color: '#22c55e' 
            }
          ],
          performanceData: [
            { time: '00:00', tier1: 95, tier2: 92, tier3: 88 },
            { time: '04:00', tier1: 96, tier2: 93, tier3: 89 },
            { time: '08:00', tier1: 94, tier2: 91, tier3: 87 },
            { time: '12:00', tier1: 97, tier2: 94, tier3: 90 },
            { time: '16:00', tier1: 95, tier2: 92, tier3: 88 },
            { time: '20:00', tier1: 96, tier2: 93, tier3: 89 },
          ],
          metrics: {
            cpuUsage: response.data.system_metrics.cpu_usage,
            memoryUsage: response.data.system_metrics.memory_usage,
            diskUsage: response.data.system_metrics.disk_usage,
            servicesUp: response.data.system_metrics.active_connections
          }
        };

        setData(transformedData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health dashboard data');
        console.error('Error fetching health dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Set up polling for real-time updates
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error };
};