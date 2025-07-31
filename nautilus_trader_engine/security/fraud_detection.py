"""
Fraud Detection Engine

This module provides comprehensive fraud detection capabilities including:
- Machine learning-based fraud scoring
- Behavioral pattern analysis
- Real-time transaction monitoring
- Automated response and mitigation
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import statistics
import json
from collections import defaultdict, deque
import hashlib
import warnings

# Try to import optional ML dependencies
try:
    import sklearn.ensemble as ensemble
    import sklearn.preprocessing as preprocessing
    import sklearn.model_selection as model_selection
    import sklearn.metrics as metrics
    from sklearn.base import BaseEstimator, TransformerMixin
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("scikit-learn not available. ML-based fraud detection will use simplified algorithms.")

try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class FraudRiskLevel(Enum):
    """Fraud risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudIndicatorType(Enum):
    """Types of fraud indicators"""
    VELOCITY_ANOMALY = "velocity_anomaly"
    AMOUNT_ANOMALY = "amount_anomaly"
    TIME_ANOMALY = "time_anomaly"
    LOCATION_ANOMALY = "location_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    PATTERN_ANOMALY = "pattern_anomaly"
    ACCOUNT_ANOMALY = "account_anomaly"
    NETWORK_ANOMALY = "network_anomaly"


class ResponseAction(Enum):
    """Automated response actions"""
    MONITOR = "monitor"
    FLAG = "flag"
    ALERT = "alert"
    BLOCK = "block"
    SUSPEND = "suspend"
    ESCALATE = "escalate"


@dataclass
class Transaction:
    """Transaction data for fraud detection"""
    transaction_id: str
    user_id: str
    account_id: str
    amount: float
    currency: str
    transaction_type: str
    timestamp: datetime
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    merchant_id: Optional[str] = None
    channel: str = "web"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FraudIndicator:
    """Fraud indicator detected in transaction"""
    indicator_id: str
    indicator_type: FraudIndicatorType
    description: str
    severity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FraudScore:
    """Fraud risk score for a transaction"""
    transaction_id: str
    overall_score: float  # 0.0 to 1.0
    risk_level: FraudRiskLevel
    indicators: List[FraudIndicator]
    model_scores: Dict[str, float] = field(default_factory=dict)
    behavioral_score: float = 0.0
    pattern_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FraudAlert:
    """Fraud alert generated for suspicious activity"""
    alert_id: str
    transaction_id: str
    user_id: str
    fraud_score: FraudScore
    alert_level: FraudRiskLevel
    message: str
    recommended_actions: List[ResponseAction]
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: str = ""


