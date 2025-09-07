/**
 * TradingModeSwitch.tsx
 * 
 * Next.js component for seamless trading mode switching between paper and live trading.
 * Provides a secure interface with proper validation and confirmation dialogs.
 */

import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { 
  Button 
} from '@/components/ui/button';
import { 
  Badge 
} from '@/components/ui/badge';
import { 
  Alert, 
  AlertDescription 
} from '@/components/ui/alert';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { 
  Switch 
} from '@/components/ui/switch';
import { 
  Loader2, 
  AlertTriangle, 
  CheckCircle, 
  XCircle 
} from 'lucide-react';

interface TradingMode {
  mode: 'paper' | 'live' | 'simulation';
  isRunning: boolean;
  lastSwitched: string;
  riskLimits: {
    maxPositionSize: number;
    maxDailyLoss: number;
    maxOrdersPerMinute: number;
  };
}

interface ValidationStatus {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

const TradingModeSwitch: React.FC = () => {
  const [currentMode, setCurrentMode] = useState<TradingMode>({
    mode: 'paper',
    isRunning: false,
    lastSwitched: new Date().toISOString(),
    riskLimits: {
      maxPositionSize: 1000000,
      maxDailyLoss: 50000,
      maxOrdersPerMinute: 100
    }
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>({
    isValid: true,
    errors: [],
    warnings: []
  });
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [targetMode, setTargetMode] = useState<'paper' | 'live'>('paper');

  // Fetch current trading mode status
  useEffect(() => {
    fetchTradingModeStatus();
    const interval = setInterval(fetchTradingModeStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchTradingModeStatus = async () => {
    try {
      const response = await fetch('/api/trading/mode/status');
      if (response.ok) {
        const data = await response.json();
        setCurrentMode(data);
      }
    } catch (error) {
      console.error('Failed to fetch trading mode status:', error);
    }
  };

  const validateModeSwitch = async (newMode: 'paper' | 'live'): Promise<ValidationStatus> => {
    try {
      const response = await fetch('/api/trading/mode/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ targetMode: newMode }),
      });
      
      if (response.ok) {
        return await response.json();
      } else {
        return {
          isValid: false,
          errors: ['Failed to validate mode switch'],
          warnings: []
        };
      }
    } catch (error) {
      return {
        isValid: false,
        errors: [`Validation error: ${error}`],
        warnings: []
      };
    }
  };

  const handleModeSwitch = async (newMode: 'paper' | 'live') => {
    setIsLoading(true);
    
    try {
      // Validate the switch first
      const validation = await validateModeSwitch(newMode);
      setValidationStatus(validation);
      
      if (!validation.isValid) {
        setIsLoading(false);
        return;
      }
      
      // If switching to live mode, show confirmation dialog
      if (newMode === 'live' && currentMode.mode !== 'live') {
        setTargetMode(newMode);
        setShowConfirmDialog(true);
        setIsLoading(false);
        return;
      }
      
      // Perform the actual switch
      await performModeSwitch(newMode);
      
    } catch (error) {
      console.error('Mode switch failed:', error);
      setValidationStatus({
        isValid: false,
        errors: [`Mode switch failed: ${error}`],
        warnings: []
      });
    } finally {
      setIsLoading(false);
    }
  };

  const performModeSwitch = async (newMode: 'paper' | 'live') => {
    const response = await fetch('/api/trading/mode/switch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        targetMode: newMode,
        force: false 
      }),
    });
    
    if (response.ok) {
      const result = await response.json();
      if (result.success) {
        await fetchTradingModeStatus();
        setValidationStatus({
          isValid: true,
          errors: [],
          warnings: []
        });
      } else {
        setValidationStatus({
          isValid: false,
          errors: [result.error || 'Mode switch failed'],
          warnings: []
        });
      }
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  };

  const confirmLiveModeSwitch = async () => {
    setShowConfirmDialog(false);
    setIsLoading(true);
    
    try {
      await performModeSwitch(targetMode);
    } catch (error) {
      console.error('Live mode switch failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'live': return 'bg-red-500';
      case 'paper': return 'bg-blue-500';
      case 'simulation': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusColor = (isRunning: boolean) => {
    return isRunning ? 'bg-green-500' : 'bg-yellow-500';
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Trading Mode Control
            <div className="flex items-center space-x-2">
              <Badge className={getModeColor(currentMode.mode)}>
                {currentMode.mode.toUpperCase()}
              </Badge>
              <Badge className={getStatusColor(currentMode.isRunning)}>
                {currentMode.isRunning ? 'RUNNING' : 'STOPPED'}
              </Badge>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Mode Switch Controls */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="space-y-1">
              <h3 className="font-medium">Paper Trading</h3>
              <p className="text-sm text-gray-600">
                Safe environment for testing strategies
              </p>
            </div>
            <Switch
              checked={currentMode.mode === 'paper'}
              onCheckedChange={() => handleModeSwitch('paper')}
              disabled={isLoading}
            />
          </div>
          
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="space-y-1">
              <h3 className="font-medium flex items-center">
                Live Trading
                <AlertTriangle className="ml-2 h-4 w-4 text-red-500" />
              </h3>
              <p className="text-sm text-gray-600">
                Real money trading - use with caution
              </p>
            </div>
            <Switch
              checked={currentMode.mode === 'live'}
              onCheckedChange={() => handleModeSwitch('live')}
              disabled={isLoading}
            />
          </div>

          {/* Risk Limits Display */}
          <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                ${(currentMode.riskLimits.maxPositionSize / 1000).toFixed(0)}K
              </div>
              <div className="text-sm text-gray-600">Max Position</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                ${(currentMode.riskLimits.maxDailyLoss / 1000).toFixed(0)}K
              </div>
              <div className="text-sm text-gray-600">Max Daily Loss</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {currentMode.riskLimits.maxOrdersPerMinute}
              </div>
              <div className="text-sm text-gray-600">Orders/Min</div>
            </div>
          </div>

          {/* Validation Status */}
          {!validationStatus.isValid && (
            <Alert className="border-red-200 bg-red-50">
              <XCircle className="h-4 w-4 text-red-600" />
              <AlertDescription>
                <div className="space-y-1">
                  {validationStatus.errors.map((error, index) => (
                    <div key={index} className="text-red-700">{error}</div>
                  ))}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {validationStatus.warnings.length > 0 && (
            <Alert className="border-yellow-200 bg-yellow-50">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertDescription>
                <div className="space-y-1">
                  {validationStatus.warnings.map((warning, index) => (
                    <div key={index} className="text-yellow-700">{warning}</div>
                  ))}
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span>Switching trading mode...</span>
            </div>
          )}

          {/* Last Switched Info */}
          <div className="text-sm text-gray-500 text-center">
            Last switched: {new Date(currentMode.lastSwitched).toLocaleString()}
          </div>
        </CardContent>
      </Card>

      {/* Live Mode Confirmation Dialog */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
              Confirm Live Trading Mode
            </DialogTitle>
            <DialogDescription>
              You are about to switch to live trading mode. This will use real money 
              and execute actual trades. Please confirm that you understand the risks.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <Alert className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription>
                <strong>Warning:</strong> Live trading involves real financial risk. 
                Ensure your strategies have been thoroughly tested in paper trading mode.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <h4 className="font-medium">Risk Limits for Live Mode:</h4>
              <ul className="text-sm space-y-1 text-gray-600">
                <li>• Max Position Size: $100,000</li>
                <li>• Max Daily Loss: $5,000</li>
                <li>• Max Orders per Minute: 10</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowConfirmDialog(false)}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={confirmLiveModeSwitch}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              Confirm Live Trading
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TradingModeSwitch;