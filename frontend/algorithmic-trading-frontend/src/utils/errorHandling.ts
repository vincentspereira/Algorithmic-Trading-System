import axios from 'axios';

interface ApiError {
  message: string;
  code?: number;
}

export const parseApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const apiError = error.response?.data as ApiError;
    if (apiError?.message) {
      return apiError.message;
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
};

export const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  // Placeholder for toast notifications (e.g., using react-hot-toast)
  console.log(`Toast (${type}):`, message);
};