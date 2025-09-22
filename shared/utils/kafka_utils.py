import os
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import logging

from shared.utils.shared_utils import load_config

def get_kafka_broker():
    """
    Retrieves the Kafka broker URL from the configuration file.

    This function loads the application's configuration, determines the current
    environment (development, production, etc.), and fetches the corresponding
    Kafka broker URL.

    Returns:
        str: The Kafka broker URL, or None if not found or on error.
    """
    try:
        config = load_config()
        env = os.getenv('TRADING_ENV', 'development')
        kafka_broker = config.get(env, {}).get('kafka_broker')
        if not kafka_broker:
            logging.error("Kafka broker not configured for environment: %s", env)
            return None
        return kafka_broker
    except Exception as e:
        logging.error("Error getting Kafka broker: %s", e, exc_info=True)
        return None


def create_kafka_producer():
    """
    Creates and returns a Kafka producer.

    This function retrieves the Kafka broker URL and initializes a KafkaProducer
    instance. It includes error handling to catch potential connectivity issues.

    Returns:
        KafkaProducer: An instance of the Kafka producer, or None if creation fails.
    """
    try:
        broker = get_kafka_broker()
        if not broker:
            return None
        producer = KafkaProducer(
            bootstrap_servers=[broker],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        return producer
    except NoBrokersAvailable:
        logging.error("Could not connect to Kafka broker at %s", broker)
        return None
    except Exception as e:
        logging.error("Failed to create Kafka producer: %s", e, exc_info=True)
        return None


def create_kafka_consumer(topic, group_id):
    """
    Creates and returns a Kafka consumer for a specific topic and group.

    Args:
        topic (str): The Kafka topic to subscribe to.
        group_id (str): The consumer group ID.

    Returns:
        KafkaConsumer: An instance of the Kafka consumer, or None if creation fails.
    """
    try:
        broker = get_kafka_broker()
        if not broker:
            return None
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[broker],
            group_id=group_id,
            auto_offset_reset='earliest',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        return consumer
    except NoBrokersAvailable:
        logging.error("Could not connect to Kafka broker at %s", broker)
        return None
    except Exception as e:
        logging.error("Failed to create Kafka consumer: %s", e, exc_info=True)
        return None