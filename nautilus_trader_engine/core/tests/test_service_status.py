
import pytest
from datetime import datetime

from app.status.service_status import ServiceStatus

def test_service_status_initialization():
    status = ServiceStatus()
    assert status.kafka_connected is False
    assert status.postgres_connected is False
    assert status.clickhouse_connected is False
    assert status.duckdb_connected is False
    assert status.ib_connected is False
    assert status.redis_connected is False
    assert status.last_health_check is None

def test_service_status_to_dict():
    status = ServiceStatus()
    status.kafka_connected = True
    status.last_health_check = datetime.now()
    status_dict = status.to_dict()
    assert status_dict["kafka_connected"] is True
    assert "last_health_check" in status_dict

def test_service_status_is_healthy():
    status = ServiceStatus()
    assert status.is_healthy() is False

    status.kafka_connected = True
    status.postgres_connected = True
    status.clickhouse_connected = True
    status.duckdb_connected = True
    status.ib_connected = True
    assert status.is_healthy() is True
