'use client';

import React from 'react';
import { Button, IconButton, Tooltip } from '@mui/material';
import { Logout as LogoutIcon } from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

interface LogoutButtonProps {
  variant?: 'text' | 'outlined' | 'contained';
  size?: 'small' | 'medium' | 'large';
  iconOnly?: boolean;
  className?: string;
}

const LogoutButton: React.FC<LogoutButtonProps> = ({ 
  variant = 'outlined', 
  size = 'medium',
  iconOnly = false,
  className 
}) => {
  const { logout, isLoading } = useAuth();

  const handleLogout = () => {
    logout();
  };

  if (iconOnly) {
    return (
      <Tooltip title="Sign Out">
        <IconButton
          onClick={handleLogout}
          disabled={isLoading}
          size={size}
          className={className}
          sx={{
            color: 'text.secondary',
            '&:hover': {
              color: 'error.main',
            },
          }}
        >
          <LogoutIcon />
        </IconButton>
      </Tooltip>
    );
  }

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleLogout}
      disabled={isLoading}
      startIcon={<LogoutIcon />}
      className={className}
      sx={{
        textTransform: 'none',
        fontWeight: 500,
        color: 'error.main',
        borderColor: 'error.main',
        '&:hover': {
          borderColor: 'error.dark',
          backgroundColor: 'error.main',
          color: 'error.contrastText',
        },
      }}
    >
      Sign Out
    </Button>
  );
};

export default LogoutButton;