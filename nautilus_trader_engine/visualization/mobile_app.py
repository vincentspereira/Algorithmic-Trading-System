"""
Mobile Trading Application
React Native mobile application with push notifications and biometric authentication
"""
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


@dataclass
class MobileUser:
    """Mobile user data"""
    user_id: str
    device_id: str
    push_token: str
    biometric_enabled: bool
    last_login: datetime
    app_version: str


@dataclass
class PushNotification:
    """Push notification data"""
    notification_id: str
    user_id: str
    title: str
    message: str
    data: Dict[str, Any]
    priority: str = "normal"  # normal, high
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class MobileAPIServer:
    """Mobile API server for React Native app"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8081):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.mobile_users: Dict[str, MobileUser] = {}
        self.push_notifications: List[PushNotification] = []
        
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            CORS(self.app)  # Enable CORS for mobile app
            self.app.config['SECRET_KEY'] = 'nautilus-mobile-secret'
            self._setup_mobile_routes()
        else:
            self.app = None
            self.logger.warning("Flask not available - mobile API disabled")
    
    def _setup_mobile_routes(self):
        """Setup mobile-specific API routes"""
        
        @self.app.route('/mobile/api/auth/login', methods=['POST'])
        def mobile_login():
            """Mobile authentication endpoint"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            device_id = data.get('device_id')
            push_token = data.get('push_token')
            app_version = data.get('app_version', '1.0.0')
            
            # Simple authentication (replace with real auth)
            if username and password and device_id:
                user_id = f"mobile_user_{username}"
                
                mobile_user = MobileUser(
                    user_id=user_id,
                    device_id=device_id,
                    push_token=push_token or "",
                    biometric_enabled=False,
                    last_login=datetime.now(),
                    app_version=app_version
                )
                
                self.mobile_users[user_id] = mobile_user
                
                # Generate JWT token
                if JWT_AVAILABLE:
                    token = jwt.encode({
                        'user_id': user_id,
                        'device_id': device_id,
                        'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
                    }, self.app.config['SECRET_KEY'], algorithm='HS256')
                else:
                    token = f"token_{user_id}_{datetime.now().timestamp()}"
                
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': {
                        'user_id': user_id,
                        'username': username,
                        'biometric_enabled': mobile_user.biometric_enabled
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        @self.app.route('/mobile/api/auth/biometric/enable', methods=['POST'])
        def enable_biometric():
            """Enable biometric authentication"""
            data = request.get_json()
            user_id = data.get('user_id')
            biometric_data = data.get('biometric_data')  # Encrypted biometric template
            
            if user_id in self.mobile_users and biometric_data:
                self.mobile_users[user_id].biometric_enabled = True
                return jsonify({'success': True, 'message': 'Biometric authentication enabled'})
            else:
                return jsonify({'success': False, 'error': 'Invalid request'}), 400
        
        @self.app.route('/mobile/api/auth/biometric/login', methods=['POST'])
        def biometric_login():
            """Biometric authentication login"""
            data = request.get_json()
            user_id = data.get('user_id')
            biometric_signature = data.get('biometric_signature')
            
            if user_id in self.mobile_users and self.mobile_users[user_id].biometric_enabled:
                # In real implementation, verify biometric signature
                if biometric_signature:
                    # Generate new token
                    if JWT_AVAILABLE:
                        token = jwt.encode({
                            'user_id': user_id,
                            'device_id': self.mobile_users[user_id].device_id,
                            'exp': datetime.utcnow().timestamp() + 86400
                        }, self.app.config['SECRET_KEY'], algorithm='HS256')
                    else:
                        token = f"bio_token_{user_id}_{datetime.now().timestamp()}"
                    
                    return jsonify({
                        'success': True,
                        'token': token,
                        'message': 'Biometric authentication successful'
                    })
            
            return jsonify({'success': False, 'error': 'Biometric authentication failed'}), 401
        
        @self.app.route('/mobile/api/market/watchlist', methods=['GET'])
        def get_watchlist():
            """Get user's watchlist"""
            # Mock watchlist data
            watchlist = [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'price': 150.25,
                    'change': 2.15,
                    'change_percent': 1.45,
                    'alert_enabled': True,
                    'alert_price': 155.00
                },
                {
                    'symbol': 'GOOGL',
                    'name': 'Alphabet Inc.',
                    'price': 2750.80,
                    'change': -15.20,
                    'change_percent': -0.55,
                    'alert_enabled': False,
                    'alert_price': None
                },
                {
                    'symbol': 'TSLA',
                    'name': 'Tesla Inc.',
                    'price': 800.45,
                    'change': 25.30,
                    'change_percent': 3.26,
                    'alert_enabled': True,
                    'alert_price': 850.00
                }
            ]
            
            return jsonify({
                'success': True,
                'watchlist': watchlist,
                'last_updated': datetime.now().isoformat()
            })
        
        @self.app.route('/mobile/api/portfolio/summary', methods=['GET'])
        def get_portfolio_summary():
            """Get portfolio summary for mobile"""
            summary = {
                'total_value': 125750.50,
                'day_change': 2150.75,
                'day_change_percent': 1.74,
                'cash_balance': 15000.00,
                'buying_power': 30000.00,
                'positions_count': 8,
                'open_orders_count': 3
            }
            
            return jsonify({
                'success': True,
                'summary': summary,
                'last_updated': datetime.now().isoformat()
            })
        
        @self.app.route('/mobile/api/orders/quick', methods=['POST'])
        def quick_order():
            """Quick order placement for mobile"""
            data = request.get_json()
            
            required_fields = ['symbol', 'side', 'quantity']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Create quick order (market order)
            order = {
                'order_id': f"MOBILE_{datetime.now().timestamp()}",
                'symbol': data['symbol'],
                'side': data['side'],
                'quantity': data['quantity'],
                'order_type': 'market',
                'status': 'pending',
                'timestamp': datetime.now().isoformat()
            }
            
            # Send push notification
            self._send_push_notification(
                user_id=data.get('user_id', 'unknown'),
                title="Order Placed",
                message=f"{data['side'].upper()} {data['quantity']} {data['symbol']}",
                data={'order_id': order['order_id'], 'type': 'order_placed'}
            )
            
            return jsonify({'success': True, 'order': order})
        
        @self.app.route('/mobile/api/alerts', methods=['GET'])
        def get_alerts():
            """Get user alerts"""
            alerts = [
                {
                    'alert_id': 'ALERT_001',
                    'symbol': 'AAPL',
                    'type': 'price_above',
                    'target_price': 155.00,
                    'current_price': 150.25,
                    'status': 'active',
                    'created_at': '2024-01-15T10:00:00Z'
                },
                {
                    'alert_id': 'ALERT_002',
                    'symbol': 'TSLA',
                    'type': 'price_below',
                    'target_price': 750.00,
                    'current_price': 800.45,
                    'status': 'active',
                    'created_at': '2024-01-14T15:30:00Z'
                }
            ]
            
            return jsonify({
                'success': True,
                'alerts': alerts
            })
        
        @self.app.route('/mobile/api/alerts', methods=['POST'])
        def create_alert():
            """Create price alert"""
            data = request.get_json()
            
            alert = {
                'alert_id': f"ALERT_{datetime.now().timestamp()}",
                'symbol': data.get('symbol'),
                'type': data.get('type'),  # price_above, price_below
                'target_price': data.get('target_price'),
                'status': 'active',
                'created_at': datetime.now().isoformat()
            }
            
            return jsonify({'success': True, 'alert': alert})
        
        @self.app.route('/mobile/api/notifications/register', methods=['POST'])
        def register_push_token():
            """Register push notification token"""
            data = request.get_json()
            user_id = data.get('user_id')
            push_token = data.get('push_token')
            
            if user_id in self.mobile_users and push_token:
                self.mobile_users[user_id].push_token = push_token
                return jsonify({'success': True, 'message': 'Push token registered'})
            else:
                return jsonify({'success': False, 'error': 'Invalid request'}), 400
        
        @self.app.route('/mobile/api/app/config', methods=['GET'])
        def get_app_config():
            """Get mobile app configuration"""
            config = {
                'features': {
                    'biometric_auth': True,
                    'push_notifications': True,
                    'quick_orders': True,
                    'price_alerts': True,
                    'offline_mode': True
                },
                'limits': {
                    'max_watchlist_items': 50,
                    'max_alerts': 20,
                    'quick_order_limit': 10000
                },
                'refresh_intervals': {
                    'market_data': 5,  # seconds
                    'portfolio': 30,
                    'orders': 10
                }
            }
            
            return jsonify({
                'success': True,
                'config': config
            })
        
        @self.app.route('/mobile/api/offline/sync', methods=['POST'])
        def sync_offline_data():
            """Sync offline data when connection restored"""
            data = request.get_json()
            offline_actions = data.get('offline_actions', [])
            
            processed_actions = []
            
            for action in offline_actions:
                # Process offline actions (orders, alerts, etc.)
                action_result = {
                    'action_id': action.get('action_id'),
                    'type': action.get('type'),
                    'status': 'processed',
                    'timestamp': datetime.now().isoformat()
                }
                processed_actions.append(action_result)
            
            return jsonify({
                'success': True,
                'processed_actions': processed_actions,
                'sync_timestamp': datetime.now().isoformat()
            })
    
    def _send_push_notification(self, user_id: str, title: str, message: str, data: Dict[str, Any] = None):
        """Send push notification to mobile user"""
        if user_id not in self.mobile_users:
            return
        
        mobile_user = self.mobile_users[user_id]
        if not mobile_user.push_token:
            return
        
        notification = PushNotification(
            notification_id=f"PUSH_{datetime.now().timestamp()}",
            user_id=user_id,
            title=title,
            message=message,
            data=data or {}
        )
        
        self.push_notifications.append(notification)
        
        # In real implementation, send to FCM/APNS
        self.logger.info(f"Push notification sent to {user_id}: {title} - {message}")
    
    def create_react_native_config(self):
        """Create React Native app configuration files"""
        mobile_dir = Path("nautilus_trader_engine/visualization/mobile")
        mobile_dir.mkdir(parents=True, exist_ok=True)
        
        # Package.json for React Native
        package_json = {
            "name": "NautilusTraderMobile",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "android": "react-native run-android",
                "ios": "react-native run-ios",
                "start": "react-native start",
                "test": "jest",
                "lint": "eslint ."
            },
            "dependencies": {
                "react": "18.2.0",
                "react-native": "0.72.0",
                "@react-navigation/native": "^6.1.0",
                "@react-navigation/stack": "^6.3.0",
                "@react-native-async-storage/async-storage": "^1.19.0",
                "react-native-biometrics": "^3.0.0",
                "@react-native-firebase/app": "^18.0.0",
                "@react-native-firebase/messaging": "^18.0.0",
                "react-native-vector-icons": "^10.0.0",
                "react-native-chart-kit": "^6.12.0",
                "react-native-gesture-handler": "^2.12.0",
                "react-native-reanimated": "^3.3.0",
                "react-native-safe-area-context": "^4.7.0",
                "react-native-screens": "^3.22.0",
                "axios": "^1.4.0"
            },
            "devDependencies": {
                "@babel/core": "^7.20.0",
                "@babel/preset-env": "^7.20.0",
                "@babel/runtime": "^7.20.0",
                "@react-native/eslint-config": "^0.72.0",
                "@react-native/metro-config": "^0.72.0",
                "@tsconfig/react-native": "^3.0.0",
                "@types/react": "^18.0.24",
                "@types/react-test-renderer": "^18.0.0",
                "babel-jest": "^29.2.1",
                "eslint": "^8.19.0",
                "jest": "^29.2.1",
                "metro-react-native-babel-preset": "0.76.5",
                "prettier": "^2.4.1",
                "react-test-renderer": "18.2.0",
                "typescript": "4.8.4"
            },
            "jest": {
                "preset": "react-native"
            }
        }
        
        with open(mobile_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        # App.tsx - Main React Native component
        app_tsx = '''
import React, { useEffect, useState } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import ReactNativeBiometrics from 'react-native-biometrics';
import messaging from '@react-native-firebase/messaging';

interface User {
  user_id: string;
  username: string;
  biometric_enabled: boolean;
}

interface MarketData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [watchlist, setWatchlist] = useState<MarketData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    initializeApp();
    setupPushNotifications();
  }, []);

  const initializeApp = async () => {
    try {
      // Check for existing session
      const token = await AsyncStorage.getItem('auth_token');
      if (token) {
        // Validate token and load user data
        await loadUserData();
      }
      
      // Load watchlist
      await loadWatchlist();
      
      setIsLoading(false);
    } catch (error) {
      console.error('App initialization error:', error);
      setIsLoading(false);
    }
  };

  const setupPushNotifications = async () => {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        const token = await messaging().getToken();
        console.log('FCM Token:', token);
        
        // Register token with backend
        await registerPushToken(token);
      }

      // Handle foreground messages
      messaging().onMessage(async remoteMessage => {
        Alert.alert(
          remoteMessage.notification?.title || 'Notification',
          remoteMessage.notification?.body || 'New notification'
        );
      });
    } catch (error) {
      console.error('Push notification setup error:', error);
    }
  };

  const loadUserData = async () => {
    try {
      // Mock user data loading
      const userData: User = {
        user_id: 'user_123',
        username: 'trader',
        biometric_enabled: false
      };
      setUser(userData);
    } catch (error) {
      console.error('Error loading user data:', error);
    }
  };

  const loadWatchlist = async () => {
    try {
      const response = await fetch('http://localhost:8081/mobile/api/market/watchlist');
      const data = await response.json();
      
      if (data.success) {
        setWatchlist(data.watchlist);
      }
    } catch (error) {
      console.error('Error loading watchlist:', error);
    }
  };

  const registerPushToken = async (token: string) => {
    try {
      await fetch('http://localhost:8081/mobile/api/notifications/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user?.user_id,
          push_token: token
        })
      });
    } catch (error) {
      console.error('Error registering push token:', error);
    }
  };

  const enableBiometricAuth = async () => {
    try {
      const biometrics = new ReactNativeBiometrics();
      const { available, biometryType } = await biometrics.isSensorAvailable();

      if (available) {
        const { success } = await biometrics.simplePrompt({
          promptMessage: 'Enable biometric authentication',
          cancelButtonText: 'Cancel'
        });

        if (success) {
          // Enable biometric auth in backend
          const response = await fetch('http://localhost:8081/mobile/api/auth/biometric/enable', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              user_id: user?.user_id,
              biometric_data: 'encrypted_template'
            })
          });

          const data = await response.json();
          if (data.success) {
            setUser(prev => prev ? { ...prev, biometric_enabled: true } : null);
            Alert.alert('Success', 'Biometric authentication enabled');
          }
        }
      } else {
        Alert.alert('Error', 'Biometric authentication not available');
      }
    } catch (error) {
      console.error('Biometric setup error:', error);
      Alert.alert('Error', 'Failed to setup biometric authentication');
    }
  };

  const placeQuickOrder = async (symbol: string, side: 'buy' | 'sell', quantity: number) => {
    try {
      const response = await fetch('http://localhost:8081/mobile/api/orders/quick', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol,
          side,
          quantity,
          user_id: user?.user_id
        })
      });

      const data = await response.json();
      if (data.success) {
        Alert.alert('Success', `Order placed: ${side.toUpperCase()} ${quantity} ${symbol}`);
      } else {
        Alert.alert('Error', 'Failed to place order');
      }
    } catch (error) {
      console.error('Order placement error:', error);
      Alert.alert('Error', 'Failed to place order');
    }
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <Text style={styles.loadingText}>Loading Nautilus Trader...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Nautilus Trader</Text>
        {user && (
          <Text style={styles.headerSubtitle}>Welcome, {user.username}</Text>
        )}
      </View>

      <ScrollView style={styles.content}>
        {/* Biometric Auth Section */}
        {user && !user.biometric_enabled && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Security</Text>
            <TouchableOpacity style={styles.button} onPress={enableBiometricAuth}>
              <Text style={styles.buttonText}>Enable Biometric Authentication</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Watchlist Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Watchlist</Text>
          {watchlist.map((item, index) => (
            <View key={index} style={styles.watchlistItem}>
              <View style={styles.symbolInfo}>
                <Text style={styles.symbolText}>{item.symbol}</Text>
                <Text style={styles.nameText}>{item.name}</Text>
              </View>
              <View style={styles.priceInfo}>
                <Text style={styles.priceText}>${item.price.toFixed(2)}</Text>
                <Text style={[
                  styles.changeText,
                  { color: item.change >= 0 ? '#28a745' : '#dc3545' }
                ]}>
                  {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)} ({item.change_percent.toFixed(2)}%)
                </Text>
              </View>
              <View style={styles.quickActions}>
                <TouchableOpacity 
                  style={[styles.quickButton, styles.buyButton]}
                  onPress={() => placeQuickOrder(item.symbol, 'buy', 10)}
                >
                  <Text style={styles.quickButtonText}>Buy</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.quickButton, styles.sellButton]}
                  onPress={() => placeQuickOrder(item.symbol, 'sell', 10)}
                >
                  <Text style={styles.quickButtonText}>Sell</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 18,
  },
  header: {
    backgroundColor: '#2d2d2d',
    padding: 20,
    borderBottomWidth: 2,
    borderBottomColor: '#4a90e2',
  },
  headerTitle: {
    color: '#4a90e2',
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  headerSubtitle: {
    color: '#ffffff',
    fontSize: 16,
    textAlign: 'center',
    marginTop: 5,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  section: {
    marginBottom: 30,
  },
  sectionTitle: {
    color: '#4a90e2',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  button: {
    backgroundColor: '#4a90e2',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  watchlistItem: {
    backgroundColor: '#2d2d2d',
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  symbolInfo: {
    flex: 1,
  },
  symbolText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  nameText: {
    color: '#cccccc',
    fontSize: 14,
  },
  priceInfo: {
    flex: 1,
    alignItems: 'center',
  },
  priceText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  changeText: {
    fontSize: 14,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 10,
  },
  quickButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 5,
  },
  buyButton: {
    backgroundColor: '#28a745',
  },
  sellButton: {
    backgroundColor: '#dc3545',
  },
  quickButtonText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
  },
});

export default App;
'''
        
        with open(mobile_dir / "App.tsx", "w") as f:
            f.write(app_tsx)
        
        self.logger.info("React Native configuration files created")
    
    def run(self):
        """Run the mobile API server"""
        if self.app:
            self.create_react_native_config()
            self.logger.info(f"Starting mobile API server on {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=False)
        else:
            self.logger.error("Cannot start mobile API server - Flask not available")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    mobile_server = MobileAPIServer()
    mobile_server.run()