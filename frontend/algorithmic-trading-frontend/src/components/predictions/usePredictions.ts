import { useState, useEffect, useRef, useCallback } from 'react';

// --- Data Types ---
export interface Prediction {
  ticker: string;
  model_type: string;
  prediction_horizon: number; // This is a single value, not an array of horizons
  predictions: number[]; // This array contains predictions for various horizons
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

// Define the structure expected by PredictionWidget
export interface WidgetPrediction {
  prediction: number;
  confidence: number;
}

export interface PredictionsData {
  '1min'?: WidgetPrediction;
  '5min'?: WidgetPrediction;
  '15min'?: WidgetPrediction;
  // Add other horizons if needed based on backend configuration
}

// --- WebSocket and API Configuration ---
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WEBSOCKET_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/api/predictions/ws/predictions';

// Helper function to transform backend Prediction to frontend PredictionsData
const transformPredictionToWidgetData = (prediction: Prediction): PredictionsData => {
  const horizons = prediction.metadata?.prediction_horizons || [1, 5, 15]; // Default horizons if not in metadata
  const transformed: PredictionsData = {};

  horizons.forEach((horizon, index) => {
    if (prediction.predictions && prediction.predictions[index] !== undefined) {
      transformed[`${horizon}min` as keyof PredictionsData] = {
        prediction: prediction.predictions[index],
        confidence: prediction.model_confidence, // Assuming overall model confidence applies to all horizons
      };
    }
  });
  return transformed;
};

export const usePredictions = (symbols: string[]) => {
  const [realtimeData, setRealtimeData] = useState<Record<string, { predictions: PredictionsData, lastUpdated: string }>>({});
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
          const transformedData = transformPredictionToWidgetData(message);
          setRealtimeData(prev => ({
            ...prev,
            [message.ticker]: {
              predictions: transformedData,
              lastUpdated: new Date().toISOString()
            }
          }));
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