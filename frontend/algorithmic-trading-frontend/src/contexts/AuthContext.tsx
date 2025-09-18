'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import keycloak, { 
  keycloakInitOptions, 
  isAuthenticated, 
  getUserInfo, 
  getUserPermissions,
  hasPermission,
  hasRole,
  refreshToken,
  login,
  logout,
  canViewMarketData,
  canTrade,
  canViewPortfolio,
  canManageUsers,
  canViewReports
} from '../lib/keycloak';

interface User {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  roles: string[];
  permissions: string[];
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | null;
  login: () => void;
  logout: () => void;
  refreshToken: () => Promise<string | undefined>;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
  // Trading-specific permissions
  canViewMarketData: () => boolean;
  canTrade: () => boolean;
  canViewPortfolio: () => boolean;
  canManageUsers: () => boolean;
  canViewReports: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const updateUserInfo = () => {
    if (isAuthenticated()) {
      const userInfo = getUserInfo();
      const permissions = getUserPermissions();
      
      if (userInfo) {
        setUser({
          id: userInfo.sub || '',
          username: userInfo.preferred_username || '',
          email: userInfo.email || '',
          firstName: userInfo.given_name,
          lastName: userInfo.family_name,
          roles: userInfo.realm_access?.roles || [],
          permissions
        });
      }
      setToken(keycloak.token || null);
      setAuthenticated(true);
    } else {
      setUser(null);
      setToken(null);
      setAuthenticated(false);
    }
  };

  useEffect(() => {
    const initKeycloak = async () => {
      try {
        const authenticated = await keycloak.init(keycloakInitOptions);
        
        if (authenticated) {
          updateUserInfo();
          
          // Set up token refresh
          keycloak.onTokenExpired = () => {
            refreshToken(30).catch((error) => {
              console.error('Token refresh failed:', error);
              logout();
            });
          };
          
          // Update token when refreshed
          keycloak.onAuthRefreshSuccess = () => {
            setToken(keycloak.token || null);
          };
          
          // Handle authentication events
          keycloak.onAuthSuccess = () => {
            updateUserInfo();
          };
          
          keycloak.onAuthLogout = () => {
            setUser(null);
            setToken(null);
            setAuthenticated(false);
          };
        }
      } catch (error) {
        console.error('Keycloak initialization failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initKeycloak();
  }, []);

  const contextValue: AuthContextType = {
    isAuthenticated: authenticated,
    isLoading,
    user,
    token,
    login,
    logout,
    refreshToken,
    hasRole,
    hasPermission,
    canViewMarketData,
    canTrade,
    canViewPortfolio,
    canManageUsers,
    canViewReports
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;