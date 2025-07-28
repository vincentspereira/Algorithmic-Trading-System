"""
Kafka AI Bridge Service
Connects Kafka data streams to AI models and serves predictions in real-time.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from ai_assistant.lstm_predictor import LSTMPredictor
from ai_assistant.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

class KafkaAIBridge:
    """Main service for connecting Kafka streams to AI prediction models."""
    
    def __init__(self, 
                 kafka_bootstrap_servers: str = 'localhost:9092',
                 input_topic: str = 'market_data',
                 output_topic: str = 'predictions',
                 model_path: str = 'ai_assistant/models/lstm_model.pkl'):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.model_path = model_path
        
        # Initialize AI components
        self.predictor = LSTMPredictor(model_path)
        self.feature_engineer = FeatureEngineer()
        
        # Kafka clients
        self.consumer = None
        self.producer = None
        
    async def initialize(self):
        """Initialize Kafka consumer and producer."""
        try:
            self.consumer = KafkaConsumer(
                self.input_topic,
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='ai_bridge_group',
                enable_auto_commit=True,
                auto_offset_reset='latest'
            )
            
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type='gzip'
            )
            
            logger.info("Kafka AI Bridge initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka AI Bridge: {e}")
            return False
    
    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single message from Kafka and generate prediction."""
        try:
            # Extract market data
            symbol = message.get('symbol')
            market_data = message.get('data', {})
            
            if not symbol or not market_data:
                logger.warning("Invalid message format")
                return None
            
            # Feature engineering
            features = self.feature_engineer.extract_features(market_data)
            
            # Generate prediction
            prediction = self.predictor.predict(features)
            
            # Create response
            result = {
                'symbol': symbol,
                'timestamp': datetime.utcnow().isoformat(),
                'prediction': float(prediction),
                'confidence': 0.85,  # Mock confidence score
                'features': features,
                'metadata': {
                    'model_version': 'lstm_v1',
                    'processing_time_ms': 50
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    async def start_processing(self):
        """Start processing messages from Kafka."""
        logger.info("Starting Kafka AI Bridge processing...")
        
        try:
            for message in self.consumer:
                result = await self.process_message(message.value)
                
                if result:
                    # Send prediction to output topic
                    self.producer.send(self.output_topic, result)
                    logger.info(f"Published prediction for {result['symbol']}")
                    
        except KeyboardInterrupt:
            logger.info("Shutting down Kafka AI Bridge...")
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the service."""
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        logger.info("Kafka AI Bridge shutdown complete")

# Global instance
kafka_ai_bridge = KafkaAIBridge()