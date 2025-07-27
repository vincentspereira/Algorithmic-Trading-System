import { useState, useEffect, useCallback } from 'react';
import { getOrderHistory, submitOrder } from '../lib/api';
import { Order } from '../types/api';

export const useOrders = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchOrderHistory = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getOrderHistory();
      setOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch order history'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSubmtiOrder = async (orderData: Omit<Order, 'id' | 'timestamp' | 'status'>) => {
    try {
        const newOrder = await submitOrder(orderData);
        setOrders((prevOrders) => [newOrder, ...prevOrders]);
    } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to submit order'));
        throw err;
    }
  };

  useEffect(() => {
    fetchOrderHistory();
  }, [fetchOrderHistory]);

  return { orders, isLoading, error, submitOrder: handleSubmtiOrder, refetch: fetchOrderHistory };
};