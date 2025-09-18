'use client';

import React from 'react';
import { Button } from '@mui/material';
import { Login as LoginIcon } from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

interface LoginButtonProps {
  variant?: 'text' | 'outlined' | 'contained';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  className?: string;
}

const LoginButton: React.FC<LoginButtonProps> = ({ 
  variant = 'contained', 
  size = 'medium',
  fullWidth = false,
  className 
}) => {
  const { login, isLoading } = useAuth();

  const handleLogin = () => {
    login();
  };

  return (
    <Button
      variant={variant}
      size={size}
      fullWidth={fullWidth}
      onClick={handleLogin}
      disabled={isLoading}
      startIcon={<LoginIcon />}
      className={className}
      sx={{
        textTransform: 'none',
        fontWeight: 500,
      }}
    >
      {isLoading ? 'Loading...' : 'Sign In'}
    </Button>
  );
};

export default LoginButton;