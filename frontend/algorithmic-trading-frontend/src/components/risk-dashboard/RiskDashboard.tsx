import React, { useState, useEffect } from 'react';
import { Card, CardContent, Chip } from '@mui/material';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
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


  const totalExposure = positions.reduce((sum, pos) => sum + Math.abs(pos.quantity * pos.current_price), 0);
  const totalPnL = positions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Risk Management Dashboard</h1>
        <Chip 
          label={riskMetrics.risk_level}
          color={riskMetrics.risk_level === 'LOW' ? 'success' : 
                 riskMetrics.risk_level === 'MEDIUM' ? 'warning' : 
                 riskMetrics.risk_level === 'HIGH' ? 'error' : 
                 'error'}
        />
      </div>

      {/* Risk Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Value at Risk (95%)</Typography>
            <Typography variant="h4">${riskMetrics.value_at_risk_95.toFixed(2)}</Typography>
            <Typography variant="body2" color="textSecondary">Maximum expected loss</Typography>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Maximum Drawdown</Typography>
            <Typography variant="h4">{(riskMetrics.max_drawdown * 100).toFixed(2)}%</Typography>
            <Typography variant="body2" color="textSecondary">Peak-to-trough decline</Typography>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Total Exposure</Typography>
            <Typography variant="h4">${totalExposure.toFixed(2)}</Typography>
            <Typography variant="body2" color="textSecondary">Current market exposure</Typography>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <div>
          <Typography variant="h5" gutterBottom>Risk Alerts</Typography>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {alerts.map(alert => (
              <Alert key={alert.id} severity={alert.type === 'CRITICAL' ? 'error' : 'warning'}>
                <AlertTitle>{alert.type}</AlertTitle>
                {alert.message}
              </Alert>
            ))}
          </div>
        </div>
      )}

      {/* Positions Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Current Positions</Typography>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left' }}>Symbol</th>
                  <th style={{ textAlign: 'left' }}>Quantity</th>
                  <th style={{ textAlign: 'left' }}>Avg Price</th>
                  <th style={{ textAlign: 'left' }}>Current Price</th>
                  <th style={{ textAlign: 'left' }}>PnL</th>
                  <th style={{ textAlign: 'left' }}>Stop Loss</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(pos => (
                  <tr key={pos.symbol}>
                    <td>{pos.symbol}</td>
                    <td>{pos.quantity}</td>
                    <td>${pos.avg_price.toFixed(2)}</td>
                    <td>${pos.current_price.toFixed(2)}</td>
                    <td style={{ color: pos.pnl >= 0 ? '#4caf50' : '#f44336' }}>
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
        <CardContent>
          <Typography variant="h6" gutterBottom>Risk Metrics Over Time</Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value_at_risk" stroke="#8884d8" name="VaR (95%)" />
              <Line type="monotone" dataKey="max_drawdown" stroke="#82ca9d" name="Max Drawdown" />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};

export default RiskDashboard;