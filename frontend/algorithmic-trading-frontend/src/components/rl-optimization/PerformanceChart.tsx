// frontend/algorithmic-trading-frontend/src/components/rl-optimization/PerformanceChart.tsx

import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface PerformanceChartProps {
    modelId: string;
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ modelId }) => {
    const [chartData, setChartData] = useState<any>(null);

    useEffect(() => {
        const fetchPerformanceData = async () => {
            if (!modelId) return;
            try {
                // This is a mock API call.
                // In a real application, you would fetch backtest results for the model.
                const response = await fetch(`/api/rl/backtest`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model_id: modelId,
                        instrument_id: 'BTC/USD',
                        start_date: '2023-01-01',
                        end_date: '2024-01-01',
                    }),
                });
                const data = await response.json();
                
                // Mock data for plotting
                const mockLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
                const mockPerformance = [1.0, 1.05, 1.02, 1.1, 1.15, 1.2];

                setChartData({
                    labels: mockLabels,
                    datasets: [
                        {
                            label: `Performance of ${modelId}`,
                            data: mockPerformance,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1,
                        },
                    ],
                });
            } catch (error) {
                console.error("Failed to fetch performance data:", error);
            }
        };

        fetchPerformanceData();
    }, [modelId]);

    if (!chartData) {
        return <p>Loading performance data...</p>;
    }

    return <Line data={chartData} />;
};

export default PerformanceChart;