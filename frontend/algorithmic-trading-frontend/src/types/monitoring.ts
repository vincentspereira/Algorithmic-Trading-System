export interface DependencyHealth {
  name: string;
  tier: number;
  status: 'healthy' | 'warning' | 'critical';
  version: string;
  last_update: string; // ISO date string
  uptime: number; // percentage
  latency: number; // ms
  error_count: number;
  last_error?: string | null;
}

export interface VulnerabilityInfo {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  component: string;
  description: string;
  published_date: string; // ISO date string
  remediation?: string | null;
}

export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number; // Mbps
  network_out: number; // Mbps
  active_connections: number;
}

export interface HealthDashboardData {
  timestamp: string; // ISO date string
  system_status: 'healthy' | 'degraded' | 'critical';
  system_metrics: SystemMetrics;
  dependencies: DependencyHealth[];
  vulnerabilities: VulnerabilityInfo[];
  alerts: Array<{
    id: string;
    severity: 'critical' | 'high' | 'warning' | 'info';
    title: string;
    description: string;
    timestamp: string; // ISO date string
    component: string;
  }>;
  last_scan: string; // ISO date string
}