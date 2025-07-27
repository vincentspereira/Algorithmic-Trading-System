import { useState, useEffect, useCallback } from 'react';
import { getMarketData } from '../lib/api';
import { MarketData } from '../types/api';

export const useMarketData = (symbol: string) => {
  const [data, setData] = useState<MarketData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchMarketData = useCallback(async () => {
    if (!symbol) return;

    try {
      setIsLoading(true);
      const marketData = await getMarketData(symbol);
      setData((prevData) => [...prevData, marketData]);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch market data'));
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [fetchMarketData]);

  return { data, isLoading, error };
};