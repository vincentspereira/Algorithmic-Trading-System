import axios from 'axios';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Health Dashboard API endpoints
export const monitoringApi = {
  // Get health dashboard data
  getHealthDashboard: async () => {
    const response = await apiClient.get('/monitoring/health-dashboard');
    return response.data;
  },

  // Get dependencies health status
  getDependenciesHealth: async () => {
    const response = await apiClient.get('/monitoring/dependencies');
    return response.data;
  },

  // Get vulnerabilities information
  getVulnerabilities: async () => {
    const response = await apiClient.get('/monitoring/vulnerabilities');
    return response.data;
  },

  // Get system metrics
  getSystemMetrics: async () => {
    const response = await apiClient.get('/monitoring/system-metrics');
    return response.data;
  },
};

export default monitoringApi;