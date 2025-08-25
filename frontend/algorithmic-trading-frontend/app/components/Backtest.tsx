'use client';

import { useState, useEffect } from 'react';
import {
    Button,
    Card,
    Grid,
    Select,
    TextField,
    Typography
} from '@mui/material';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from 'recharts';

interface BacktestProps {
    symbol: string;
    startDate: string;
    endDate: string;
    timeframe: string;
    fastMa: number;
    slowMa: number;
}

interface Trade {
    timestamp: string;
    side: 'BUY' | 'SELL';
    quantity: number;
    price: number;
    pnl: number;
}

interface EquityPoint {
    timestamp: string;
    equity: number;
}

interface Metrics {
    totalReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
}

interface BacktestResults {
    metrics: Metrics;
    trades: Trade[];
    equityCurve: EquityPoint[];
}

export default function BacktestComponent() {
    // State
    const [loading, setLoading] = useState(false);
    const [connected, setConnected] = useState(false);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [requestId, setRequestId] = useState<string | null>(null);
    const [results, setResults] = useState<BacktestResults | null>(null);
    const [error, setError] = useState<string | null>(null);
    
    // Form state
    const [params, setParams] = useState<BacktestProps>({
        symbol: 'AAPL',
        startDate: '2025-01-01',
        endDate: '2025-08-24',
        timeframe: '1d',
        fastMa: 20,
        slowMa: 50
    });
    
    // WebSocket setup
    useEffect(() => {
        if (requestId && !socket) {
            const ws = new WebSocket(
                `ws://localhost:8000/ws/backtest/${requestId}`
            );
            
            ws.onopen = () => {
                setConnected(true);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.status === 'COMPLETED') {
                    setResults(data.results);
                    setLoading(false);
                } else if (data.status === 'FAILED') {
                    setError(data.error);
                    setLoading(false);
                }
            };
            
            ws.onclose = () => {
                setConnected(false);
            };
            
            setSocket(ws);
            
            return () => {
                ws.close();
            };
        }
    }, [requestId]);
    
    // Handle form submission
    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError(null);
            setResults(null);
            
            const response = await fetch(
                'http://localhost:8000/api/backtest',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        strategy: {
                            symbol: params.symbol,
                            start_date: params.startDate,
                            end_date: params.endDate,
                            timeframe: params.timeframe,
                            fast_ma: params.fastMa,
                            slow_ma: params.slowMa
                        }
                    })
                }
            );
            
            const data = await response.json();
            setRequestId(data.request_id);
            
        } catch (err) {
            setError(err.message);
            setLoading(false);
        }
    };
    
    return (
        <div className="container mx-auto p-4">
            <Typography variant="h4" className="mb-4">
                MA Crossover Backtest
            </Typography>
            
            {/* Parameters Form */}
            <Card className="p-4 mb-4">
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                        <TextField
                            fullWidth
                            label="Symbol"
                            value={params.symbol}
                            onChange={(e) => setParams({
                                ...params,
                                symbol: e.target.value
                            })}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                        <Select
                            fullWidth
                            label="Timeframe"
                            value={params.timeframe}
                            onChange={(e) => setParams({
                                ...params,
                                timeframe: e.target.value
                            })}
                        >
                            <option value="1m">1 Minute</option>
                            <option value="5m">5 Minutes</option>
                            <option value="15m">15 Minutes</option>
                            <option value="1h">1 Hour</option>
                            <option value="4h">4 Hours</option>
                            <option value="1d">1 Day</option>
                        </Select>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                        <TextField
                            fullWidth
                            type="date"
                            label="Start Date"
                            value={params.startDate}
                            onChange={(e) => setParams({
                                ...params,
                                startDate: e.target.value
                            })}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                        <TextField
                            fullWidth
                            type="date"
                            label="End Date"
                            value={params.endDate}
                            onChange={(e) => setParams({
                                ...params,
                                endDate: e.target.value
                            })}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                        <TextField
                            fullWidth
                            type="number"
                            label="Fast MA Period"
                            value={params.fastMa}
                            onChange={(e) => setParams({
                                ...params,
                                fastMa: parseInt(e.target.value)
                            })}
                        />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                        <TextField
                            fullWidth
                            type="number"
                            label="Slow MA Period"
                            value={params.slowMa}
                            onChange={(e) => setParams({
                                ...params,
                                slowMa: parseInt(e.target.value)
                            })}
                        />
                    </Grid>
                </Grid>
                
                <Button
                    variant="contained"
                    color="primary"
                    onClick={handleSubmit}
                    disabled={loading}
                    className="mt-4"
                >
                    {loading ? 'Running...' : 'Run Backtest'}
                </Button>
            </Card>
            
            {/* Results */}
            {results && (
                <div>
                    {/* Metrics */}
                    <Card className="p-4 mb-4">
                        <Typography variant="h6" className="mb-2">
                            Performance Metrics
                        </Typography>
                        <Grid container spacing={2}>
                            <Grid item xs={6} sm={3}>
                                <Typography variant="subtitle2">
                                    Total Return
                                </Typography>
                                <Typography>
                                    {(results.metrics.totalReturn * 100).toFixed(2)}%
                                </Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                <Typography variant="subtitle2">
                                    Sharpe Ratio
                                </Typography>
                                <Typography>
                                    {results.metrics.sharpeRatio.toFixed(2)}
                                </Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                <Typography variant="subtitle2">
                                    Max Drawdown
                                </Typography>
                                <Typography>
                                    {(results.metrics.maxDrawdown * 100).toFixed(2)}%
                                </Typography>
                            </Grid>
                            <Grid item xs={6} sm={3}>
                                <Typography variant="subtitle2">
                                    Win Rate
                                </Typography>
                                <Typography>
                                    {(results.metrics.winRate * 100).toFixed(2)}%
                                </Typography>
                            </Grid>
                        </Grid>
                    </Card>
                    
                    {/* Equity Curve */}
                    <Card className="p-4 mb-4">
                        <Typography variant="h6" className="mb-2">
                            Equity Curve
                        </Typography>
                        <LineChart
                            width={800}
                            height={400}
                            data={results.equityCurve}
                            margin={{
                                top: 5,
                                right: 30,
                                left: 20,
                                bottom: 5
                            }}
                        >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="timestamp"
                                tickFormatter={(ts) => new Date(ts).toLocaleDateString()}
                            />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="equity"
                                stroke="#8884d8"
                                activeDot={{ r: 8 }}
                            />
                        </LineChart>
                    </Card>
                    
                    {/* Trade List */}
                    <Card className="p-4">
                        <Typography variant="h6" className="mb-2">
                            Trade History
                        </Typography>
                        <div className="overflow-x-auto">
                            <table className="min-w-full">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Side</th>
                                        <th>Quantity</th>
                                        <th>Price</th>
                                        <th>P&L</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.trades.map((trade, index) => (
                                        <tr key={index}>
                                            <td>{new Date(trade.timestamp).toLocaleString()}</td>
                                            <td>{trade.side}</td>
                                            <td>{trade.quantity}</td>
                                            <td>${trade.price.toFixed(2)}</td>
                                            <td
                                                className={
                                                    trade.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                                                }
                                            >
                                                ${trade.pnl.toFixed(2)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                </div>
            )}
            
            {/* Error Display */}
            {error && (
                <Typography color="error" className="mt-4">
                    Error: {error}
                </Typography>
            )}
        </div>
    );
}
