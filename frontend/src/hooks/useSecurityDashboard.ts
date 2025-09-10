import { useState, useEffect } from 'react';
import monitoringApi from '@/app/api/monitoring/service';

// Types for security data
export interface Vulnerability {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  component: string;
  description: string;
  publishedDate: string;
  remediation: string | null;
}

export interface SastFinding {
  severity: 'critical' | 'high' | 'medium' | 'low';
  confidence: 'low' | 'medium' | 'high';
  description: string;
  file: string;
  line: number;
  testId: string;
}

export interface ThreatModel {
  id: string;
  component: string;
  category: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  mitigation: string;
  cvssScore: number;
  status: string;
}

export interface SecurityDashboardData {
  overallRiskScore: number;
  vulnerabilities: Vulnerability[];
  sastFindings: SastFinding[];
  threatModels: ThreatModel[];
  scanSummary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export interface SecurityDashboardResponse {
  success: boolean;
  data: {
    timestamp: string;
    overall_risk_score: number;
    vulnerabilities: Array<{
      id: string;
      severity: string;
      component: string;
      description: string;
      published_date: string;
      remediation: string | null;
    }>;
    sast_findings: Array<{
      severity: string;
      confidence: string;
      description: string;
      file: string;
      line: number;
      test_id: string;
    }>;
    threat_models: Array<{
      id: string;
      component: string;
      category: string;
      description: string;
      severity: string;
      mitigation: string;
      cvss_score: number;
      status: string;
    }>;
  };
  message: string;
}

export const useSecurityDashboard = () => {
  const [data, setData] = useState<SecurityDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // In a real implementation, this would fetch from your API
        // For now, we'll use mock data since the backend API doesn't have this endpoint yet
        
        // Mock data for demonstration
        const mockData: SecurityDashboardData = {
          overallRiskScore: 7.2,
          vulnerabilities: [
            {
              id: 'CVE-2023-12345',
              severity: 'high',
              component: 'NautilusTrader',
              description: 'Potential memory leak in order processing module',
              publishedDate: '2023-10-15',
              remediation: 'Upgrade to version 2.0.2 or apply patch'
            },
            {
              id: 'CVE-2023-67890',
              severity: 'medium',
              component: 'LangChain',
              description: 'Insecure temporary file creation',
              publishedDate: '2023-10-01',
              remediation: 'Upgrade to version 0.1.6'
            }
          ],
          sastFindings: [
            {
              severity: 'high',
              confidence: 'high',
              description: 'Use of insecure cryptographic hash function',
              file: 'security/auth.py',
              line: 45,
              testId: 'B324'
            },
            {
              severity: 'medium',
              confidence: 'medium',
              description: 'Hardcoded password detected',
              file: 'config/database.py',
              line: 12,
              testId: 'B105'
            }
          ],
          threatModels: [
            {
              id: 'THREAT-TRADING-ENGINE-TAMPERING-001',
              component: 'Trading Engine',
              category: 'Tampering',
              description: 'Unauthorized modification of trade orders or execution parameters',
              severity: 'critical',
              mitigation: 'Implement immutable event sourcing, digital signatures for all trade events, audit trails',
              cvssScore: 9.0,
              status: 'Open'
            },
            {
              id: 'THREAT-DATABASE-DISCLOSURE-001',
              component: 'PostgreSQL Database',
              category: 'Information Disclosure',
              description: 'Unauthorized access to sensitive financial data, trade history, or user information',
              severity: 'critical',
              mitigation: 'Implement AES-256 encryption at rest, TLS 1.3 for data in transit, RBAC with least privilege',
              cvssScore: 9.0,
              status: 'Mitigated'
            }
          ],
          scanSummary: {
            critical: 2,
            high: 3,
            medium: 5,
            low: 8
          }
        };

        setData(mockData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch security dashboard data');
        console.error('Error fetching security dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Set up polling for real-time updates
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error };
};