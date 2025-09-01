"""
Comprehensive Benchmark: mvent InMemoryHTTPManager vs FastAPI vs traditional HTTP server.
Measures throughput, latency, CPU usage, memory usage, and resource efficiency.
"""
import time
import threading
import uvicorn
import multiprocessing
import psutil
import os
import gc
from contextlib import contextmanager
from datetime import datetime
import statistics

# --- Traditional HTTP setup (http.server + requests) ---
import http.server
import socketserver
import requests

# --- FastAPI setup ---
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

HTTP_PORT = 8009
FASTAPI_PORT = 8010
RESULTS_FILE = "HTTP_BENCHMARKS.txt"

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ACK")
    
    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        pass

def start_http_server():
    with socketserver.TCPServer(("localhost", HTTP_PORT), SimpleHandler) as httpd:
        httpd.serve_forever()

# FastAPI app
app = FastAPI()

@app.post("/bench")
async def fastapi_handler(request: Request):
    body = await request.body()
    return PlainTextResponse("ACK")

def start_fastapi_server():
    uvicorn.run(app, host="localhost", port=FASTAPI_PORT, log_level="error")

# --- mvent InMemoryHTTPManager setup ---
from mvent.core.in_memory_http import InMemoryHTTPManager

def mvent_http_setup():
    http = InMemoryHTTPManager()

    @http.route("/bench")
    def handler(request):
        return "ACK"
    return http

class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.cpu_samples = []
        self.memory_samples = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        self.monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def _monitor_resources(self):
        while self.monitoring:
            try:
                # CPU percentage (non-blocking)
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append(cpu_percent)
                
                # Memory usage in MB
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                self.memory_samples.append(memory_mb)
                
                time.sleep(0.01)  # Sample every 10ms
            except:
                break
    
    def get_stats(self):
        if not self.cpu_samples or not self.memory_samples:
            return {
                'cpu_avg': 0, 'cpu_max': 0, 'cpu_min': 0,
                'memory_avg': 0, 'memory_max': 0, 'memory_min': 0,
                'memory_peak_delta': 0
            }
        
        return {
            'cpu_avg': statistics.mean(self.cpu_samples),
            'cpu_max': max(self.cpu_samples),
            'cpu_min': min(self.cpu_samples),
            'memory_avg': statistics.mean(self.memory_samples),
            'memory_max': max(self.memory_samples),
            'memory_min': min(self.memory_samples),
            'memory_peak_delta': max(self.memory_samples) - min(self.memory_samples)
        }

def benchmark_with_resources(label, sender, N=100, warmup=10):
    """Benchmark with comprehensive resource monitoring"""
    # Warmup
    print(f"  Warming up {label}...")
    for _ in range(warmup):
        sender()
    
    # Force garbage collection before measurement
    gc.collect()
    
    # Start resource monitoring
    monitor = ResourceMonitor()
    monitor.start_monitoring()
    
    # Benchmark
    print(f"  Running {label} benchmark...")
    latencies = []
    
    overall_start = time.time()
    for _ in range(N):
        req_start = time.time()
        sender()
        req_end = time.time()
        latencies.append((req_end - req_start) * 1000)  # Convert to ms
    
    overall_end = time.time()
    
    # Stop monitoring
    monitor.stop_monitoring()
    
    # Calculate metrics
    total_time = overall_end - overall_start
    throughput = N / total_time if total_time > 0 else float('inf')
    
    # Latency statistics
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    
    # Resource statistics
    resource_stats = monitor.get_stats()
    
    return {
        'label': label,
        'requests': N,
        'total_time': total_time,
        'throughput': throughput,
        'avg_latency_ms': avg_latency,
        'min_latency_ms': min_latency,
        'max_latency_ms': max_latency,
        'p95_latency_ms': p95_latency,
        'cpu_avg_percent': resource_stats['cpu_avg'],
        'cpu_max_percent': resource_stats['cpu_max'],
        'memory_avg_mb': resource_stats['memory_avg'],
        'memory_max_mb': resource_stats['memory_max'],
        'memory_delta_mb': resource_stats['memory_peak_delta'],
        'efficiency_score': throughput / max(resource_stats['cpu_avg'], 1)  # requests per CPU %
    }

