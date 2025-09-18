'use client';

import React, { useState } from 'react';
import {
  Box,
  Button,
  Menu,
  MenuItem,
  Avatar,
  Typography,
  Divider,
  ListItemIcon,
  CircularProgress,
  Chip
} from '@mui/material';
import {
  Person as PersonIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import LoginButton from './LoginButton';

interface AuthStatusProps {
  showUserInfo?: boolean;
  variant?: 'header' | 'sidebar' | 'compact';
}

const AuthStatus: React.FC<AuthStatusProps> = ({ 
  showUserInfo = true, 
  variant = 'header' 
}) => {
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    handleClose();
    logout();
  };

  const getInitials = (firstName?: string, lastName?: string, username?: string) => {
    if (firstName && lastName) {
      return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
    }
    if (username) {
      return username.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  const getPrimaryRole = () => {
    if (!user?.roles || user.roles.length === 0) return null;
    
    // Prioritize roles
    const rolePriority = ['admin', 'trader', 'analyst', 'viewer'];
    for (const role of rolePriority) {
      if (user.roles.includes(role)) {
        return role;
      }
    }
    return user.roles[0];
  };

  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        <CircularProgress size={20} />
        <Typography variant="body2" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <LoginButton variant={variant === 'compact' ? 'outlined' : 'contained'} />;
  }

  if (variant === 'compact') {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        <Avatar
          sx={{ width: 32, height: 32, fontSize: '0.875rem' }}
          onClick={handleClick}
        >
          {getInitials(user?.firstName, user?.lastName, user?.username)}
        </Avatar>
        <Menu
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          onClick={handleClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon fontSize="small" />
            </ListItemIcon>
            Sign Out
          </MenuItem>
        </Menu>
      </Box>
    );
  }

  return (
    <Box display="flex" alignItems="center" gap={2}>
      {showUserInfo && user && (
        <Box display="flex" alignItems="center" gap={1}>
          <Avatar
            sx={{ 
              width: variant === 'sidebar' ? 40 : 36, 
              height: variant === 'sidebar' ? 40 : 36,
              fontSize: variant === 'sidebar' ? '1rem' : '0.875rem'
            }}
          >
            {getInitials(user.firstName, user.lastName, user.username)}
          </Avatar>
          
          <Box>
            <Typography 
              variant={variant === 'sidebar' ? 'body1' : 'body2'} 
              fontWeight={500}
              noWrap
            >
              {user.firstName && user.lastName 
                ? `${user.firstName} ${user.lastName}`
                : user.username
              }
            </Typography>
            
            {variant === 'sidebar' && (
              <Box display="flex" alignItems="center" gap={1}>
                {getPrimaryRole() && (
                  <Chip
                    label={getPrimaryRole()}
                    size="small"
                    variant="outlined"
                    sx={{ height: 20, fontSize: '0.75rem' }}
                  />
                )}
              </Box>
            )}
          </Box>
        </Box>
      )}
      
      <Button
        onClick={handleClick}
        endIcon={<ExpandMoreIcon />}
        sx={{ 
          textTransform: 'none',
          color: 'text.primary',
          minWidth: 'auto'
        }}
      >
        {variant === 'header' && !showUserInfo && 'Account'}
      </Button>
      
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        PaperProps={{
          sx: {
            minWidth: 200,
            mt: 1
          }
        }}
      >
        <MenuItem>
          <ListItemIcon>
            <PersonIcon fontSize="small" />
          </ListItemIcon>
          Profile
        </MenuItem>
        
        <MenuItem>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          Settings
        </MenuItem>
        
        <Divider />
        
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Sign Out
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default AuthStatus;