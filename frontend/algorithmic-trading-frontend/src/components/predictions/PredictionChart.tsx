"use client";

import React from 'react';
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
  TimeScale,
  ChartOptions,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface HistoricalPrediction {
  timestamp: string;
  actualPrice?: number;
  predictedPrice: number;
}

interface PredictionChartProps {
  symbol: string;
  data: HistoricalPrediction[];
}

const PredictionChart: React.FC<PredictionChartProps> = ({ symbol, data }) => {
  const chartData = {
    labels: data.map(d => new Date(d.timestamp)),
    datasets: [
      {
        label: `${symbol} Predicted Price`,
        data: data.map(d => d.predictedPrice),
        borderColor: 'rgba(255, 159, 64, 1)',
        backgroundColor: 'rgba(255, 159, 64, 0.2)',
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.1,
      },
      {
        label: `${symbol} Actual Price`,
        data: data.map(d => d.actualPrice),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.1,
      },
    ],
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#ffffff',
        },
      },
      title: {
        display: true,
        text: `${symbol} - Predicted vs. Actual Prices`,
        color: '#ffffff',
        font: {
          size: 16,
        },
      },
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'minute',
          tooltipFormat: 'PP pp',
        },
        title: {
          display: true,
          text: 'Time',
          color: '#ffffff',
        },
        ticks: {
          color: '#ffffff',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Price (USD)',
          color: '#ffffff',
        },
        ticks: {
          color: '#ffffff',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
      },
    },
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
      <Line options={options} data={chartData} />
    </div>
  );
};

// Mock data for demonstration
const generateMockData = (points = 30): HistoricalPrediction[] => {
  const data: HistoricalPrediction[] = [];
  let lastPrice = 150 + Math.random() * 10;
  for (let i = points - 1; i >= 0; i--) {
    const date = new Date();
    date.setMinutes(date.getMinutes() - i);
    
    lastPrice += (Math.random() - 0.5) * 2;
    const predictedPrice = lastPrice * (1 + (Math.random() - 0.5) * 0.02);
    
    data.push({
      timestamp: date.toISOString(),
      actualPrice: lastPrice,
      predictedPrice: predictedPrice,
    });
  }
  return data;
};

export const MockPredictionChart: React.FC = () => {
    const mockData = generateMockData();
    return (
        <div className="p-8 bg-gray-900">
            <PredictionChart symbol="TSLA" data={mockData} />
        </div>
    );
};

export default PredictionChart;