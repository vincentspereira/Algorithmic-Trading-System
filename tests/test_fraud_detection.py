"""
Tests for Fraud Detection Engine
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.security.fraud_detection import (
    FraudDetectionEngine,
    BehavioralAnalyzer,
    MLFraudDetector,
    PatternDetector,
    Transaction,
    UserProfile,
    FraudScore,
    FraudAlert,
    FraudIndicator,
    FraudRiskLevel,
    FraudIndicatorType,
    ResponseAction
)


class TestTransaction:
    """Test Transaction data class"""
    
    def test_transaction_creation(self):
        """Test creating a transaction"""
        transaction = Transaction(
            transaction_id="test_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        assert transaction.transaction_id == "test_001"
        assert transaction.user_id == "user_123"
        assert transaction.amount == 100.0
        assert transaction.currency == "USD"


class TestBehavioralAnalyzer:
    """Test behavioral pattern analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return BehavioralAnalyzer(lookback_days=7)
    
    @pytest.fixture
    def sample_transaction(self):
        return Transaction(
            transaction_id="test_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now(),
            channel="web"
        )
    
    def test_update_user_profile(self, analyzer, sample_transaction):
        """Test updating user profile"""
        analyzer.update_user_profile(sample_transaction)
        
        assert "user_123" in analyzer.user_profiles
        profile = analyzer.user_profiles["user_123"]
        assert len(profile.transaction_history) == 1
        assert profile.transaction_history[0] == sample_transaction
    
    def test_behavioral_patterns_calculation(self, analyzer):
        """Test behavioral patterns calculation"""
        user_id = "user_123"
        
        # Create multiple transactions with patterns
        transactions = []
        for i in range(10):
            transaction = Transaction(
                transaction_id=f"test_{i:03d}",
                user_id=user_id,
                account_id="acc_456",
                amount=100.0 + i * 10,  # Increasing amounts
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=i),
                channel="web"
            )
            transactions.append(transaction)
            analyzer.update_user_profile(transaction)
        
        profile = analyzer.user_profiles[user_id]
        patterns = profile.behavioral_patterns
        
        assert 'avg_amount' in patterns
        assert 'median_amount' in patterns
        assert 'amount_std' in patterns
        assert 'transaction_frequency' in patterns
        assert patterns['avg_amount'] > 0
    
    def test_amount_anomaly_detection(self, analyzer):
        """Test amount anomaly detection"""
        user_id = "user_123"
        
        # Create normal transactions
        for i in range(5):
            transaction = Transaction(
                transaction_id=f"normal_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=100.0,  # Normal amount
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=i+1)
            )
            analyzer.update_user_profile(transaction)
        
        # Create anomalous transaction
        anomalous_transaction = Transaction(
            transaction_id="anomaly_001",
            user_id=user_id,
            account_id="acc_456",
            amount=10000.0,  # Very large amount
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        indicators = analyzer.analyze_transaction_behavior(anomalous_transaction)
        
        # Should detect amount anomaly
        amount_anomalies = [
            i for i in indicators 
            if i.indicator_type == FraudIndicatorType.AMOUNT_ANOMALY
        ]
        assert len(amount_anomalies) > 0
        assert amount_anomalies[0].severity > 0.5
    
    def test_time_anomaly_detection(self, analyzer):
        """Test time anomaly detection"""
        user_id = "user_123"
        
        # Create transactions during normal hours (9-17)
        for i in range(5):
            timestamp = datetime.now().replace(hour=10 + i % 8)
            transaction = Transaction(
                transaction_id=f"normal_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=100.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=timestamp
            )
            analyzer.update_user_profile(transaction)
        
        # Create transaction at unusual hour
        unusual_transaction = Transaction(
            transaction_id="unusual_001",
            user_id=user_id,
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now().replace(hour=3)  # 3 AM
        )
        
        indicators = analyzer.analyze_transaction_behavior(unusual_transaction)
        
        # Should detect time anomaly
        time_anomalies = [
            i for i in indicators 
            if i.indicator_type == FraudIndicatorType.TIME_ANOMALY
        ]
        assert len(time_anomalies) > 0
    
    def test_velocity_anomaly_detection(self, analyzer):
        """Test velocity anomaly detection"""
        user_id = "user_123"
        
        # Create many transactions in short time
        base_time = datetime.now()
        for i in range(15):  # More than threshold
            transaction = Transaction(
                transaction_id=f"velocity_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=100.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=base_time - timedelta(minutes=i)
            )
            analyzer.update_user_profile(transaction)
        
        # Analyze the last transaction
        last_transaction = Transaction(
            transaction_id="velocity_last",
            user_id=user_id,
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=base_time
        )
        
        indicators = analyzer.analyze_transaction_behavior(last_transaction)
        
        # Should detect velocity anomaly
        velocity_anomalies = [
            i for i in indicators 
            if i.indicator_type == FraudIndicatorType.VELOCITY_ANOMALY
        ]
        assert len(velocity_anomalies) > 0
    
    def test_behavioral_score_calculation(self, analyzer, sample_transaction):
        """Test behavioral score calculation"""
        score = analyzer.get_behavioral_score(sample_transaction)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_new_user_handling(self, analyzer):
        """Test handling of new users"""
        new_transaction = Transaction(
            transaction_id="new_001",
            user_id="new_user",
            account_id="acc_789",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        # Should not raise errors for new users
        indicators = analyzer.analyze_transaction_behavior(new_transaction)
        score = analyzer.get_behavioral_score(new_transaction)
        
        assert isinstance(indicators, list)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestMLFraudDetector:
    """Test ML-based fraud detection"""
    
    @pytest.fixture
    def ml_detector(self):
        return MLFraudDetector()
    
    @pytest.fixture
    def sample_transaction(self):
        return Transaction(
            transaction_id="test_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
    
    def test_feature_extraction(self, ml_detector, sample_transaction):
        """Test feature extraction from transaction"""
        features = ml_detector.extract_features(sample_transaction)
        
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == 1  # Single transaction
        assert features.shape[1] > 0   # Has features
    
    def test_feature_extraction_with_profile(self, ml_detector, sample_transaction):
        """Test feature extraction with user profile"""
        user_profile = UserProfile(
            user_id="user_123",
            account_created=datetime.now() - timedelta(days=30)
        )
        user_profile.behavioral_patterns = {
            'avg_amount': 150.0,
            'transaction_frequency': 2.0,
            'preferred_hours': [10, 11, 12],
            'channel_distribution': {'web': 5, 'mobile': 3},
            'location_diversity': 2
        }
        
        features = ml_detector.extract_features(sample_transaction, user_profile)
        
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == 1
        assert features.shape[1] > 0
    
    def test_simple_fraud_scoring(self, ml_detector, sample_transaction):
        """Test simple heuristic fraud scoring"""
        scores = ml_detector._simple_fraud_scoring(sample_transaction)
        
        assert isinstance(scores, dict)
        assert 'simple_heuristic' in scores
        assert 0.0 <= scores['simple_heuristic'] <= 1.0
    
    def test_high_amount_scoring(self, ml_detector):
        """Test scoring for high amount transactions"""
        high_amount_transaction = Transaction(
            transaction_id="high_001",
            user_id="user_123",
            account_id="acc_456",
            amount=15000.0,  # High amount
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        scores = ml_detector._simple_fraud_scoring(high_amount_transaction)
        
        # Should have higher score for high amount
        assert scores['simple_heuristic'] > 0.2
    
    def test_unusual_time_scoring(self, ml_detector):
        """Test scoring for unusual time transactions"""
        late_night_transaction = Transaction(
            transaction_id="late_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now().replace(hour=2)  # 2 AM
        )
        
        scores = ml_detector._simple_fraud_scoring(late_night_transaction)
        
        # Should have higher score for unusual time
        assert scores['simple_heuristic'] > 0.1
    
    def test_predict_fraud_probability(self, ml_detector, sample_transaction):
        """Test fraud probability prediction"""
        scores = ml_detector.predict_fraud_probability(sample_transaction)
        
        assert isinstance(scores, dict)
        assert len(scores) > 0
        
        for score in scores.values():
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0


class TestPatternDetector:
    """Test pattern-based fraud detection"""
    
    @pytest.fixture
    def pattern_detector(self):
        return PatternDetector(pattern_window_hours=24)
    
    def test_transaction_buffer_management(self, pattern_detector):
        """Test transaction buffer management"""
        # Add transactions
        for i in range(5):
            transaction = Transaction(
                transaction_id=f"test_{i}",
                user_id="user_123",
                account_id="acc_456",
                amount=100.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=i)
            )
            pattern_detector.add_transaction(transaction)
        
        assert len(pattern_detector.transaction_buffer) == 5
    
    def test_card_testing_pattern_detection(self, pattern_detector):
        """Test card testing pattern detection"""
        user_id = "user_123"
        merchant_id = "merchant_001"
        
        # Create multiple small transactions (card testing pattern)
        for i in range(6):  # Above threshold
            transaction = Transaction(
                transaction_id=f"card_test_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=5.0,  # Small amount
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(minutes=i),
                merchant_id=merchant_id
            )
            pattern_detector.add_transaction(transaction)
        
        # Test with the last transaction
        test_transaction = Transaction(
            transaction_id="card_test_final",
            user_id=user_id,
            account_id="acc_456",
            amount=5.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now(),
            merchant_id=merchant_id
        )
        
        indicators = pattern_detector.detect_patterns(test_transaction)
        
        # Should detect card testing pattern
        card_testing_indicators = [
            i for i in indicators 
            if 'card_testing' in i.details.get('pattern_name', '')
        ]
        assert len(card_testing_indicators) > 0
    
    def test_velocity_attack_pattern_detection(self, pattern_detector):
        """Test velocity attack pattern detection"""
        user_id = "user_123"
        
        # Create many transactions in short time
        for i in range(12):  # Above threshold
            transaction = Transaction(
                transaction_id=f"velocity_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=100.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            pattern_detector.add_transaction(transaction)
        
        # Test with the last transaction
        test_transaction = Transaction(
            transaction_id="velocity_final",
            user_id=user_id,
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        indicators = pattern_detector.detect_patterns(test_transaction)
        
        # Should detect velocity attack pattern
        velocity_indicators = [
            i for i in indicators 
            if 'velocity_attack' in i.details.get('pattern_name', '')
        ]
        assert len(velocity_indicators) > 0
    
    def test_amount_laddering_pattern_detection(self, pattern_detector):
        """Test amount laddering pattern detection"""
        user_id = "user_123"
        
        # Create transactions with increasing amounts (non-round to avoid round pattern)
        # Use reverse order for timestamps so amounts increase chronologically
        amounts = [123, 234, 345, 456, 567]
        for i, amount in enumerate(amounts):
            transaction = Transaction(
                transaction_id=f"ladder_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=amount,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(minutes=(len(amounts)-i)*10)  # Reverse time order
            )
            pattern_detector.add_transaction(transaction)
        
        # Test with the last transaction
        test_transaction = Transaction(
            transaction_id="ladder_final",
            user_id=user_id,
            account_id="acc_456",
            amount=678,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        indicators = pattern_detector.detect_patterns(test_transaction)
        
        # Should detect amount laddering pattern
        laddering_indicators = [
            i for i in indicators 
            if 'amount_laddering' in i.details.get('pattern_name', '')
        ]
        assert len(laddering_indicators) > 0
    
    def test_round_amount_pattern_detection(self, pattern_detector):
        """Test round amount pattern detection"""
        user_id = "user_123"
        
        # Create transactions with round amounts
        round_amounts = [100, 200, 300, 500]
        for i, amount in enumerate(round_amounts):
            transaction = Transaction(
                transaction_id=f"round_{i}",
                user_id=user_id,
                account_id="acc_456",
                amount=amount,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(minutes=i*10)
            )
            pattern_detector.add_transaction(transaction)
        
        # Test with the last transaction
        test_transaction = Transaction(
            transaction_id="round_final",
            user_id=user_id,
            account_id="acc_456",
            amount=1000,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        indicators = pattern_detector.detect_patterns(test_transaction)
        
        # Should detect round amount pattern
        round_indicators = [
            i for i in indicators 
            if 'round_amount_pattern' in i.details.get('pattern_name', '')
        ]
        assert len(round_indicators) > 0
    
    def test_pattern_score_calculation(self, pattern_detector):
        """Test pattern score calculation"""
        transaction = Transaction(
            transaction_id="test_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now()
        )
        
        score = pattern_detector.get_pattern_score(transaction)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestFraudDetectionEngine:
    """Test main fraud detection engine"""
    
    @pytest.fixture
    def fraud_engine(self):
        return FraudDetectionEngine()
    
    @pytest.fixture
    def sample_transaction(self):
        return Transaction(
            transaction_id="test_001",
            user_id="user_123",
            account_id="acc_456",
            amount=100.0,
            currency="USD",
            transaction_type="purchase",
            timestamp=datetime.now(),
            ip_address="192.168.1.1",
            device_id="device_001",
            location={"country": "US", "city": "New York"}
        )
    
    @pytest.mark.asyncio
    async def test_analyze_transaction(self, fraud_engine, sample_transaction):
        """Test transaction analysis"""
        fraud_score = await fraud_engine.analyze_transaction(sample_transaction)
        
        assert isinstance(fraud_score, FraudScore)
        assert fraud_score.transaction_id == sample_transaction.transaction_id
        assert isinstance(fraud_score.overall_score, float)
        assert 0.0 <= fraud_score.overall_score <= 1.0
        assert isinstance(fraud_score.risk_level, FraudRiskLevel)
        assert isinstance(fraud_score.indicators, list)
    
    @pytest.mark.asyncio
    async def test_high_risk_transaction_analysis(self, fraud_engine):
        """Test analysis of high-risk transaction"""
        high_risk_transaction = Transaction(
            transaction_id="high_risk_001",
            user_id="user_123",
            account_id="acc_456",
            amount=50000.0,  # Very high amount
            currency="USD",
            transaction_type="transfer",
            timestamp=datetime.now().replace(hour=3),  # Unusual time
            ip_address="10.0.0.1",
            device_id="unknown_device",
            location={"country": "XX", "city": "Unknown"}
        )
        
        fraud_score = await fraud_engine.analyze_transaction(high_risk_transaction)
        
        # Should have higher risk score
        assert fraud_score.overall_score > 0.3
        assert len(fraud_score.indicators) > 0
    
    @pytest.mark.asyncio
    async def test_fraud_alert_generation(self, fraud_engine):
        """Test fraud alert generation for high-risk transactions"""
        initial_alert_count = len(fraud_engine.fraud_alerts)
        
        # Create high-risk transaction
        high_risk_transaction = Transaction(
            transaction_id="alert_test_001",
            user_id="user_456",
            account_id="acc_789",
            amount=25000.0,
            currency="USD",
            transaction_type="transfer",
            timestamp=datetime.now().replace(hour=2),
            location={"country": "XX", "city": "Unknown"}
        )
        
        fraud_score = await fraud_engine.analyze_transaction(high_risk_transaction)
        
        # Check if alert was generated for high-risk transaction
        if fraud_score.risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]:
            assert len(fraud_engine.fraud_alerts) > initial_alert_count
    
    def test_risk_level_determination(self, fraud_engine):
        """Test risk level determination"""
        # Test different score ranges
        assert fraud_engine._determine_risk_level(0.1) == FraudRiskLevel.LOW
        assert fraud_engine._determine_risk_level(0.5) == FraudRiskLevel.MEDIUM
        assert fraud_engine._determine_risk_level(0.7) == FraudRiskLevel.HIGH
        assert fraud_engine._determine_risk_level(0.9) == FraudRiskLevel.CRITICAL
    
    def test_overall_score_calculation(self, fraud_engine):
        """Test overall score calculation"""
        behavioral_score = 0.3
        ml_scores = {'model1': 0.4, 'model2': 0.6}
        pattern_score = 0.5
        
        overall_score = fraud_engine._calculate_overall_score(
            behavioral_score, ml_scores, pattern_score
        )
        
        assert isinstance(overall_score, float)
        assert 0.0 <= overall_score <= 1.0
    
    def test_fraud_statistics(self, fraud_engine):
        """Test fraud statistics generation"""
        stats = fraud_engine.get_fraud_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_alerts' in stats
        assert 'alerts_24h' in stats
        assert 'alerts_by_level' in stats
        assert 'resolution_rate' in stats
        assert 'user_profiles' in stats
    
    def test_alert_resolution(self, fraud_engine):
        """Test alert resolution"""
        # Create a mock alert
        alert = FraudAlert(
            alert_id="test_alert_001",
            transaction_id="test_txn_001",
            user_id="user_123",
            fraud_score=FraudScore(
                transaction_id="test_txn_001",
                overall_score=0.8,
                risk_level=FraudRiskLevel.HIGH,
                indicators=[]
            ),
            alert_level=FraudRiskLevel.HIGH,
            message="Test alert",
            recommended_actions=[ResponseAction.ALERT]
        )
        
        fraud_engine.fraud_alerts.append(alert)
        
        # Resolve the alert
        success = fraud_engine.resolve_alert("test_alert_001", "Resolved in test")
        
        assert success is True
        assert alert.resolved is True
        assert alert.resolution_notes == "Resolved in test"
    
    def test_user_risk_profile(self, fraud_engine, sample_transaction):
        """Test user risk profile generation"""
        # First analyze a transaction to create user profile
        fraud_engine.behavioral_analyzer.update_user_profile(sample_transaction)
        
        risk_profile = fraud_engine.get_user_risk_profile("user_123")
        
        assert isinstance(risk_profile, dict)
        assert 'user_id' in risk_profile
        assert 'total_transactions' in risk_profile
        assert 'behavioral_patterns' in risk_profile
        assert 'fraud_alerts' in risk_profile
    
    def test_user_risk_profile_not_found(self, fraud_engine):
        """Test user risk profile for non-existent user"""
        risk_profile = fraud_engine.get_user_risk_profile("non_existent_user")
        
        assert 'error' in risk_profile
        assert risk_profile['error'] == 'User profile not found'


class TestIntegration:
    """Integration tests for fraud detection system"""
    
    @pytest.mark.asyncio
    async def test_complete_fraud_detection_workflow(self):
        """Test complete fraud detection workflow"""
        fraud_engine = FraudDetectionEngine()
        
        # Create a series of transactions showing escalating fraud risk
        transactions = [
            # Normal transaction
            Transaction(
                transaction_id="normal_001",
                user_id="user_123",
                account_id="acc_456",
                amount=150.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=2),
                ip_address="192.168.1.1",
                device_id="device_001",
                location={"country": "US", "city": "New York"},
                channel="web"
            ),
            # Slightly suspicious transaction
            Transaction(
                transaction_id="suspicious_001",
                user_id="user_123",
                account_id="acc_456",
                amount=1500.0,  # Higher amount
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=1),
                ip_address="192.168.1.1",
                device_id="device_001",
                location={"country": "US", "city": "New York"},
                channel="web"
            ),
            # High-risk transaction
            Transaction(
                transaction_id="high_risk_001",
                user_id="user_123",
                account_id="acc_456",
                amount=15000.0,  # Very high amount
                currency="USD",
                transaction_type="transfer",
                timestamp=datetime.now(),
                ip_address="10.0.0.1",  # Different IP
                device_id="device_002",  # Different device
                location={"country": "RU", "city": "Moscow"},  # Different country
                channel="mobile"
            )
        ]
        
        fraud_scores = []
        
        # Analyze each transaction
        for transaction in transactions:
            fraud_score = await fraud_engine.analyze_transaction(transaction)
            fraud_scores.append(fraud_score)
            
            print(f"Transaction {transaction.transaction_id}:")
            print(f"  Amount: ${transaction.amount}")
            print(f"  Risk Level: {fraud_score.risk_level.value}")
            print(f"  Score: {fraud_score.overall_score:.3f}")
            print(f"  Indicators: {len(fraud_score.indicators)}")
        
        # Verify escalating risk scores
        assert fraud_scores[0].overall_score < fraud_scores[1].overall_score
        assert fraud_scores[1].overall_score < fraud_scores[2].overall_score
        
        # Verify high-risk transaction generates alert
        high_risk_score = fraud_scores[2]
        if high_risk_score.risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL]:
            assert len(fraud_engine.fraud_alerts) > 0
        
        # Test statistics
        stats = fraud_engine.get_fraud_statistics()
        assert stats['user_profiles'] >= 1
        assert stats['total_alerts'] >= 0
        
        # Test user risk profile
        user_profile = fraud_engine.get_user_risk_profile("user_123")
        assert user_profile['total_transactions'] == 3
        
        print("Complete fraud detection workflow test passed!")
    
    @pytest.mark.asyncio
    async def test_pattern_detection_integration(self):
        """Test pattern detection integration"""
        fraud_engine = FraudDetectionEngine()
        
        # Create card testing pattern
        user_id = "card_tester"
        merchant_id = "merchant_001"
        
        # Multiple small transactions (card testing)
        for i in range(8):
            transaction = Transaction(
                transaction_id=f"card_test_{i}",
                user_id=user_id,
                account_id="acc_789",
                amount=5.0,
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(minutes=i),
                merchant_id=merchant_id
            )
            
            fraud_score = await fraud_engine.analyze_transaction(transaction)
            
            # Later transactions should have higher scores due to pattern
            if i > 5:  # After pattern threshold
                assert fraud_score.pattern_score > 0.0
                pattern_indicators = [
                    ind for ind in fraud_score.indicators
                    if ind.indicator_type == FraudIndicatorType.PATTERN_ANOMALY
                ]
                assert len(pattern_indicators) > 0
        
        print("Pattern detection integration test passed!")
    
    @pytest.mark.asyncio
    async def test_behavioral_learning_integration(self):
        """Test behavioral learning integration"""
        fraud_engine = FraudDetectionEngine()
        
        user_id = "learning_user"
        
        # Establish normal behavior pattern
        normal_transactions = []
        for i in range(10):
            transaction = Transaction(
                transaction_id=f"normal_{i}",
                user_id=user_id,
                account_id="acc_123",
                amount=100.0 + i * 5,  # Gradually increasing
                currency="USD",
                transaction_type="purchase",
                timestamp=datetime.now() - timedelta(hours=24-i),
                ip_address="192.168.1.1",
                device_id="device_001",
                location={"country": "US", "city": "New York"},
                channel="web"
            )
            normal_transactions.append(transaction)
            
            fraud_score = await fraud_engine.analyze_transaction(transaction)
            # Early transactions should have lower behavioral scores
            # as the system learns the user's pattern
        
        # Create anomalous transaction
        anomalous_transaction = Transaction(
            transaction_id="anomaly_001",
            user_id=user_id,
            account_id="acc_123",
            amount=5000.0,  # Much higher than normal
            currency="USD",
            transaction_type="transfer",  # Different type
            timestamp=datetime.now().replace(hour=3),  # Unusual time
            ip_address="10.0.0.1",  # Different IP
            device_id="device_002",  # Different device
            location={"country": "CA", "city": "Toronto"},  # Different location
            channel="mobile"  # Different channel
        )
        
        fraud_score = await fraud_engine.analyze_transaction(anomalous_transaction)
        
        # Should detect multiple behavioral anomalies
        behavioral_indicators = [
            ind for ind in fraud_score.indicators
            if ind.indicator_type in [
                FraudIndicatorType.AMOUNT_ANOMALY,
                FraudIndicatorType.TIME_ANOMALY,
                FraudIndicatorType.LOCATION_ANOMALY,
                FraudIndicatorType.VELOCITY_ANOMALY
            ]
        ]
        
        assert len(behavioral_indicators) > 0
        assert fraud_score.behavioral_score > 0.3
        
        print("Behavioral learning integration test passed!")


if __name__ == "__main__":
    pytest.main([__file__])