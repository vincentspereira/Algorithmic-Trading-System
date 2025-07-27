import { useState, useEffect, useCallback } from 'react';
import { getPortfolio } from '../lib/api';
import { Portfolio } from '../types/api';

export const usePortfolio = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchPortfolio = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getPortfolio();
      setPortfolio(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch portfolio'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [fetchPortfolio]);

  return { portfolio, isLoading, error, refetch: fetchPortfolio };
};