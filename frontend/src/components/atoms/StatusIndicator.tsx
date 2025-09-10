import React from 'react';
import { cn } from '@/lib/utils';

export interface StatusIndicatorProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'healthy' | 'warning' | 'critical';
  size?: 'sm' | 'md' | 'lg';
}

const StatusIndicator = React.forwardRef<HTMLSpanElement, StatusIndicatorProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    const baseClasses = 'inline-flex items-center justify-center rounded-full';
    
    const variantClasses = {
      default: 'bg-gray-200',
      healthy: 'bg-green-500',
      warning: 'bg-yellow-500',
      critical: 'bg-red-500',
    };
    
    const sizeClasses = {
      sm: 'w-3 h-3',
      md: 'w-4 h-4',
      lg: 'w-5 h-5',
    };
    
    return (
      <span
        className={cn(baseClasses, variantClasses[variant], sizeClasses[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);

StatusIndicator.displayName = 'StatusIndicator';

export { StatusIndicator };