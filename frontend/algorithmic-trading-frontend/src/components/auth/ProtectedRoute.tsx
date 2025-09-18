'use client';

import React, { ReactNode } from 'react';
import { Box, CircularProgress, Paper, Typography, Alert } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';
import LoginButton from './LoginButton';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
  requiredPermission?: string;
  fallback?: ReactNode;
  showLoginPrompt?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
  fallback,
  showLoginPrompt = true
}) => {
  const { isAuthenticated, isLoading, hasRole, hasPermission, user } = useAuth();

  // Show loading spinner while authentication is being checked
  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
        flexDirection="column"
        gap={2}
      >
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary">
          Checking authentication...
        </Typography>
      </Box>
    );
  }

  // Show login prompt if not authenticated
  if (!isAuthenticated) {
    if (fallback) {
      return <>{fallback}</>;
    }

    if (!showLoginPrompt) {
      return null;
    }

    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
        p={3}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            textAlign: 'center',
            maxWidth: 400,
            width: '100%'
          }}
        >
          <Typography variant="h5" gutterBottom color="primary">
            Authentication Required
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Please sign in to access this feature.
          </Typography>
          <LoginButton fullWidth size="large" />
        </Paper>
      </Box>
    );
  }

  // Check role requirement
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <Box p={3}>
        <Alert severity="error">
          <Typography variant="h6" gutterBottom>
            Access Denied
          </Typography>
          <Typography variant="body2">
            You need the <strong>{requiredRole}</strong> role to access this feature.
            {user && (
              <>
                <br />
                Your current roles: {user.roles.join(', ') || 'None'}
              </>
            )}
          </Typography>
        </Alert>
      </Box>
    );
  }

  // Check permission requirement
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <Box p={3}>
        <Alert severity="error">
          <Typography variant="h6" gutterBottom>
            Access Denied
          </Typography>
          <Typography variant="body2">
            You need the <strong>{requiredPermission}</strong> permission to access this feature.
            {user && (
              <>
                <br />
                Your current permissions: {user.permissions.join(', ') || 'None'}
              </>
            )}
          </Typography>
        </Alert>
      </Box>
    );
  }

  // User is authenticated and has required permissions
  return <>{children}</>;
};

export default ProtectedRoute;