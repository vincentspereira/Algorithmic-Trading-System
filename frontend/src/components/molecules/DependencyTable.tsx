import React from 'react';
import { StatusIndicator } from '@/components/atoms/StatusIndicator';

export interface Dependency {
  name: string;
  tier: number;
  version: string;
  status: 'healthy' | 'warning' | 'critical';
  lastUpdate: string;
  uptime: number;
  latency: number;
  vulnerabilities: number;
}

export interface DependencyTableProps extends React.HTMLAttributes<HTMLDivElement> {
  dependencies: Dependency[];
}

const DependencyTable = React.forwardRef<HTMLDivElement, DependencyTableProps>(
  ({ className, dependencies, ...props }, ref) => {
    const getStatusVariant = (status: string) => {
      switch (status) {
        case 'healthy': return 'healthy';
        case 'warning': return 'warning';
        case 'critical': return 'critical';
        default: return 'default';
      }
    };

    const formatLatency = (latency: number) => {
      return `${(latency * 1000).toFixed(1)}ms`;
    };

    const formatUptime = (uptime: number) => {
      return `${(uptime * 100).toFixed(2)}%`;
    };

    return (
      <div className={className} ref={ref} {...props}>
        <div className="rounded-md border">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Dependency
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Tier
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Version
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Status
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Last Update
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Uptime
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Latency
                </th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                  Vulnerabilities
                </th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {dependencies.map((dep, index) => (
                <tr 
                  key={index} 
                  className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted"
                >
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 font-medium">
                    {dep.name}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                      Tier {dep.tier}
                    </span>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    {dep.version}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <div className="flex items-center">
                      <StatusIndicator 
                        variant={getStatusVariant(dep.status)} 
                        size="sm" 
                        className="mr-2"
                      />
                      <span className="capitalize">{dep.status}</span>
                    </div>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0 text-muted-foreground">
                    {dep.lastUpdate}
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className={dep.uptime > 0.99 ? 'text-green-600' : dep.uptime > 0.95 ? 'text-yellow-600' : 'text-red-600'}>
                      {formatUptime(dep.uptime)}
                    </span>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className={dep.latency < 0.05 ? 'text-green-600' : dep.latency < 0.1 ? 'text-yellow-600' : 'text-red-600'}>
                      {formatLatency(dep.latency)}
                    </span>
                  </td>
                  <td className="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                    <span className={dep.vulnerabilities === 0 ? 'text-green-600' : dep.vulnerabilities < 5 ? 'text-yellow-600' : 'text-red-600'}>
                      {dep.vulnerabilities}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
);

DependencyTable.displayName = 'DependencyTable';

export { DependencyTable };