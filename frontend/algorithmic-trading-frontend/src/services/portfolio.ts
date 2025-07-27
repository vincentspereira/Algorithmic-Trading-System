import { PortfolioValue } from '@/types/portfolio';

export const getPortfolioValue = async (): Promise<PortfolioValue> => {
  // Mock data for now
  return Promise.resolve({ value: 100000 });
};