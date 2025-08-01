#!/usr/bin/env python3
"""
Nautilus Trader - Comprehensive Performance Test Suite

This module provides comprehensive performance testing capabilities including:
- Load testing for normal operations
- Stress testing for extreme conditions
- Endurance testing for long-running operations
- Performance baseline establishment
"""

import asyncio
import json
import time
import statistics
import logging
import argparse
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
import psutil
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import websockets
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: float
    response_time: float
    status_code: int
    error: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    thread_id: Optional[int] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None

@dataclass
class TestConfiguration:
    """Test configuration parameters"""
    base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8001"
    concurrent_users: int = 10
    requests_per_user: int = 100
    ramp_up_time: int = 60
    test_duration: int = 300
    think_time: float = 1.0
    timeout: int = 30
    endpoints: List[str] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = [
                "/health",
                "/api/v1/status",
                "/api/v1/portfolio",
                "/api/v1/orders",
                "/api/v1/positions",
                "/api/v1/market-data",
                "/graphql"
            ]

class PerformanceTestSuite:
    """Comprehensive performance test suite"""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.metrics: List[PerformanceMetrics] = []
        self.baseline_metrics: Dict[str, Any] = {}
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def run_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test"""
        logger.info(f"Starting load test with {self.config.concurrent_users} users")
        
        start_time = time.time()
        
        # Run concurrent load test
        with ThreadPoolExecutor(max_workers=self.config.concurrent_users) as executor:
            futures = []
            
            for user_id in range(self.config.concurrent_users):
                # Stagger user start times for ramp-up
                delay = (user_id * self.config.ramp_up_time) / self.config.concurrent_users
                future = executor.submit(self._simulate_user, user_id, delay)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    user_metrics = future.result()
                    self.metrics.extend(user_metrics)
                except Exception as e:
                    logger.error(f"User simulation failed: {e}")
        
        end_time = time.time()
        test_duration = end_time - start_time
        
        # Analyze results
        results = self._analyze_metrics()
        results['test_type'] = 'load_test'
        results['test_duration'] = test_duration
        results['configuration'] = asdict(self.config)
        
        logger.info(f"Load test completed in {test_duration:.2f} seconds")
        return results
    
    def run_stress_test(self) -> Dict[str, Any]:
        """Run stress test with extreme conditions"""
        logger.info("Starting stress test with extreme conditions")
        
        # Increase load progressively
        stress_config = TestConfiguration(
            base_url=self.config.base_url,
            concurrent_users=self.config.concurrent_users * 5,  # 5x normal load
            requests_per_user=self.config.requests_per_user * 2,  # 2x requests
            ramp_up_time=30,  # Faster ramp-up
            think_time=0.1,  # Minimal think time
            timeout=10  # Shorter timeout
        )
        
        original_config = self.config
        self.config = stress_config
        
        try:
            results = self.run_load_test()
            results['test_type'] = 'stress_test'
            return results
        finally:
            self.config = original_config
    
    def run_endurance_test(self, duration_hours: int = 2) -> Dict[str, Any]:
        """Run endurance test for long-running operations"""
        logger.info(f"Starting endurance test for {duration_hours} hours")
        
        endurance_config = TestConfiguration(
            base_url=self.config.base_url,
            concurrent_users=max(1, self.config.concurrent_users // 2),  # Reduced load
            test_duration=duration_hours * 3600,  # Convert to seconds
            think_time=5.0,  # Longer think time
            timeout=60  # Longer timeout
        )
        
        original_config = self.config
        self.config = endurance_config
        
        try:
            start_time = time.time()
            end_time = start_time + endurance_config.test_duration
            
            # Run continuous test
            while time.time() < end_time:
                batch_results = self.run_load_test()
                
                # Check for performance degradation
                if self._detect_performance_degradation(batch_results):
                    logger.warning("Performance degradation detected during endurance test")
                
                # Brief pause between batches
                time.sleep(60)
            
            results = self._analyze_metrics()
            results['test_type'] = 'endurance_test'
            results['test_duration'] = time.time() - start_time
            
            return results
        finally:
            self.config = original_config
    
    def establish_baseline(self) -> Dict[str, Any]:
        """Establish performance baseline"""
        logger.info("Establishing performance baseline")
        
        # Run baseline test with minimal load
        baseline_config = TestConfiguration(
            base_url=self.config.base_url,
            concurrent_users=1,
            requests_per_user=50,
            think_time=1.0
        )
        
        original_config = self.config
        self.config = baseline_config
        
        try:
            results = self.run_load_test()
            results['test_type'] = 'baseline'
            
            # Store baseline metrics
            self.baseline_metrics = {
                'avg_response_time': results['avg_response_time'],
                'p95_response_time': results['p95_response_time'],
                'p99_response_time': results['p99_response_time'],
                'error_rate': results['error_rate'],
                'throughput': results['throughput']
            }
            
            # Save baseline to file
            baseline_file = Path("performance/baseline_metrics.json")
            baseline_file.parent.mkdir(exist_ok=True)
            with open(baseline_file, 'w') as f:
                json.dump(self.baseline_metrics, f, indent=2)
            
            logger.info("Baseline established and saved")
            return results
        finally:
            self.config = original_config
    
    def _simulate_user(self, user_id: int, delay: float) -> List[PerformanceMetrics]:
        """Simulate individual user behavior"""
        if delay > 0:
            time.sleep(delay)
        
        user_metrics = []
        
        for request_num in range(self.config.requests_per_user):
            # Select random endpoint
            endpoint = np.random.choice(self.config.endpoints)
            
            # Record system metrics before request
            process = psutil.Process()
            cpu_before = process.cpu_percent()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Make request
            start_time = time.time()
            try:
                if endpoint == "/graphql":
                    response = self._make_graphql_request()
                else:
                    response = self.session.get(
                        f"{self.config.base_url}{endpoint}",
                        timeout=self.config.timeout
                    )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                # Record metrics
                metrics = PerformanceMetrics(
                    timestamp=start_time,
                    response_time=response_time,
                    status_code=response.status_code,
                    memory_usage=memory_before,
                    cpu_usage=cpu_before,
                    thread_id=user_id,
                    request_size=len(response.request.body) if response.request.body else 0,
                    response_size=len(response.content)
                )
                
                user_metrics.append(metrics)
                
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                metrics = PerformanceMetrics(
                    timestamp=start_time,
                    response_time=response_time,
                    status_code=0,
                    error=str(e),
                    memory_usage=memory_before,
                    cpu_usage=cpu_before,
                    thread_id=user_id
                )
                
                user_metrics.append(metrics)
            
            # Think time
            if self.config.think_time > 0:
                time.sleep(self.config.think_time)
        
        return user_metrics
    
    def _make_graphql_request(self) -> requests.Response:
        """Make GraphQL request"""
        query = """
        query {
            portfolio {
                totalValue
                positions {
                    symbol
                    quantity
                    marketValue
                }
            }
        }
        """
        
        return self.session.post(
            f"{self.config.base_url}/graphql",
            json={"query": query},
            timeout=self.config.timeout
        )
    
    def _analyze_metrics(self) -> Dict[str, Any]:
        """Analyze collected performance metrics"""
        if not self.metrics:
            return {}
        
        # Extract response times and status codes
        response_times = [m.response_time for m in self.metrics if m.error is None]
        status_codes = [m.status_code for m in self.metrics]
        errors = [m for m in self.metrics if m.error is not None]
        
        # Calculate statistics
        total_requests = len(self.metrics)
        successful_requests = len(response_times)
        error_count = len(errors)
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = np.percentile(response_times, 95)
            p99_response_time = np.percentile(response_times, 99)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            std_response_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = std_response_time = 0
        
        # Calculate throughput
        if self.metrics:
            test_start = min(m.timestamp for m in self.metrics)
            test_end = max(m.timestamp for m in self.metrics)
            test_duration = test_end - test_start
            throughput = successful_requests / test_duration if test_duration > 0 else 0
        else:
            throughput = 0
        
        # Status code distribution
        status_code_dist = {}
        for code in status_codes:
            status_code_dist[code] = status_code_dist.get(code, 0) + 1
        
        # Memory and CPU statistics
        memory_usage = [m.memory_usage for m in self.metrics if m.memory_usage is not None]
        cpu_usage = [m.cpu_usage for m in self.metrics if m.cpu_usage is not None]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'error_count': error_count,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'median_response_time': median_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'std_response_time': std_response_time,
            'throughput': throughput,
            'status_code_distribution': status_code_dist,
            'errors': [{'error': e.error, 'timestamp': e.timestamp} for e in errors[:10]],  # First 10 errors
        }
        
        if memory_usage:
            results['avg_memory_usage'] = statistics.mean(memory_usage)
            results['max_memory_usage'] = max(memory_usage)
        
        if cpu_usage:
            results['avg_cpu_usage'] = statistics.mean(cpu_usage)
            results['max_cpu_usage'] = max(cpu_usage)
        
        return results
    
    def _detect_performance_degradation(self, current_results: Dict[str, Any]) -> bool:
        """Detect performance degradation compared to baseline"""
        if not self.baseline_metrics:
            return False
        
        # Check response time degradation (>20% increase)
        if current_results.get('avg_response_time', 0) > self.baseline_metrics['avg_response_time'] * 1.2:
            return True
        
        # Check error rate increase (>5% increase)
        if current_results.get('error_rate', 0) > self.baseline_metrics['error_rate'] + 5:
            return True
        
        # Check throughput degradation (>20% decrease)
        if current_results.get('throughput', 0) < self.baseline_metrics['throughput'] * 0.8:
            return True
        
        return False
    
    def generate_report(self, results: Dict[str, Any], output_file: str = None) -> str:
        """Generate comprehensive performance test report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"performance/report_{results.get('test_type', 'unknown')}_{timestamp}.html"
        
        # Create visualizations
        self._create_visualizations(results)
        
        # Generate HTML report
        html_content = self._generate_html_report(results)
        
        # Save report
        Path(output_file).parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Performance report generated: {output_file}")
        return output_file
    
    def _create_visualizations(self, results: Dict[str, Any]):
        """Create performance visualizations"""
        if not self.metrics:
            return
        
        # Response time distribution
        response_times = [m.response_time for m in self.metrics if m.error is None]
        
        if response_times:
            plt.figure(figsize=(12, 8))
            
            # Response time histogram
            plt.subplot(2, 2, 1)
            plt.hist(response_times, bins=50, alpha=0.7, color='blue')
            plt.title('Response Time Distribution')
            plt.xlabel('Response Time (ms)')
            plt.ylabel('Frequency')
            
            # Response time over time
            plt.subplot(2, 2, 2)
            timestamps = [m.timestamp for m in self.metrics if m.error is None]
            plt.plot(timestamps, response_times, alpha=0.6)
            plt.title('Response Time Over Time')
            plt.xlabel('Time')
            plt.ylabel('Response Time (ms)')
            
            # Throughput over time
            plt.subplot(2, 2, 3)
            # Calculate throughput in 10-second windows
            window_size = 10
            throughput_data = self._calculate_windowed_throughput(window_size)
            if throughput_data:
                times, throughputs = zip(*throughput_data)
                plt.plot(times, throughputs, color='green')
            plt.title('Throughput Over Time')
            plt.xlabel('Time')
            plt.ylabel('Requests/Second')
            
            # Status code distribution
            plt.subplot(2, 2, 4)
            status_codes = list(results['status_code_distribution'].keys())
            counts = list(results['status_code_distribution'].values())
            plt.bar([str(code) for code in status_codes], counts)
            plt.title('Status Code Distribution')
            plt.xlabel('Status Code')
            plt.ylabel('Count')
            
            plt.tight_layout()
            plt.savefig('performance/performance_charts.png', dpi=300, bbox_inches='tight')
            plt.close()
    
    def _calculate_windowed_throughput(self, window_size: int) -> List[tuple]:
        """Calculate throughput in time windows"""
        if not self.metrics:
            return []
        
        start_time = min(m.timestamp for m in self.metrics)
        end_time = max(m.timestamp for m in self.metrics)
        
        throughput_data = []
        current_time = start_time
        
        while current_time < end_time:
            window_end = current_time + window_size
            window_requests = [
                m for m in self.metrics 
                if current_time <= m.timestamp < window_end and m.error is None
            ]
            throughput = len(window_requests) / window_size
            throughput_data.append((current_time, throughput))
            current_time = window_end
        
        return throughput_data
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate HTML performance report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nautilus Trader Performance Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
                .metric-card { background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007cba; }
                .metric-value { font-size: 24px; font-weight: bold; color: #007cba; }
                .metric-label { font-size: 14px; color: #666; }
                .chart { text-align: center; margin: 20px 0; }
                .error-list { background-color: #ffe6e6; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .pass { color: green; } .fail { color: red; } .warning { color: orange; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Nautilus Trader Performance Test Report</h1>
                <p><strong>Test Type:</strong> {test_type}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p><strong>Test Duration:</strong> {test_duration:.2f} seconds</p>
            </div>
            
            <h2>Performance Metrics</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{total_requests}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{successful_requests}</div>
                    <div class="metric-label">Successful Requests</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{error_rate:.2f}%</div>
                    <div class="metric-label">Error Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{avg_response_time:.2f}ms</div>
                    <div class="metric-label">Average Response Time</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{p95_response_time:.2f}ms</div>
                    <div class="metric-label">95th Percentile Response Time</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{p99_response_time:.2f}ms</div>
                    <div class="metric-label">99th Percentile Response Time</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{throughput:.2f}</div>
                    <div class="metric-label">Throughput (req/sec)</div>
                </div>
            </div>
            
            <h2>Performance Charts</h2>
            <div class="chart">
                <img src="performance_charts.png" alt="Performance Charts" style="max-width: 100%;">
            </div>
            
            <h2>Test Configuration</h2>
            <pre>{configuration}</pre>
            
            {error_section}
            
            <h2>Performance Assessment</h2>
            <div class="assessment">
                {assessment}
            </div>
        </body>
        </html>
        """
        
        # Generate error section if there are errors
        error_section = ""
        if results.get('errors'):
            error_list = "\n".join([f"<li>{error['error']} (at {error['timestamp']})</li>" for error in results['errors']])
            error_section = f"""
            <h2>Errors</h2>
            <div class="error-list">
                <ul>{error_list}</ul>
            </div>
            """
        
        # Generate performance assessment
        assessment = self._generate_performance_assessment(results)
        
        return html_template.format(
            test_type=results.get('test_type', 'Unknown'),
            timestamp=results.get('timestamp', 'Unknown'),
            test_duration=results.get('test_duration', 0),
            total_requests=results.get('total_requests', 0),
            successful_requests=results.get('successful_requests', 0),
            error_rate=results.get('error_rate', 0),
            avg_response_time=results.get('avg_response_time', 0),
            p95_response_time=results.get('p95_response_time', 0),
            p99_response_time=results.get('p99_response_time', 0),
            throughput=results.get('throughput', 0),
            configuration=json.dumps(results.get('configuration', {}), indent=2),
            error_section=error_section,
            assessment=assessment
        )
    
    def _generate_performance_assessment(self, results: Dict[str, Any]) -> str:
        """Generate performance assessment based on results"""
        assessments = []
        
        # Response time assessment
        avg_response_time = results.get('avg_response_time', 0)
        if avg_response_time < 100:
            assessments.append('<p class="pass">✓ Excellent response time (&lt;100ms)</p>')
        elif avg_response_time < 500:
            assessments.append('<p class="warning">⚠ Good response time (&lt;500ms)</p>')
        else:
            assessments.append('<p class="fail">✗ Poor response time (&gt;500ms)</p>')
        
        # Error rate assessment
        error_rate = results.get('error_rate', 0)
        if error_rate < 1:
            assessments.append('<p class="pass">✓ Excellent error rate (&lt;1%)</p>')
        elif error_rate < 5:
            assessments.append('<p class="warning">⚠ Acceptable error rate (&lt;5%)</p>')
        else:
            assessments.append('<p class="fail">✗ High error rate (&gt;5%)</p>')
        
        # Throughput assessment
        throughput = results.get('throughput', 0)
        if throughput > 100:
            assessments.append('<p class="pass">✓ High throughput (&gt;100 req/sec)</p>')
        elif throughput > 50:
            assessments.append('<p class="warning">⚠ Moderate throughput (&gt;50 req/sec)</p>')
        else:
            assessments.append('<p class="fail">✗ Low throughput (&lt;50 req/sec)</p>')
        
        return "\n".join(assessments)

async def run_websocket_test(websocket_url: str, duration: int = 60) -> Dict[str, Any]:
    """Run WebSocket performance test"""
    logger.info(f"Starting WebSocket performance test for {duration} seconds")
    
    metrics = []
    start_time = time.time()
    end_time = start_time + duration
    
    async def websocket_client():
        try:
            async with websockets.connect(websocket_url) as websocket:
                while time.time() < end_time:
                    # Send ping and measure response time
                    ping_start = time.time()
                    await websocket.send(json.dumps({"type": "ping", "timestamp": ping_start}))
                    
                    response = await websocket.recv()
                    ping_end = time.time()
                    
                    response_time = (ping_end - ping_start) * 1000  # Convert to ms
                    
                    metrics.append({
                        'timestamp': ping_start,
                        'response_time': response_time,
                        'message_type': 'ping'
                    })
                    
                    await asyncio.sleep(1)  # 1 second interval
                    
        except Exception as e:
            logger.error(f"WebSocket test error: {e}")
    
    # Run WebSocket test
    await websocket_client()
    
    # Analyze results
    if metrics:
        response_times = [m['response_time'] for m in metrics]
        results = {
            'test_type': 'websocket_test',
            'duration': duration,
            'total_messages': len(metrics),
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': np.percentile(response_times, 95),
            'p99_response_time': np.percentile(response_times, 99)
        }
    else:
        results = {
            'test_type': 'websocket_test',
            'duration': duration,
            'total_messages': 0,
            'error': 'No messages received'
        }
    
    return results

def main():
    """Main function to run performance tests"""
    parser = argparse.ArgumentParser(description='Nautilus Trader Performance Test Suite')
    parser.add_argument('--test-type', choices=['load', 'stress', 'endurance', 'baseline', 'websocket'], 
                       default='load', help='Type of test to run')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL for API tests')
    parser.add_argument('--websocket-url', default='ws://localhost:8001', help='WebSocket URL')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--requests', type=int, default=100, help='Requests per user')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    # Create test configuration
    config = TestConfiguration(
        base_url=args.base_url,
        websocket_url=args.websocket_url,
        concurrent_users=args.users,
        requests_per_user=args.requests,
        test_duration=args.duration
    )
    
    # Create test suite
    test_suite = PerformanceTestSuite(config)
    
    # Run specified test
    if args.test_type == 'load':
        results = test_suite.run_load_test()
    elif args.test_type == 'stress':
        results = test_suite.run_stress_test()
    elif args.test_type == 'endurance':
        results = test_suite.run_endurance_test(duration_hours=args.duration // 3600)
    elif args.test_type == 'baseline':
        results = test_suite.establish_baseline()
    elif args.test_type == 'websocket':
        results = asyncio.run(run_websocket_test(args.websocket_url, args.duration))
    
    # Generate report
    if args.test_type != 'websocket':
        report_file = test_suite.generate_report(results, args.output)
        print(f"Report generated: {report_file}")
    
    # Print summary
    print(f"\nTest Results Summary:")
    print(f"Test Type: {results.get('test_type', 'Unknown')}")
    if 'total_requests' in results:
        print(f"Total Requests: {results['total_requests']}")
        print(f"Successful Requests: {results['successful_requests']}")
        print(f"Error Rate: {results['error_rate']:.2f}%")
        print(f"Average Response Time: {results['avg_response_time']:.2f}ms")
        print(f"95th Percentile: {results['p95_response_time']:.2f}ms")
        print(f"Throughput: {results['throughput']:.2f} req/sec")

if __name__ == "__main__":
    main()