@dataclass
class UserProfile:
    """User behavioral profile for fraud detection"""
    user_id: str
    account_created: datetime
    transaction_history: List[Transaction] = field(default_factory=list)
    behavioral_patterns: Dict[str, Any] = field(default_factory=dict)
    risk_factors: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class BehavioralAnalyzer:
    """Behavioral pattern analysis for fraud detection"""
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
        self.user_profiles: Dict[str, UserProfile] = {}
    
    def update_user_profile(self, transaction: Transaction):
        """Update user behavioral profile with new transaction"""
        try:
            user_id = transaction.user_id
            
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(
                    user_id=user_id,
                    account_created=datetime.now() - timedelta(days=30)  # Default
                )
            
            profile = self.user_profiles[user_id]
            
            # Add transaction to history (keep only recent transactions)
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            profile.transaction_history = [
                t for t in profile.transaction_history 
                if t.timestamp >= cutoff_date
            ]
            profile.transaction_history.append(transaction)
            
            # Update behavioral patterns
            self._update_behavioral_patterns(profile)
            profile.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error updating user profile: {e}")
    
    def _update_behavioral_patterns(self, profile: UserProfile):
        """Update behavioral patterns based on transaction history"""
        try:
            transactions = profile.transaction_history
            if not transactions:
                return
            
            # Calculate transaction patterns
            amounts = [t.amount for t in transactions]
            hours = [t.timestamp.hour for t in transactions]
            days_of_week = [t.timestamp.weekday() for t in transactions]
            
            # Amount patterns
            profile.behavioral_patterns.update({
                'avg_amount': statistics.mean(amounts) if amounts else 0,
                'median_amount': statistics.median(amounts) if amounts else 0,
                'amount_std': statistics.stdev(amounts) if len(amounts) > 1 else 0,
                'max_amount': max(amounts) if amounts else 0,
                'min_amount': min(amounts) if amounts else 0
            })
            
            # Time patterns
            profile.behavioral_patterns.update({
                'preferred_hours': self._get_preferred_hours(hours),
                'preferred_days': self._get_preferred_days(days_of_week),
                'transaction_frequency': len(transactions) / max(self.lookback_days, 1)
            })
            
            # Channel patterns
            channels = [t.channel for t in transactions]
            channel_counts = {}
            for channel in channels:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
            profile.behavioral_patterns['channel_distribution'] = channel_counts
            
            # Location patterns (if available)
            locations = [t.location for t in transactions if t.location]
            if locations:
                profile.behavioral_patterns['location_diversity'] = len(set(
                    f"{loc.get('country', '')}-{loc.get('city', '')}" 
                    for loc in locations
                ))
            
        except Exception as e:
            self.logger.error(f"Error updating behavioral patterns: {e}")
    
    def _get_preferred_hours(self, hours: List[int]) -> List[int]:
        """Get preferred transaction hours"""
        if not hours:
            return []
        
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Return hours with above-average frequency
        avg_count = len(hours) / 24
        return [hour for hour, count in hour_counts.items() if count > avg_count]
    
    def _get_preferred_days(self, days: List[int]) -> List[int]:
        """Get preferred transaction days of week"""
        if not days:
            return []
        
        day_counts = {}
        for day in days:
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Return days with above-average frequency
        avg_count = len(days) / 7
        return [day for day, count in day_counts.items() if count > avg_count]
    
    def analyze_transaction_behavior(self, transaction: Transaction) -> List[FraudIndicator]:
        """Analyze transaction against user behavioral patterns"""
        indicators = []
        
        try:
            user_id = transaction.user_id
            if user_id not in self.user_profiles:
                # New user - create basic profile
                self.update_user_profile(transaction)
                return indicators
            
            profile = self.user_profiles[user_id]
            patterns = profile.behavioral_patterns
            
            # Amount anomaly detection
            amount_indicators = self._detect_amount_anomalies(transaction, patterns)
            indicators.extend(amount_indicators)
            
            # Time anomaly detection
            time_indicators = self._detect_time_anomalies(transaction, patterns)
            indicators.extend(time_indicators)
            
            # Velocity anomaly detection
            velocity_indicators = self._detect_velocity_anomalies(transaction, profile)
            indicators.extend(velocity_indicators)
            
            # Location anomaly detection
            if transaction.location:
                location_indicators = self._detect_location_anomalies(transaction, profile)
                indicators.extend(location_indicators)
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction behavior: {e}")
        
        return indicators
    
    def _detect_amount_anomalies(self, transaction: Transaction, patterns: Dict[str, Any]) -> List[FraudIndicator]:
        """Detect amount-based anomalies"""
        indicators = []
        
        try:
            amount = transaction.amount
            avg_amount = patterns.get('avg_amount', 0)
            amount_std = patterns.get('amount_std', 0)
            max_amount = patterns.get('max_amount', 0)
            
            # Large amount anomaly
            if avg_amount > 0 and amount_std > 0:
                z_score = abs(amount - avg_amount) / amount_std
                if z_score > 3:  # 3 standard deviations
                    indicators.append(FraudIndicator(
                        indicator_id=str(uuid.uuid4()),
                        indicator_type=FraudIndicatorType.AMOUNT_ANOMALY,
                        description=f"Transaction amount significantly deviates from user pattern",
                        severity=min(z_score / 5, 1.0),  # Cap at 1.0
                        confidence=0.8,
                        details={
                            'amount': amount,
                            'avg_amount': avg_amount,
                            'z_score': z_score,
                            'threshold': 3
                        }
                    ))
            
            # Unusually large transaction
            if max_amount > 0 and amount > max_amount * 2:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.AMOUNT_ANOMALY,
                    description=f"Transaction amount exceeds historical maximum by 2x",
                    severity=0.9,
                    confidence=0.9,
                    details={
                        'amount': amount,
                        'max_historical': max_amount,
                        'multiplier': amount / max_amount if max_amount > 0 else 0
                    }
                ))
            
        except Exception as e:
            self.logger.error(f"Error detecting amount anomalies: {e}")
        
        return indicators
    
    def _detect_time_anomalies(self, transaction: Transaction, patterns: Dict[str, Any]) -> List[FraudIndicator]:
        """Detect time-based anomalies"""
        indicators = []
        
        try:
            hour = transaction.timestamp.hour
            day_of_week = transaction.timestamp.weekday()
            
            preferred_hours = patterns.get('preferred_hours', [])
            preferred_days = patterns.get('preferred_days', [])
            
            # Unusual hour
            if preferred_hours and hour not in preferred_hours:
                # Check if it's significantly outside normal hours
                if len(preferred_hours) > 0:
                    min_hour = min(preferred_hours)
                    max_hour = max(preferred_hours)
                    
                    # Calculate distance from preferred time range
                    if hour < min_hour:
                        distance = min_hour - hour
                    elif hour > max_hour:
                        distance = hour - max_hour
                    else:
                        distance = 0
                    
                    if distance > 3:  # More than 3 hours outside normal range
                        indicators.append(FraudIndicator(
                            indicator_id=str(uuid.uuid4()),
                            indicator_type=FraudIndicatorType.TIME_ANOMALY,
                            description=f"Transaction at unusual hour for user",
                            severity=min(distance / 12, 1.0),  # Cap at 1.0
                            confidence=0.6,
                            details={
                                'transaction_hour': hour,
                                'preferred_hours': preferred_hours,
                                'distance': distance
                            }
                        ))
            
            # Unusual day
            if preferred_days and day_of_week not in preferred_days:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.TIME_ANOMALY,
                    description=f"Transaction on unusual day for user",
                    severity=0.4,
                    confidence=0.5,
                    details={
                        'transaction_day': day_of_week,
                        'preferred_days': preferred_days
                    }
                ))
            
        except Exception as e:
            self.logger.error(f"Error detecting time anomalies: {e}")
        
        return indicators
    
    def _detect_velocity_anomalies(self, transaction: Transaction, profile: UserProfile) -> List[FraudIndicator]:
        """Detect velocity-based anomalies"""
        indicators = []
        
        try:
            now = transaction.timestamp
            recent_transactions = [
                t for t in profile.transaction_history
                if (now - t.timestamp).total_seconds() <= 3600  # Last hour
            ]
            
            # High frequency in short time
            if len(recent_transactions) > 10:  # More than 10 transactions in an hour
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.VELOCITY_ANOMALY,
                    description=f"High transaction frequency detected",
                    severity=min(len(recent_transactions) / 20, 1.0),
                    confidence=0.8,
                    details={
                        'transactions_last_hour': len(recent_transactions),
                        'threshold': 10
                    }
                ))
            
            # High amount velocity
            recent_amount = sum(t.amount for t in recent_transactions)
            avg_hourly_amount = profile.behavioral_patterns.get('avg_amount', 0) * \
                               profile.behavioral_patterns.get('transaction_frequency', 0)
            
            if avg_hourly_amount > 0 and recent_amount > avg_hourly_amount * 5:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.VELOCITY_ANOMALY,
                    description=f"High transaction amount velocity detected",
                    severity=min(recent_amount / (avg_hourly_amount * 10), 1.0),
                    confidence=0.7,
                    details={
                        'recent_amount': recent_amount,
                        'avg_hourly_amount': avg_hourly_amount,
                        'multiplier': recent_amount / avg_hourly_amount if avg_hourly_amount > 0 else 0
                    }
                ))
            
        except Exception as e:
            self.logger.error(f"Error detecting velocity anomalies: {e}")
        
        return indicators
    
    def _detect_location_anomalies(self, transaction: Transaction, profile: UserProfile) -> List[FraudIndicator]:
        """Detect location-based anomalies"""
        indicators = []
        
        try:
            current_location = transaction.location
            if not current_location:
                return indicators
            
            # Get historical locations
            historical_locations = [
                t.location for t in profile.transaction_history 
                if t.location and t.timestamp >= datetime.now() - timedelta(days=7)
            ]
            
            if not historical_locations:
                return indicators
            
            # Check for new country
            current_country = current_location.get('country', '')
            historical_countries = set(loc.get('country', '') for loc in historical_locations)
            
            if current_country and current_country not in historical_countries:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.LOCATION_ANOMALY,
                    description=f"Transaction from new country",
                    severity=0.7,
                    confidence=0.8,
                    details={
                        'current_country': current_country,
                        'historical_countries': list(historical_countries)
                    }
                ))
            
            # Check for rapid location changes
            recent_locations = [
                t.location for t in profile.transaction_history
                if t.location and (transaction.timestamp - t.timestamp).total_seconds() <= 3600
            ]
            
            if len(recent_locations) > 1:
                # Check if locations are geographically distant
                unique_countries = set(loc.get('country', '') for loc in recent_locations + [current_location])
                if len(unique_countries) > 1:
                    indicators.append(FraudIndicator(
                        indicator_id=str(uuid.uuid4()),
                        indicator_type=FraudIndicatorType.LOCATION_ANOMALY,
                        description=f"Rapid location changes detected",
                        severity=0.8,
                        confidence=0.9,
                        details={
                            'countries_last_hour': list(unique_countries),
                            'time_window': '1 hour'
                        }
                    ))
            
        except Exception as e:
            self.logger.error(f"Error detecting location anomalies: {e}")
        
        return indicators
    
    def get_behavioral_score(self, transaction: Transaction) -> float:
        """Get behavioral anomaly score for transaction"""
        try:
            indicators = self.analyze_transaction_behavior(transaction)
            
            if not indicators:
                return 0.0
            
            # Calculate weighted score based on indicators
            total_score = 0.0
            total_weight = 0.0
            
            for indicator in indicators:
                weight = indicator.confidence
                score = indicator.severity * weight
                total_score += score
                total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating behavioral score: {e}")
            return 0.0


