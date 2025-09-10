import { DependencyHealth, VulnerabilityInfo, SystemMetrics, HealthDashboardData } from '@/types/monitoring';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  timestamp?: string;
}

/**
 * Fetches the complete health dashboard data.
 * @returns A promise that resolves to the health dashboard data.
 */
export const getHealthDashboard = async (): Promise<HealthDashboardData> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/health-dashboard`, {
      headers: {
        'Authorization': 'Bearer demo_token', // In a real app, this would come from auth context
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result: ApiResponse<HealthDashboardData> = await response.json();
    
    if (!result.success || !result.data) {
      throw new Error(result.message || 'Failed to fetch health dashboard data.');
    }
    
    return result.data;
  } catch (error) {
    console.error('Error fetching health dashboard:', error);
    throw error;
  }
};

/**
 * Fetches the health status of all dependencies.
 * @returns A promise that resolves to an array of dependency health data.
 */
export const getDependenciesHealth = async (): Promise<DependencyHealth[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/dependencies`, {
      headers: {
        'Authorization': 'Bearer demo_token',
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result: ApiResponse<DependencyHealth[]> = await response.json();
    
    if (!result.success || !result.data) {
      throw new Error(result.message || 'Failed to fetch dependencies health data.');
    }
    
    return result.data;
  } catch (error) {
    console.error('Error fetching dependencies health:', error);
    throw error;
  }
};

/**
 * Fetches current vulnerability information.
 * @returns A promise that resolves to an array of vulnerability data.
 */
export const getVulnerabilities = async (): Promise<VulnerabilityInfo[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/vulnerabilities`, {
      headers: {
        'Authorization': 'Bearer demo_token',
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result: ApiResponse<VulnerabilityInfo[]> = await response.json();
    
    if (!result.success || !result.data) {
      throw new Error(result.message || 'Failed to fetch vulnerabilities data.');
    }
    
    return result.data;
  } catch (error) {
    console.error('Error fetching vulnerabilities:', error);
    throw error;
  }
};

/**
 * Fetches current system metrics.
 * @returns A promise that resolves to system metrics data.
 */
export const getSystemMetrics = async (): Promise<SystemMetrics> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/system-metrics`, {
      headers: {
        'Authorization': 'Bearer demo_token',
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result: ApiResponse<SystemMetrics> = await response.json();
    
    if (!result.success || !result.data) {
      throw new Error(result.message || 'Failed to fetch system metrics data.');
    }
    
    return result.data;
  } catch (error) {
    console.error('Error fetching system metrics:', error);
    throw error;
  }
};