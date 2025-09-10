import React from 'react';
import { StatusIndicator } from '@/components/atoms/StatusIndicator';
import { cn } from '@/lib/utils';

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  unit?: string;
  status?: 'healthy' | 'warning' | 'critical';
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
}

const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  ({ 
    className, 
    title, 
    value, 
    unit, 
    status, 
    trend, 
    description,
    ...props 
  }, ref) => {
    return (
      <div 
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm p-6',
          className
        )}
        ref={ref}
        {...props}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          {status && (
            <StatusIndicator 
              variant={status === 'healthy' ? 'healthy' : status === 'warning' ? 'warning' : 'critical'} 
              size="sm" 
            />
          )}
        </div>
        <div className="mt-2">
          <p className="text-2xl font-bold">
            {value}
            {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
          </p>
        </div>
        {description && (
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        )}
        {trend && (
          <div className="mt-2 flex items-center">
            <span className={cn(
              'text-xs',
              trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-muted-foreground'
            )}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} 2.5%
            </span>
            <span className="text-xs text-muted-foreground ml-1">from last week</span>
          </div>
        )}
      </div>
    );
  }
);

MetricCard.displayName = 'MetricCard';

export { MetricCard };