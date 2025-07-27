import { RealtimePrediction, HistoricalPrediction } from '@/components/predictions/usePredictions';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/predictions';

interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
}

/**
 * Fetches the latest real-time prediction for a given symbol.
 * @param symbol The stock symbol to fetch.
 * @returns A promise that resolves to the real-time prediction data.
 */
export const getRealtimePrediction = async (symbol: string): Promise<RealtimePrediction> => {
  try {
    const response = await fetch(`${API_BASE_URL}/realtime/${symbol}`);
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    const result: ApiResponse<RealtimePrediction> = await response.json();
    if (result.status === 'error' || !result.data) {
      throw new Error(result.message || 'Failed to fetch real-time prediction.');
    }
    return result.data;
  } catch (error) {
    console.error(`Error fetching real-time prediction for ${symbol}:`, error);
    // Return a mock error response or rethrow
    throw error;
  }
};

/**
 * Fetches historical prediction data for a given symbol.
 * @param symbol The stock symbol to fetch.
 * @param limit The number of data points to retrieve.
 * @returns A promise that resolves to an array of historical predictions.
 */
export const getHistoricalPredictions = async (symbol: string, limit: number = 100): Promise<HistoricalPrediction[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${symbol}?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    const result: ApiResponse<HistoricalPrediction[]> = await response.json();
    if (result.status === 'error' || !result.data) {
      throw new Error(result.message || 'Failed to fetch historical predictions.');
    }
    return result.data;
  } catch (error) {
    console.error(`Error fetching historical predictions for ${symbol}:`, error);
    throw error;
  }
};


/**
 * Fetches the model's accuracy metrics.
 * @returns A promise that resolves to the accuracy data.
 */
export const getModelAccuracy = async (): Promise<any> => {
    try {
      const response = await fetch(`${API_BASE_URL}/accuracy`);
      if (!response.ok) {
        throw new Error(`API call failed with status: ${response.status}`);
      }
      const result: ApiResponse<any> = await response.json();
      if (result.status === 'error' || !result.data) {
        throw new Error(result.message || 'Failed to fetch model accuracy.');
      }
      return result.data;
    } catch (error) {
      console.error('Error fetching model accuracy:', error);
      throw error;
    }
};

// WebSocket logic is handled by the usePredictions hook, 
// but this service could be expanded to include more complex API interactions.