import { useState, useEffect } from 'react';
import { 
  getHealthDashboard, 
  getDependenciesHealth, 
  getVulnerabilities, 
  getSystemMetrics 
} from '@/services/monitoring';
import { HealthDashboardData, DependencyHealth, VulnerabilityInfo, SystemMetrics } from '@/types/monitoring';

export const useMonitoring = () => {
  const [dashboardData, setDashboardData] = useState<HealthDashboardData | null>(null);
  const [dependencies, setDependencies] = useState<DependencyHealth[]>([]);
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilityInfo[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getHealthDashboard();
      setDashboardData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchDependencies = async () => {
    try {
      const data = await getDependenciesHealth();
      setDependencies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dependencies data');
    }
  };

  const fetchVulnerabilities = async () => {
    try {
      const data = await getVulnerabilities();
      setVulnerabilities(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch vulnerabilities data');
    }
  };

  const fetchMetrics = async () => {
    try {
      const data = await getSystemMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics data');
    }
  };

  // Fetch all data initially
  useEffect(() => {
    const fetchData = async () => {
      await Promise.all([
        fetchDashboardData(),
        fetchDependencies(),
        fetchVulnerabilities(),
        fetchMetrics()
      ]);
    };

    fetchData();

    // Set up polling for real-time updates (every 30 seconds)
    const interval = setInterval(fetchData, 30000);

    return () => clearInterval(interval);
  }, []);

  return {
    dashboardData,
    dependencies,
    vulnerabilities,
    metrics,
    loading,
    error,
    refresh: fetchDashboardData
  };
};