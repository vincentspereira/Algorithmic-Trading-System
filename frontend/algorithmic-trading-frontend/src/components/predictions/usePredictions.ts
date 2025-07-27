import { useState, useEffect, useRef, useCallback } from 'react';

// --- Data Types ---
export interface Prediction {
  ticker: string;
  model_type: string;
  prediction_horizon: number;
  predictions: number[];
  confidence_intervals?: {
    lower: number[];
    upper: number[];
  };
  prediction_dates: string[];
  model_confidence: number;
  feature_importance?: Record<string, number>;
  metadata: Record<string, any>;
}

export interface HistoricalPrediction {
  timestamp: string;
  predictedPrice: number;
  actualPrice?: number;
}

// --- WebSocket and API Configuration ---
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/api/predictions/ws/predictions';

export const usePredictions = (symbols: string[]) => {
  const [realtimeData, setRealtimeData] = useState<Record<string, Prediction>>({});
  const [historicalData, setHistoricalData] = useState<Record<string, HistoricalPrediction[]>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const websocket = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (websocket.current && websocket.current.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(WEBSOCKET_URL);

    ws.onopen = () => {
      console.log('Prediction WebSocket connected');
      setIsConnected(true);
      setError(null);
      // The new backend doesn't require a subscription message, it broadcasts all predictions.
    };

    ws.onmessage = (event) => {
      try {
        const message: Prediction = JSON.parse(event.data);
        if (symbols.includes(message.ticker)) {
          setRealtimeData(prev => ({ ...prev, [message.ticker]: message }));
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
        setError('Error processing prediction data.');
      }
    };

    ws.onclose = () => {
      console.log('Prediction WebSocket disconnected. Reconnecting...');
      setIsConnected(false);
      setTimeout(connect, 5000); // Reconnect after 5 seconds
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('WebSocket connection error.');
      ws.close();
    };

    websocket.current = ws;
  }, [JSON.stringify(symbols)]);

  useEffect(() => {
    connect();

    const fetchHistorical = async (symbol: string) => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/predictions/history/${symbol}?limit=100`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        setHistoricalData(prev => ({ ...prev, [symbol]: result.data }));
      } catch (err) {
        console.error(`Failed to fetch historical data for ${symbol}:`, err);
        setError(`Failed to fetch history for ${symbol}.`);
      }
    };

    symbols.forEach(fetchHistorical);

    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
    };
  }, [connect, JSON.stringify(symbols)]);

  return { realtimeData, historicalData, isConnected, error };
};