// Authentication Components
export { default as LoginButton } from './LoginButton';
export { default as LogoutButton } from './LogoutButton';
export { default as ProtectedRoute } from './ProtectedRoute';
export { default as UserProfile } from './UserProfile';
export { default as AuthStatus } from './AuthStatus';

// Authentication Context
export { AuthProvider, useAuth } from '../../contexts/AuthContext';

// Keycloak utilities
export {
  getToken,
  getRefreshToken,
  isAuthenticated,
  getUserInfo,
  hasRole,
  hasResourceRole,
  refreshToken,
  logout,
  login,
  getUserPermissions,
  hasPermission,
  canViewMarketData,
  canTrade,
  canViewPortfolio,
  canManageUsers,
  canViewReports
} from '../../lib/keycloak';