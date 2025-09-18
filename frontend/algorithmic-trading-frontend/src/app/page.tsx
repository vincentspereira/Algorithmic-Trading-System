"use client";

import { useState, useEffect } from 'react';
import { Box, AppBar, Toolbar, Typography, Container } from '@mui/material';
import TradingDashboard from '@/components/TradingDashboard';
import ConnectionStatus from '@/components/ConnectionStatus';
import { AuthStatus, ProtectedRoute } from '@/components/auth';
import { TradingMode } from '@/types/trading';

export default function Home() {
  const [tradingMode, setTradingMode] = useState<TradingMode>('paper');
  const [isConnected, setIsConnected] = useState(false);

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <AppBar position="static" elevation={1} sx={{ bgcolor: 'background.paper', color: 'text.primary' }}>
        <Toolbar>
          <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}>
            <Typography variant="h6" component="h1" sx={{ fontWeight: 600 }}>
              Algorithmic Trading System
            </Typography>
            <Typography variant="body2" sx={{ ml: 2, color: 'text.secondary' }}>
              Phase 1 - Core System
            </Typography>
          </Box>
          
          {/* Trading Mode Toggle and Auth Status */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <ConnectionStatus isConnected={isConnected} />
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Trading Mode:
              </Typography>
              <select
                value={tradingMode}
                onChange={(e) => setTradingMode(e.target.value as TradingMode)}
                className={`
                  px-3 py-1 rounded-md text-sm font-medium border transition-colors
                  ${tradingMode === 'paper' 
                    ? 'bg-green-100 text-green-800 border-green-300'
                    : 'bg-red-100 text-red-800 border-red-300'
                  }
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                `}
              >
                <option value="paper">📄 Paper Trading</option>
                <option value="live">🔴 Live Trading</option>
              </select>
            </Box>
            
            {/* Safety Warning for Live Mode */}
            {tradingMode === 'live' && (
              <Box sx={{ 
                bgcolor: 'error.light', 
                color: 'error.contrastText', 
                px: 1, 
                py: 0.5, 
                borderRadius: 1, 
                fontSize: '0.75rem',
                fontWeight: 500
              }}>
                ⚠️ LIVE MODE
              </Box>
            )}
            
            {/* Authentication Status */}
            <AuthStatus variant="header" />
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Dashboard */}
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <ProtectedRoute requiredPermission="market_data_viewer">
          <TradingDashboard 
            tradingMode={tradingMode} 
            setIsConnected={setIsConnected}
          />
        </ProtectedRoute>
      </Container>
    </Box>
  );
}
