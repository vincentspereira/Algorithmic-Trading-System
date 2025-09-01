
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import psutil

# Prometheus metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
api_duration = Histogram('api_request_duration_seconds', 'API request duration')
system_uptime = Gauge('system_uptime_seconds', 'System uptime in seconds')
system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percent')
system_memory_usage = Gauge('system_memory_usage_bytes', 'System memory usage in bytes')
db_connection_status = Gauge('db_connection_status', 'Database connection status', ['db_name'])

class MetricsManager:
    def __init__(self):
        self.start_time = time.time()

    def record_api_request(self, method: str, endpoint: str, duration: float, status: str):
        api_requests.labels(method=method, endpoint=endpoint, status=status).inc()
        api_duration.observe(duration)

    def update_uptime(self):
        uptime = time.time() - self.start_time
        system_uptime.set(uptime)

    def update_resource_usage(self):
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        system_memory_usage.set(memory_info.rss)
        system_cpu_usage.set(cpu_percent)

    def update_db_connection_status(self, db_name: str, status: bool):
        db_connection_status.labels(db_name=db_name).set(1 if status else 0)

    def get_metrics(self):
        return generate_latest()

metrics_manager = MetricsManager()