class MLFraudDetector:
    """Machine learning-based fraud detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models: Dict[str, Any] = {}
        self.feature_extractors: Dict[str, Any] = {}
        self.is_trained = False
        
        if SKLEARN_AVAILABLE:
            self._initialize_models()
        else:
            self.logger.warning("scikit-learn not available. Using simplified fraud detection.")
    
    def _initialize_models(self):
        """Initialize ML models for fraud detection"""
        try:
            # Random Forest for general fraud detection
            self.models['random_forest'] = ensemble.RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Isolation Forest for anomaly detection
            self.models['isolation_forest'] = ensemble.IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Feature scalers
            self.feature_extractors['scaler'] = preprocessing.StandardScaler()
            self.feature_extractors['encoder'] = preprocessing.LabelEncoder()
            
        except Exception as e:
            self.logger.error(f"Error initializing ML models: {e}")
    
    def extract_features(self, transaction: Transaction, user_profile: Optional[UserProfile] = None) -> np.ndarray:
        """Extract features from transaction for ML models"""
        try:
            features = []
            
            # Transaction features
            features.extend([
                transaction.amount,
                transaction.timestamp.hour,
                transaction.timestamp.weekday(),
                len(transaction.transaction_type),
                hash(transaction.channel) % 1000,  # Simple hash for categorical
                hash(transaction.currency) % 100
            ])
            
            # User profile features
            if user_profile:
                patterns = user_profile.behavioral_patterns
                features.extend([
                    patterns.get('avg_amount', 0),
                    patterns.get('transaction_frequency', 0),
                    len(patterns.get('preferred_hours', [])),
                    len(patterns.get('channel_distribution', {})),
                    patterns.get('location_diversity', 0)
                ])
            else:
                # Default values for new users
                features.extend([0, 0, 0, 0, 0])
            
            # Device and location features
            features.extend([
                1 if transaction.device_id else 0,
                1 if transaction.ip_address else 0,
                1 if transaction.location else 0
            ])
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
            return np.array([]).reshape(1, -1)
    
    def train_models(self, training_data: List[Tuple[Transaction, bool, Optional[UserProfile]]]):
        """Train ML models with labeled data"""
        if not SKLEARN_AVAILABLE:
            self.logger.warning("Cannot train models without scikit-learn")
            return
        
        try:
            if len(training_data) < 100:
                self.logger.warning("Insufficient training data for ML models")
                return
            
            # Extract features and labels
            X = []
            y = []
            
            for transaction, is_fraud, user_profile in training_data:
                features = self.extract_features(transaction, user_profile)
                if features.size > 0:
                    X.append(features.flatten())
                    y.append(1 if is_fraud else 0)
            
            if not X:
                self.logger.error("No valid features extracted from training data")
                return
            
            X = np.array(X)
            y = np.array(y)
            
            # Scale features
            X_scaled = self.feature_extractors['scaler'].fit_transform(X)
            
            # Train Random Forest
            self.models['random_forest'].fit(X_scaled, y)
            
            # Train Isolation Forest (unsupervised)
            self.models['isolation_forest'].fit(X_scaled)
            
            self.is_trained = True
            self.logger.info(f"Trained ML models with {len(training_data)} samples")
            
        except Exception as e:
            self.logger.error(f"Error training ML models: {e}")
    
    def predict_fraud_probability(self, transaction: Transaction, user_profile: Optional[UserProfile] = None) -> Dict[str, float]:
        """Predict fraud probability using ML models"""
        scores = {}
        
        try:
            if not SKLEARN_AVAILABLE or not self.is_trained:
                # Use simple heuristic scoring
                return self._simple_fraud_scoring(transaction, user_profile)
            
            features = self.extract_features(transaction, user_profile)
            if features.size == 0:
                return {'simple_score': 0.0}
            
            # Scale features
            features_scaled = self.feature_extractors['scaler'].transform(features)
            
            # Random Forest prediction
            rf_prob = self.models['random_forest'].predict_proba(features_scaled)[0]
            scores['random_forest'] = rf_prob[1] if len(rf_prob) > 1 else 0.0
            
            # Isolation Forest anomaly score
            anomaly_score = self.models['isolation_forest'].decision_function(features_scaled)[0]
            # Convert to probability (higher anomaly = higher fraud probability)
            scores['isolation_forest'] = max(0, (0.5 - anomaly_score) * 2)
            
        except Exception as e:
            self.logger.error(f"Error predicting fraud probability: {e}")
            scores['error_fallback'] = 0.5  # Medium risk on error
        
        return scores
    
    def _simple_fraud_scoring(self, transaction: Transaction, user_profile: Optional[UserProfile] = None) -> Dict[str, float]:
        """Simple heuristic fraud scoring when ML is not available"""
        score = 0.0
        
        try:
            # Amount-based scoring
            if transaction.amount > 10000:
                score += 0.3
            elif transaction.amount > 5000:
                score += 0.1
            
            # Time-based scoring
            hour = transaction.timestamp.hour
            if hour < 6 or hour > 22:  # Late night/early morning
                score += 0.2
            
            # Weekend scoring
            if transaction.timestamp.weekday() >= 5:
                score += 0.1
            
            # New user scoring
            if not user_profile:
                score += 0.2
            
            # Round-number amounts (often suspicious)
            if transaction.amount % 100 == 0 and transaction.amount >= 1000:
                score += 0.1
            
        except Exception as e:
            self.logger.error(f"Error in simple fraud scoring: {e}")
        
        return {'simple_heuristic': min(score, 1.0)}


class PatternDetector:
    """Pattern-based fraud detection"""
    
    def __init__(self, pattern_window_hours: int = 24):
        self.pattern_window_hours = pattern_window_hours
        self.logger = logging.getLogger(__name__)
        self.transaction_buffer: deque = deque(maxlen=10000)  # Keep recent transactions
        self.known_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Initialize known fraud patterns
        self._initialize_fraud_patterns()
    
    def _initialize_fraud_patterns(self):
        """Initialize known fraud patterns"""
        self.known_patterns = {
            'card_testing': {
                'description': 'Multiple small transactions to test card validity',
                'criteria': {
                    'min_transactions': 5,
                    'max_amount': 10,
                    'time_window_minutes': 30,
                    'same_merchant': True
                },
                'severity': 0.8
            },
            'velocity_attack': {
                'description': 'High-frequency transactions in short time',
                'criteria': {
                    'min_transactions': 10,
                    'time_window_minutes': 60,
                    'same_user': True
                },
                'severity': 0.9
            },
            'amount_laddering': {
                'description': 'Incrementally increasing transaction amounts',
                'criteria': {
                    'min_transactions': 3,
                    'increasing_amounts': True,
                    'time_window_minutes': 120,
                    'same_user': True
                },
                'severity': 0.7
            },
            'round_amount_pattern': {
                'description': 'Multiple round-number transactions',
                'criteria': {
                    'min_transactions': 3,
                    'round_amounts': True,
                    'time_window_minutes': 180
                },
                'severity': 0.6
            }
        }
    
    def add_transaction(self, transaction: Transaction):
        """Add transaction to pattern detection buffer"""
        try:
            self.transaction_buffer.append(transaction)
            
            # Clean old transactions
            cutoff_time = datetime.now() - timedelta(hours=self.pattern_window_hours)
            while (self.transaction_buffer and 
                   self.transaction_buffer[0].timestamp < cutoff_time):
                self.transaction_buffer.popleft()
                
        except Exception as e:
            self.logger.error(f"Error adding transaction to pattern buffer: {e}")
    
    def detect_patterns(self, transaction: Transaction) -> List[FraudIndicator]:
        """Detect fraud patterns involving the current transaction"""
        indicators = []
        
        try:
            # Add current transaction to buffer
            self.add_transaction(transaction)
            
            # Check each known pattern
            for pattern_name, pattern_config in self.known_patterns.items():
                pattern_indicators = self._check_pattern(transaction, pattern_name, pattern_config)
                indicators.extend(pattern_indicators)
            
        except Exception as e:
            self.logger.error(f"Error detecting patterns: {e}")
        
        return indicators
    
    def _check_pattern(self, transaction: Transaction, pattern_name: str, pattern_config: Dict[str, Any]) -> List[FraudIndicator]:
        """Check if transaction matches a specific fraud pattern"""
        indicators = []
        
        try:
            criteria = pattern_config['criteria']
            time_window = timedelta(minutes=criteria.get('time_window_minutes', 60))
            cutoff_time = transaction.timestamp - time_window
            
            # Get relevant transactions within time window
            relevant_transactions = [
                t for t in self.transaction_buffer
                if t.timestamp >= cutoff_time
            ]
            
            # Apply pattern-specific filters
            if criteria.get('same_user'):
                relevant_transactions = [
                    t for t in relevant_transactions
                    if t.user_id == transaction.user_id
                ]
            
            if criteria.get('same_merchant'):
                relevant_transactions = [
                    t for t in relevant_transactions
                    if t.merchant_id == transaction.merchant_id
                ]
            
            # Check pattern criteria
            if pattern_name == 'card_testing':
                indicators.extend(self._check_card_testing_pattern(
                    transaction, relevant_transactions, criteria, pattern_config
                ))
            elif pattern_name == 'velocity_attack':
                indicators.extend(self._check_velocity_attack_pattern(
                    transaction, relevant_transactions, criteria, pattern_config
                ))
            elif pattern_name == 'amount_laddering':
                indicators.extend(self._check_amount_laddering_pattern(
                    transaction, relevant_transactions, criteria, pattern_config
                ))
            elif pattern_name == 'round_amount_pattern':
                indicators.extend(self._check_round_amount_pattern(
                    transaction, relevant_transactions, criteria, pattern_config
                ))
            
        except Exception as e:
            self.logger.error(f"Error checking pattern {pattern_name}: {e}")
        
        return indicators
    
    def _check_card_testing_pattern(self, transaction: Transaction, relevant_transactions: List[Transaction], 
                                   criteria: Dict[str, Any], pattern_config: Dict[str, Any]) -> List[FraudIndicator]:
        """Check for card testing pattern"""
        indicators = []
        
        try:
            min_transactions = criteria.get('min_transactions', 5)
            max_amount = criteria.get('max_amount', 10)
            
            # Filter small amount transactions
            small_transactions = [
                t for t in relevant_transactions
                if t.amount <= max_amount
            ]
            
            if len(small_transactions) >= min_transactions:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.PATTERN_ANOMALY,
                    description=pattern_config['description'],
                    severity=pattern_config['severity'],
                    confidence=0.8,
                    details={
                        'pattern_name': 'card_testing',
                        'transaction_count': len(small_transactions),
                        'threshold': min_transactions,
                        'max_amount': max_amount,
                        'time_window_minutes': criteria.get('time_window_minutes', 30)
                    }
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking card testing pattern: {e}")
        
        return indicators
    
    def _check_velocity_attack_pattern(self, transaction: Transaction, relevant_transactions: List[Transaction],
                                     criteria: Dict[str, Any], pattern_config: Dict[str, Any]) -> List[FraudIndicator]:
        """Check for velocity attack pattern"""
        indicators = []
        
        try:
            min_transactions = criteria.get('min_transactions', 10)
            
            if len(relevant_transactions) >= min_transactions:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.PATTERN_ANOMALY,
                    description=pattern_config['description'],
                    severity=pattern_config['severity'],
                    confidence=0.9,
                    details={
                        'pattern_name': 'velocity_attack',
                        'transaction_count': len(relevant_transactions),
                        'threshold': min_transactions,
                        'time_window_minutes': criteria.get('time_window_minutes', 60)
                    }
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking velocity attack pattern: {e}")
        
        return indicators
    
    def _check_amount_laddering_pattern(self, transaction: Transaction, relevant_transactions: List[Transaction],
                                      criteria: Dict[str, Any], pattern_config: Dict[str, Any]) -> List[FraudIndicator]:
        """Check for amount laddering pattern"""
        indicators = []
        
        try:
            min_transactions = criteria.get('min_transactions', 3)
            
            if len(relevant_transactions) >= min_transactions:
                # Sort by timestamp
                sorted_transactions = sorted(relevant_transactions, key=lambda t: t.timestamp)
                amounts = [t.amount for t in sorted_transactions]
                
                # Check if amounts are generally increasing
                increasing_count = 0
                for i in range(1, len(amounts)):
                    if amounts[i] > amounts[i-1]:
                        increasing_count += 1
                
                # If most transactions show increasing amounts
                if increasing_count >= len(amounts) * 0.6:
                    indicators.append(FraudIndicator(
                        indicator_id=str(uuid.uuid4()),
                        indicator_type=FraudIndicatorType.PATTERN_ANOMALY,
                        description=pattern_config['description'],
                        severity=pattern_config['severity'],
                        confidence=0.7,
                        details={
                            'pattern_name': 'amount_laddering',
                            'transaction_count': len(relevant_transactions),
                            'increasing_ratio': increasing_count / (len(amounts) - 1) if len(amounts) > 1 else 0,
                            'amounts': amounts
                        }
                    ))
        
        except Exception as e:
            self.logger.error(f"Error checking amount laddering pattern: {e}")
        
        return indicators
    
    def _check_round_amount_pattern(self, transaction: Transaction, relevant_transactions: List[Transaction],
                                  criteria: Dict[str, Any], pattern_config: Dict[str, Any]) -> List[FraudIndicator]:
        """Check for round amount pattern"""
        indicators = []
        
        try:
            min_transactions = criteria.get('min_transactions', 3)
            
            # Count round amount transactions
            round_transactions = [
                t for t in relevant_transactions
                if t.amount % 100 == 0 and t.amount >= 100
            ]
            
            if len(round_transactions) >= min_transactions:
                indicators.append(FraudIndicator(
                    indicator_id=str(uuid.uuid4()),
                    indicator_type=FraudIndicatorType.PATTERN_ANOMALY,
                    description=pattern_config['description'],
                    severity=pattern_config['severity'],
                    confidence=0.6,
                    details={
                        'pattern_name': 'round_amount_pattern',
                        'round_transaction_count': len(round_transactions),
                        'total_transaction_count': len(relevant_transactions),
                        'threshold': min_transactions,
                        'round_amounts': [t.amount for t in round_transactions]
                    }
                ))
        
        except Exception as e:
            self.logger.error(f"Error checking round amount pattern: {e}")
        
        return indicators
    
    def get_pattern_score(self, transaction: Transaction) -> float:
        """Get pattern-based fraud score"""
        try:
            indicators = self.detect_patterns(transaction)
            
            if not indicators:
                return 0.0
            
            # Calculate weighted score
            total_score = 0.0
            total_weight = 0.0
            
            for indicator in indicators:
                weight = indicator.confidence
                score = indicator.severity * weight
                total_score += score
                total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating pattern score: {e}")
            return 0.0


class FraudDetectionEngine:
    """Main fraud detection engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.ml_detector = MLFraudDetector()
        self.pattern_detector = PatternDetector()
        self.fraud_alerts: List[FraudAlert] = []
        
        # Configuration
        self.risk_thresholds = {
            FraudRiskLevel.LOW: 0.0,
            FraudRiskLevel.MEDIUM: 0.3,
            FraudRiskLevel.HIGH: 0.6,
            FraudRiskLevel.CRITICAL: 0.8
        }
        
        # Response configuration
        self.response_rules = {
            FraudRiskLevel.LOW: [ResponseAction.MONITOR],
            FraudRiskLevel.MEDIUM: [ResponseAction.FLAG, ResponseAction.MONITOR],
            FraudRiskLevel.HIGH: [ResponseAction.ALERT, ResponseAction.FLAG],
            FraudRiskLevel.CRITICAL: [ResponseAction.BLOCK, ResponseAction.ESCALATE]
        }
    
    async def analyze_transaction(self, transaction: Transaction) -> FraudScore:
        """Comprehensive fraud analysis of a transaction"""
        try:
            # Update user profile
            self.behavioral_analyzer.update_user_profile(transaction)
            user_profile = self.behavioral_analyzer.user_profiles.get(transaction.user_id)
            
            # Get behavioral analysis
            behavioral_indicators = self.behavioral_analyzer.analyze_transaction_behavior(transaction)
            behavioral_score = self.behavioral_analyzer.get_behavioral_score(transaction)
            
            # Get ML-based scores
            ml_scores = self.ml_detector.predict_fraud_probability(transaction, user_profile)
            
            # Get pattern-based analysis
            pattern_indicators = self.pattern_detector.detect_patterns(transaction)
            pattern_score = self.pattern_detector.get_pattern_score(transaction)
            
            # Combine all indicators
            all_indicators = behavioral_indicators + pattern_indicators
            
            # Calculate overall fraud score
            overall_score = self._calculate_overall_score(
                behavioral_score, ml_scores, pattern_score
            )
            
            # Determine risk level
            risk_level = self._determine_risk_level(overall_score)
            
            # Create fraud score object
            fraud_score = FraudScore(
                transaction_id=transaction.transaction_id,
                overall_score=overall_score,
                risk_level=risk_level,
                indicators=all_indicators,
                model_scores=ml_scores,
                behavioral_score=behavioral_score,
                pattern_score=pattern_score,
                metadata={
                    'analysis_timestamp': datetime.now().isoformat(),
                    'user_profile_exists': user_profile is not None,
                    'total_indicators': len(all_indicators)
                }
            )
            
            # Generate alert if necessary
            if risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]:
                await self._generate_fraud_alert(transaction, fraud_score)
            
            return fraud_score
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction: {e}")
            # Return safe default score
            return FraudScore(
                transaction_id=transaction.transaction_id,
                overall_score=0.5,  # Medium risk on error
                risk_level=FraudRiskLevel.MEDIUM,
                indicators=[],
                metadata={'error': str(e)}
            )
    
    def _calculate_overall_score(self, behavioral_score: float, ml_scores: Dict[str, float], pattern_score: float) -> float:
        """Calculate overall fraud score from component scores"""
        try:
            # Weights for different components
            weights = {
                'behavioral': 0.3,
                'ml': 0.4,
                'pattern': 0.3
            }
            
            # Calculate weighted ML score
            ml_score = 0.0
            if ml_scores:
                ml_score = sum(ml_scores.values()) / len(ml_scores)
            
            # Calculate weighted overall score
            overall_score = (
                behavioral_score * weights['behavioral'] +
                ml_score * weights['ml'] +
                pattern_score * weights['pattern']
            )
            
            return min(max(overall_score, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating overall score: {e}")
            return 0.5  # Default medium risk
    
    def _determine_risk_level(self, score: float) -> FraudRiskLevel:
        """Determine risk level based on fraud score"""
        if score >= 0.8:
            return FraudRiskLevel.CRITICAL
        elif score >= 0.6:
            return FraudRiskLevel.HIGH
        elif score >= 0.3:
            return FraudRiskLevel.MEDIUM
        else:
            return FraudRiskLevel.LOW
    
    async def _generate_fraud_alert(self, transaction: Transaction, fraud_score: FraudScore):
        """Generate fraud alert for high-risk transactions"""
        try:
            alert = FraudAlert(
                alert_id=str(uuid.uuid4()),
                transaction_id=transaction.transaction_id,
                user_id=transaction.user_id,
                fraud_score=fraud_score,
                alert_level=fraud_score.risk_level,
                message=f"High fraud risk detected for transaction {transaction.transaction_id}",
                recommended_actions=self.response_rules.get(fraud_score.risk_level, [ResponseAction.MONITOR])
            )
            
            self.fraud_alerts.append(alert)
            
            # Log alert
            self.logger.warning(
                f"Fraud alert generated: {alert.alert_id} for transaction {transaction.transaction_id} "
                f"(Risk: {fraud_score.risk_level.value}, Score: {fraud_score.overall_score:.3f})"
            )
            
            # Execute automated responses
            await self._execute_automated_responses(alert)
            
        except Exception as e:
            self.logger.error(f"Error generating fraud alert: {e}")
    
    async def _execute_automated_responses(self, alert: FraudAlert):
        """Execute automated responses based on alert level"""
        try:
            for action in alert.recommended_actions:
                if action == ResponseAction.MONITOR:
                    self.logger.info(f"Monitoring transaction {alert.transaction_id}")
                
                elif action == ResponseAction.FLAG:
                    self.logger.info(f"Flagging transaction {alert.transaction_id} for review")
                
                elif action == ResponseAction.ALERT:
                    self.logger.warning(f"Alerting on transaction {alert.transaction_id}")
                    # In a real system, this would send notifications
                
                elif action == ResponseAction.BLOCK:
                    self.logger.critical(f"Blocking transaction {alert.transaction_id}")
                    # In a real system, this would block the transaction
                
                elif action == ResponseAction.SUSPEND:
                    self.logger.critical(f"Suspending account for transaction {alert.transaction_id}")
                    # In a real system, this would suspend the account
                
                elif action == ResponseAction.ESCALATE:
                    self.logger.critical(f"Escalating transaction {alert.transaction_id} to fraud team")
                    # In a real system, this would escalate to human reviewers
            
        except Exception as e:
            self.logger.error(f"Error executing automated responses: {e}")
    
    def train_ml_models(self, training_data: List[Tuple[Transaction, bool, Optional[UserProfile]]]):
        """Train ML models with labeled fraud data"""
        try:
            self.ml_detector.train_models(training_data)
            self.logger.info(f"Trained fraud detection models with {len(training_data)} samples")
        except Exception as e:
            self.logger.error(f"Error training ML models: {e}")
    
    def get_fraud_statistics(self) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            
            # Filter alerts by time period
            alerts_24h = [a for a in self.fraud_alerts if a.timestamp >= last_24h]
            alerts_7d = [a for a in self.fraud_alerts if a.timestamp >= last_7d]
            
            # Calculate statistics
            stats = {
                'total_alerts': len(self.fraud_alerts),
                'alerts_24h': len(alerts_24h),
                'alerts_7d': len(alerts_7d),
                'alerts_by_level': {
                    level.value: len([a for a in self.fraud_alerts if a.alert_level == level])
                    for level in FraudRiskLevel
                },
                'resolved_alerts': len([a for a in self.fraud_alerts if a.resolved]),
                'resolution_rate': len([a for a in self.fraud_alerts if a.resolved]) / len(self.fraud_alerts) if self.fraud_alerts else 0,
                'ml_models_trained': self.ml_detector.is_trained,
                'user_profiles': len(self.behavioral_analyzer.user_profiles),
                'pattern_buffer_size': len(self.pattern_detector.transaction_buffer)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting fraud statistics: {e}")
            return {}
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Resolve a fraud alert"""
        try:
            for alert in self.fraud_alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    alert.resolution_notes = resolution_notes
                    
                    self.logger.info(f"Resolved fraud alert: {alert_id}")
                    return True
            
            self.logger.warning(f"Alert not found: {alert_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_user_risk_profile(self, user_id: str) -> Dict[str, Any]:
        """Get risk profile for a specific user"""
        try:
            user_profile = self.behavioral_analyzer.user_profiles.get(user_id)
            if not user_profile:
                return {'error': 'User profile not found'}
            
            # Get user's alerts
            user_alerts = [a for a in self.fraud_alerts if a.user_id == user_id]
            
            risk_profile = {
                'user_id': user_id,
                'account_age_days': (datetime.now() - user_profile.account_created).days,
                'total_transactions': len(user_profile.transaction_history),
                'behavioral_patterns': user_profile.behavioral_patterns,
                'risk_factors': user_profile.risk_factors,
                'fraud_alerts': {
                    'total': len(user_alerts),
                    'resolved': len([a for a in user_alerts if a.resolved]),
                    'by_level': {
                        level.value: len([a for a in user_alerts if a.alert_level == level])
                        for level in FraudRiskLevel
                    }
                },
                'last_updated': user_profile.last_updated.isoformat()
            }
            
            return risk_profile
            
        except Exception as e:
            self.logger.error(f"Error getting user risk profile: {e}")
            return {'error': str(e)}


# Example usage and testing
async def example_usage():
    """Demonstrate fraud detection engine"""
    print("=== Fraud Detection Engine Demo ===")
    
    # Initialize fraud detection engine
    fraud_engine = FraudDetectionEngine()
    
    # Create sample transactions
    transactions = [
        Transaction(
            transaction_id="txn_001",
            user_id="user_123",
            account_id="acc_456",
            amount=150.00,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now(),
            ip_address="192.168.1.1",
            device_id="device_001",
            location={"country": "US", "city": "New York"},
            channel="web"
        ),
        Transaction(
            transaction_id="txn_002",
            user_id="user_123",
            account_id="acc_456",
            amount=15000.00,  # Large amount
            currency="USD",
            transaction_type="transfer",
            timestamp=datetime.now(),
            ip_address="10.0.0.1",  # Different IP
            device_id="device_002",  # Different device
            location={"country": "RU", "city": "Moscow"},  # Different country
            channel="mobile"
        )
    ]
    
    print(f"Analyzing {len(transactions)} transactions...")
    
    # Analyze each transaction
    for transaction in transactions:
        print(f"\nAnalyzing transaction {transaction.transaction_id}:")
        print(f"  Amount: ${transaction.amount}")
        print(f"  User: {transaction.user_id}")
        print(f"  Location: {transaction.location}")
        
        # Perform fraud analysis
        fraud_score = await fraud_engine.analyze_transaction(transaction)
        
        print(f"  Fraud Score: {fraud_score.overall_score:.3f}")
        print(f"  Risk Level: {fraud_score.risk_level.value}")
        print(f"  Behavioral Score: {fraud_score.behavioral_score:.3f}")
        print(f"  Pattern Score: {fraud_score.pattern_score:.3f}")
        print(f"  ML Scores: {fraud_score.model_scores}")
        print(f"  Indicators: {len(fraud_score.indicators)}")
        
        for indicator in fraud_score.indicators:
            print(f"    - {indicator.description} (Severity: {indicator.severity:.2f})")
    
    # Get fraud statistics
    stats = fraud_engine.get_fraud_statistics()
    print(f"\nFraud Detection Statistics:")
    print(f"  Total Alerts: {stats.get('total_alerts', 0)}")
    print(f"  Alerts (24h): {stats.get('alerts_24h', 0)}")
    print(f"  Resolution Rate: {stats.get('resolution_rate', 0):.1%}")
    print(f"  User Profiles: {stats.get('user_profiles', 0)}")
    
    # Get user risk profile
    user_profile = fraud_engine.get_user_risk_profile("user_123")
    print(f"\nUser Risk Profile:")
    print(f"  Total Transactions: {user_profile.get('total_transactions', 0)}")
    print(f"  Fraud Alerts: {user_profile.get('fraud_alerts', {}).get('total', 0)}")
    
    print("\n=== Demo completed ===")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())