@contextmanager
def http_session():
    """Context manager for HTTP session with connection pooling"""
    session = requests.Session()
    # Configure connection pooling
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=3
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    try:
        yield session
    finally:
        session.close()

def wait_for_server(url, timeout=10):
    """Wait for server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url.replace('/bench', ''), timeout=1)
            return True
        except:
            time.sleep(0.1)
    return False

def save_results(results, test_config):
    """Save benchmark results to file"""
    with open(RESULTS_FILE, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HTTP BENCHMARK RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Python Version: {os.sys.version}\n")
        f.write(f"CPU Count: {psutil.cpu_count()}\n")
        f.write(f"Total RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB\n")
        f.write(f"Test Configuration: {test_config}\n")
        f.write("-" * 80 + "\n\n")
        
        # Summary table
        f.write("PERFORMANCE SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Method':<25} {'Req/s':<12} {'Avg Lat (ms)':<12} {'CPU %':<10} {'Mem (MB)':<10} {'Efficiency':<12}\n")
        f.write("-" * 80 + "\n")
        
        for result in results:
            f.write(f"{result['label']:<25} "
                   f"{result['throughput']:<12.1f} "
                   f"{result['avg_latency_ms']:<12.2f} "
                   f"{result['cpu_avg_percent']:<10.1f} "
                   f"{result['memory_avg_mb']:<10.1f} "
                   f"{result['efficiency_score']:<12.1f}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Detailed results for each method
        for result in results:
            f.write(f"{result['label'].upper()}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Throughput:           {result['throughput']:.1f} req/s\n")
            f.write(f"Total Time:           {result['total_time']:.4f} s\n")
            f.write(f"Average Latency:      {result['avg_latency_ms']:.2f} ms\n")
            f.write(f"Min Latency:          {result['min_latency_ms']:.2f} ms\n")
            f.write(f"Max Latency:          {result['max_latency_ms']:.2f} ms\n")
            f.write(f"95th Percentile:      {result['p95_latency_ms']:.2f} ms\n")
            f.write(f"Average CPU Usage:    {result['cpu_avg_percent']:.1f}%\n")
            f.write(f"Peak CPU Usage:       {result['cpu_max_percent']:.1f}%\n")
            f.write(f"Average Memory:       {result['memory_avg_mb']:.1f} MB\n")
            f.write(f"Peak Memory:          {result['memory_max_mb']:.1f} MB\n")
            f.write(f"Memory Delta:         {result['memory_delta_mb']:.1f} MB\n")
            f.write(f"Efficiency Score:     {result['efficiency_score']:.1f} req/s per CPU%\n")
            f.write("\n")
    
    print(f"\nResults saved to {RESULTS_FILE}")

if __name__ == "__main__":
    # Test configurations
    test_configs = [
        {"N": 100, "label": "Quick Test (100 requests)"},
        {"N": 1000, "label": "Standard Test (1000 requests)"},
        {"N": 5000, "label": "Stress Test (5000 requests)"}
    ]
    
    # Let user choose test configuration
    print("Available test configurations:")
    for i, config in enumerate(test_configs):
        print(f"{i+1}. {config['label']}")
    
    try:
        choice = int(input("\nSelect test configuration (1-3): ")) - 1
        if choice < 0 or choice >= len(test_configs):
            raise ValueError()
        selected_config = test_configs[choice]
    except:
        print("Invalid selection, using Standard Test")
        selected_config = test_configs[1]
    
    N = selected_config["N"]
    print(f"\nRunning {selected_config['label']}...")
    print(f"System: {psutil.cpu_count()} CPU cores, {psutil.virtual_memory().total / (1024**3):.1f} GB RAM")
    print("=" * 80)
    
    results = []

    # --- Traditional HTTP benchmark ---
    print("\n1. Starting Traditional HTTP Server...")
    http_server_thread = threading.Thread(target=start_http_server, daemon=True)
    http_server_thread.start()
    
    if wait_for_server(f"http://localhost:{HTTP_PORT}", timeout=5):
        print("   Server ready!")
        with http_session() as session:
            def http_request():
                session.post(f"http://localhost:{HTTP_PORT}/bench", data=b"test_payload")
            
            result = benchmark_with_resources("Traditional HTTP", http_request, N)
            results.append(result)
            print(f"   ✓ {result['throughput']:.1f} req/s, {result['avg_latency_ms']:.2f}ms avg latency")
    else:
        print("   ✗ Server failed to start!")

    # --- FastAPI benchmark ---
    print("\n2. Starting FastAPI Server...")
    fastapi_process = multiprocessing.Process(target=start_fastapi_server, daemon=True)
    fastapi_process.start()
    
    if wait_for_server(f"http://localhost:{FASTAPI_PORT}", timeout=10):
        print("   Server ready!")
        with http_session() as session:
            def fastapi_request():
                session.post(f"http://localhost:{FASTAPI_PORT}/bench", data=b"test_payload")
            
            result = benchmark_with_resources("FastAPI HTTP", fastapi_request, N)
            results.append(result)
            print(f"   ✓ {result['throughput']:.1f} req/s, {result['avg_latency_ms']:.2f}ms avg latency")
    else:
        print("   ✗ Server failed to start!")
    
    if 'fastapi_process' in locals():
        fastapi_process.terminate()
        fastapi_process.join(timeout=2)

    # --- mvent HTTP benchmark ---
    print("\n3. Testing mvent InMemoryHTTPManager...")
    try:
        mvent_api = mvent_http_setup()
        
        def mvent_request():
            mvent_api.send_request("/bench", method="POST", data="test_payload")
        
        result = benchmark_with_resources("mvent InMemoryHTTP", mvent_request, N)
        results.append(result)
        print(f"   ✓ {result['throughput']:.1f} req/s, {result['avg_latency_ms']:.2f}ms avg latency")
    except Exception as e:
        print(f"   ✗ mvent test failed: {e}")

    # Save and display results
    if results:
        print("\n" + "=" * 80)
        print("BENCHMARK COMPLETE!")
        print("=" * 80)
        
        # Display summary
        print(f"\n{'Method':<25} {'Req/s':<12} {'Latency':<12} {'CPU %':<10} {'Memory':<12} {'Efficiency':<12}")
        print("-" * 85)
        
        # Sort by throughput for ranking
        results_sorted = sorted(results, key=lambda x: x['throughput'], reverse=True)
        for i, result in enumerate(results_sorted, 1):
            print(f"{i}. {result['label']:<22} "
                  f"{result['throughput']:<12.1f} "
                  f"{result['avg_latency_ms']:<9.2f}ms "
                  f"{result['cpu_avg_percent']:<10.1f} "
                  f"{result['memory_avg_mb']:<9.1f}MB "
                  f"{result['efficiency_score']:<12.1f}")
        
        save_results(results, selected_config['label'])
        
        # Performance insights
        print(f"\nKEY INSIGHTS:")
        if len(results) >= 2:
            fastest = max(results, key=lambda x: x['throughput'])
            most_efficient = max(results, key=lambda x: x['efficiency_score'])
            lowest_latency = min(results, key=lambda x: x['avg_latency_ms'])
            
            print(f"• Fastest: {fastest['label']} ({fastest['throughput']:.1f} req/s)")
            print(f"• Most Efficient: {most_efficient['label']} ({most_efficient['efficiency_score']:.1f} req/s per CPU%)")
            print(f"• Lowest Latency: {lowest_latency['label']} ({lowest_latency['avg_latency_ms']:.2f}ms)")
            
            if 'mvent' in fastest['label'].lower():
                http_result = next((r for r in results if 'HTTP' in r['label'] and 'mvent' not in r['label']), None)
                if http_result:
                    speedup = fastest['throughput'] / http_result['throughput']
                    cpu_savings = http_result['cpu_avg_percent'] - fastest['cpu_avg_percent']
                    print(f"• mvent is {speedup:.1f}x faster than traditional HTTP")
                    print(f"• mvent saves {cpu_savings:.1f}% CPU usage on average")
    else:
        print("No successful benchmarks completed!")