'use client';

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Avatar,
  Chip,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  Person as PersonIcon,
  Email as EmailIcon,
  Security as SecurityIcon,
  VpnKey as VpnKeyIcon
} from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';
import LogoutButton from './LogoutButton';

const UserProfile: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return (
      <Card>
        <CardContent>
          <Typography variant="body1" color="text.secondary">
            No user information available
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const getInitials = (firstName?: string, lastName?: string, username?: string) => {
    if (firstName && lastName) {
      return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
    }
    if (username) {
      return username.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'admin':
        return 'error';
      case 'trader':
        return 'primary';
      case 'analyst':
        return 'secondary';
      case 'viewer':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Avatar
            sx={{
              width: 64,
              height: 64,
              mr: 2,
              bgcolor: 'primary.main',
              fontSize: '1.5rem'
            }}
          >
            {getInitials(user.firstName, user.lastName, user.username)}
          </Avatar>
          <Box flex={1}>
            <Typography variant="h5" gutterBottom>
              {user.firstName && user.lastName 
                ? `${user.firstName} ${user.lastName}`
                : user.username
              }
            </Typography>
            <Typography variant="body2" color="text.secondary">
              @{user.username}
            </Typography>
          </Box>
          <LogoutButton iconOnly />
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <PersonIcon sx={{ mr: 1 }} />
              User Information
            </Typography>
            <List dense>
              <ListItem>
                <ListItemIcon>
                  <EmailIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Email"
                  secondary={user.email || 'Not provided'}
                />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <VpnKeyIcon />
                </ListItemIcon>
                <ListItemText
                  primary="User ID"
                  secondary={user.id}
                />
              </ListItem>
            </List>
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <SecurityIcon sx={{ mr: 1 }} />
              Roles & Permissions
            </Typography>
            
            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                Roles:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {user.roles.length > 0 ? (
                  user.roles.map((role) => (
                    <Chip
                      key={role}
                      label={role}
                      color={getRoleColor(role) as any}
                      size="small"
                      variant="outlined"
                    />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No roles assigned
                  </Typography>
                )}
              </Box>
            </Box>

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Permissions:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {user.permissions.length > 0 ? (
                  user.permissions.slice(0, 6).map((permission) => (
                    <Chip
                      key={permission}
                      label={permission}
                      size="small"
                      variant="filled"
                      color="default"
                    />
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No permissions assigned
                  </Typography>
                )}
                {user.permissions.length > 6 && (
                  <Chip
                    label={`+${user.permissions.length - 6} more`}
                    size="small"
                    variant="outlined"
                    color="default"
                  />
                )}
              </Box>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default UserProfile;