import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface RiskMetrics {
  value_at_risk_95: number;
  max_drawdown: number;
  exposure: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface Position {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl: number;
  stop_loss: number;
}

interface RiskAlert {
  id: string;
  type: 'WARNING' | 'CRITICAL';
  message: string;
  timestamp: string;
}

const RiskDashboard: React.FC = () => {
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics>({
    value_at_risk_95: 0,
    max_drawdown: 0,
    exposure: 0,
    risk_level: 'LOW'
  });

  const [positions, setPositions] = useState<Position[]>([]);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [historicalData, setHistoricalData] = useState<any[]>([]);

  useEffect(() => {
    // Fetch risk metrics from API
    fetchRiskMetrics();
    fetchPositions();
    fetchAlerts();
    fetchHistoricalData();

    // Set up polling for real-time updates
    const interval = setInterval(() => {
      fetchRiskMetrics();
      fetchPositions();
      fetchAlerts();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchRiskMetrics = async () => {
    try {
      const response = await fetch('/api/v1/risk/metrics');
      const data = await response.json();
      setRiskMetrics(data);
    } catch (error) {
      console.error('Error fetching risk metrics:', error);
    }
  };

  const fetchPositions = async () => {
    try {
      const response = await fetch('/api/v1/trading/positions');
      const data = await response.json();
      setPositions(data.positions || []);
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/api/v1/risk/alerts');
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  };

  const fetchHistoricalData = async () => {
    try {
      const response = await fetch('/api/v1/risk/historical');
      const data = await response.json();
      setHistoricalData(data.data || []);
    } catch (error) {
      console.error('Error fetching historical data:', error);
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'bg-green-500';
      case 'MEDIUM': return 'bg-yellow-500';
      case 'HIGH': return 'bg-orange-500';
      case 'CRITICAL': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const totalExposure = positions.reduce((sum, pos) => sum + Math.abs(pos.quantity * pos.current_price), 0);
  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Risk Management Dashboard</h1>
        <Badge className={getRiskLevelColor(riskMetrics.risk_level)}>
          {riskMetrics.risk_level}
        </Badge>
      </div>

      {/* Risk Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Value at Risk (95%)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${riskMetrics.value_at_risk_95.toFixed(2)}</div>
            <p className="text-sm text-muted-foreground">Maximum expected loss</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Maximum Drawdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(riskMetrics.max_drawdown * 100).toFixed(2)}%</div>
            <p className="text-sm text-muted-foreground">Peak-to-trough decline</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Total Exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalExposure.toFixed(2)}</div>
            <p className="text-sm text-muted-foreground">Current market exposure</p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Risk Alerts</h2>
          <div className="space-y-2">
            {alerts.map(alert => (
              <Alert key={alert.id} variant={alert.type === 'CRITICAL' ? 'destructive' : 'default'}>
                <AlertDescription>{alert.message}</AlertDescription>
              </Alert>
            ))}
          </div>
        </div>
      )}

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Current Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-left">Symbol</th>
                  <th className="text-left">Quantity</th>
                  <th className="text-left">Avg Price</th>
                  <th className="text-left">Current Price</th>
                  <th className="text-left">PnL</th>
                  <th className="text-left">Stop Loss</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(pos => (
                  <tr key={pos.symbol}>
                    <td>{pos.symbol}</td>
                    <td>{pos.quantity}</td>
                    <td>${pos.avg_price.toFixed(2)}</td>
                    <td>${pos.current_price.toFixed(2)}</td>
                    <td className={pos.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                      ${pos.pnl.toFixed(2)}
                    </td>
                    <td>${pos.stop_loss.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Historical Risk Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Metrics Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value_at_risk" stroke="#8884d8" name="VaR (95%)" />
              <Line type="monotone" dataKey="max_drawdown" stroke="#82ca9d" name="Max Drawdown