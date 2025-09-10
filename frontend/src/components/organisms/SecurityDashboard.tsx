import React from 'react';
import { useSecurityDashboard } from '@/hooks/useSecurityDashboard';
import { MetricCard } from '@/components/molecules/MetricCard';
import { StatusIndicator } from '@/components/atoms/StatusIndicator';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const SecurityDashboard = () => {
  const { data, loading, error } = useSecurityDashboard();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p>Loading security dashboard data...</p>
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

  // Severity colors
  const severityColors = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#eab308',
    low: '#22c55e'
  };

  // Prepare data for charts
  const severityData = [
    { name: 'Critical', value: data.scanSummary.critical, color: severityColors.critical },
    { name: 'High', value: data.scanSummary.high, color: severityColors.high },
    { name: 'Medium', value: data.scanSummary.medium, color: severityColors.medium },
    { name: 'Low', value: data.scanSummary.low, color: severityColors.low }
  ];

  const threatCategoryData = [
    { name: 'Spoofing', value: data.threatModels.filter(t => t.category === 'Spoofing').length },
    { name: 'Tampering', value: data.threatModels.filter(t => t.category === 'Tampering').length },
    { name: 'Repudiation', value: data.threatModels.filter(t => t.category === 'Repudiation').length },
    { name: 'Information Disclosure', value: data.threatModels.filter(t => t.category === 'Information Disclosure').length },
    { name: 'Denial of Service', value: data.threatModels.filter(t => t.category === 'Denial of Service').length },
    { name: 'Elevation of Privilege', value: data.threatModels.filter(t => t.category === 'Elevation of Privilege').length }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Security Dashboard</h1>
        <p className="text-muted-foreground">Comprehensive security monitoring and threat analysis</p>
      </div>

      {/* Overall Risk Score */}
      <div className="flex items-center p-4 rounded-lg border bg-card">
        <StatusIndicator 
          variant={data.overallRiskScore > 8 ? 'critical' : data.overallRiskScore > 6 ? 'warning' : 'healthy'} 
          size="lg" 
          className="mr-3"
        />
        <div>
          <h2 className="text-lg font-semibold">
            Overall Risk Score: <span className="font-bold">{data.overallRiskScore.toFixed(1)}/10.0</span>
          </h2>
          <p className="text-sm text-muted-foreground">
            Based on {data.vulnerabilities.length} vulnerabilities and {data.sastFindings.length} SAST findings
          </p>
        </div>
      </div>

      {/* Security Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Critical Issues"
          value={data.scanSummary.critical}
          status={data.scanSummary.critical > 0 ? 'critical' : 'healthy'}
        />
        <MetricCard
          title="High Severity"
          value={data.scanSummary.high}
          status={data.scanSummary.high > 0 ? 'warning' : 'healthy'}
        />
        <MetricCard
          title="Threat Models"
          value={data.threatModels.length}
          status="healthy"
        />
        <MetricCard
          title="Mitigated Threats"
          value={data.threatModels.filter(t => t.status === 'Mitigated').length}
          status="healthy"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vulnerabilities by Severity */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Issues by Severity</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value) => [value, 'Issues']}
                  labelFormatter={(label) => `Severity: ${label}`}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Threat Categories */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Threat Categories</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={threatCategoryData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Vulnerabilities Table */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Vulnerabilities</h3>
        <div className="rounded-md border">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  CVE ID
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Severity
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Component
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Description
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Published
                </th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {data.vulnerabilities.map((vuln, index) => (
                <tr 
                  key={index} 
                  className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                >
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium">
                    {vuln.id}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <div className="flex items-center">
                      <StatusIndicator 
                        variant={vuln.severity === 'critical' ? 'critical' : vuln.severity === 'high' ? 'warning' : vuln.severity === 'medium' ? 'warning' : 'healthy'} 
                        size="sm" 
                        className="mr-2"
                      />
                      <span className="capitalize">{vuln.severity}</span>
                    </div>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {vuln.component}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {vuln.description}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 text-muted-foreground">
                    {vuln.publishedDate}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SAST Findings Table */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">SAST Findings</h3>
        <div className="rounded-md border">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Severity
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Confidence
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Description
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Location
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Test ID
                </th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {data.sastFindings.map((finding, index) => (
                <tr 
                  key={index} 
                  className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                >
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <div className="flex items-center">
                      <StatusIndicator 
                        variant={finding.severity === 'critical' ? 'critical' : finding.severity === 'high' ? 'warning' : finding.severity === 'medium' ? 'warning' : 'healthy'} 
                        size="sm" 
                        className="mr-2"
                      />
                      <span className="capitalize">{finding.severity}</span>
                    </div>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className="capitalize">{finding.confidence}</span>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {finding.description}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {finding.file}:{finding.line}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 font-mono text-sm">
                    {finding.testId}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Threat Models Table */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Threat Models</h3>
        <div className="rounded-md border">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  ID
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Component
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Category
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Description
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Severity
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {data.threatModels.map((threat, index) => (
                <tr 
                  key={index} 
                  className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                >
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium">
                    {threat.id}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {threat.component}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {threat.category}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {threat.description}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <div className="flex items-center">
                      <StatusIndicator 
                        variant={threat.severity === 'critical' ? 'critical' : threat.severity === 'high' ? 'warning' : threat.severity === 'medium' ? 'warning' : 'healthy'} 
                        size="sm" 
                        className="mr-2"
                      />
                      <span className="capitalize">{threat.severity}</span>
                    </div>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      threat.status === 'Open' ? 'bg-red-100 text-red-800' :
                      threat.status === 'Mitigated' ? 'bg-green-100 text-green-800' :
                      threat.status === 'Accepted' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {threat.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export { SecurityDashboard };