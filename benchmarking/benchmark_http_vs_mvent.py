"""
Benchmark: mvent InMemoryHTTPManager vs FastAPI vs traditional HTTP server.
Measures throughput and latency for a large batch of request/responses.
"""
import time
import threading
import uvicorn
import multiprocessing
from contextlib import contextmanager

# --- Traditional HTTP setup (http.server + requests) ---
import http.server
import socketserver
import requests

# --- FastAPI setup ---
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

HTTP_PORT = 8009
FASTAPI_PORT = 8010

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ACK")

def start_http_server():
    with socketserver.TCPServer(("localhost", HTTP_PORT), SimpleHandler) as httpd:
        httpd.serve_forever()

# FastAPI app
app = FastAPI()

@app.post("/bench")
async def fastapi_handler(request: Request):
    # Read the request body (equivalent to the other handlers)
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
        # Simulate server handling
        return "ACK"
    return http

def benchmark_requests(label, sender, N=100):
    t0 = time.time()
    for _ in range(N):
        sender()
    elapsed = time.time() - t0
    # Prevent division by zero for extremely fast benchmarks
    if elapsed == 0:
        elapsed = 1e-9
        print(f"{label}: {N} requests finished almost instantly (elapsed < 1ms)")
    print(f"{label}: {N} requests in {elapsed:.4f}s, {N/elapsed:.1f} req/s")

@contextmanager
def http_session():
    """Context manager for HTTP session to enable connection reuse"""
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()

def wait_for_server(url, timeout=10):
    """Wait for server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=1)
            return True
        except:
            time.sleep(0.1)
    return False

if __name__ == "__main__":
    N = 100
    
    print(f"Running benchmark with {N} requests per test...\n")

    # --- Traditional HTTP benchmark ---
    print("Starting traditional HTTP server...")
    http_server_thread = threading.Thread(target=start_http_server, daemon=True)
    http_server_thread.start()
    
    # Wait for HTTP server to be ready
    if wait_for_server(f"http://localhost:{HTTP_PORT}", timeout=5):
        print("HTTP server ready!")
    else:
        print("HTTP server failed to start!")
        exit(1)

    with http_session() as session:
        def http_request():
            session.post(f"http://localhost:{HTTP_PORT}/bench", data=b"x")

        benchmark_requests("Traditional HTTP", http_request, N)

    # --- FastAPI benchmark ---
    print("\nStarting FastAPI server...")
    # Use multiprocessing for FastAPI to avoid blocking
    fastapi_process = multiprocessing.Process(target=start_fastapi_server, daemon=True)
    fastapi_process.start()
    
    # Wait for FastAPI server to be ready
    if wait_for_server(f"http://localhost:{FASTAPI_PORT}/bench", timeout=10):
        print("FastAPI server ready!")
    else:
        print("FastAPI server failed to start!")
        fastapi_process.terminate()
        exit(1)

    with http_session() as session:
        def fastapi_request():
            session.post(f"http://localhost:{FASTAPI_PORT}/bench", data=b"x")

        benchmark_requests("FastAPI HTTP", fastapi_request, N)

    # Cleanup FastAPI process
    fastapi_process.terminate()
    fastapi_process.join()

    # --- mvent HTTP benchmark ---
    print("\nTesting mvent InMemoryHTTPManager...")
    mvent_api = mvent_http_setup()
    
    def mvent_request():
        mvent_api.send_request("/bench", method="POST", data="x")

    benchmark_requests("mvent InMemoryHTTPManager", mvent_request, N)
    
    print("\nBenchmark complete!")
    print("\nNotes:")
    print("- Traditional HTTP: Basic Python http.server")
    print("- FastAPI HTTP: Modern ASGI server with async handling")  
    print("- mvent: In-memory HTTP simulation")
    print("- All tests use session-based connection reuse for fair comparison")