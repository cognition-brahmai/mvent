"""
Example demonstrating global HTTP endpoints across processes.
"""
import multiprocessing
import time
from mvent.core.in_memory_http import InMemoryHTTPManager

def run_server(pool_name):
    # Create HTTP manager in server process
    http = InMemoryHTTPManager(pool_name=pool_name)
    
    @http.route("/hello")
    def hello(request):
        return {"message": f"Hello from process {multiprocessing.current_process().name}!"}
    
    # Start serving: poll for global requests and handle them
    while True:
        http.poll_global_requests()  # Will sleep internally; handles all incoming requests from any process

def run_client(pool_name):
    # Create HTTP manager in client process with same pool name
    http = InMemoryHTTPManager(pool_name=pool_name)
    
    # Send request to endpoint defined in server process
    response = http.send_request("/hello")
    print(f"Client received: {response}")

if __name__ == "__main__":
    pool_name = "global_http_pool"
    
    # Start server in separate process
    server_process = multiprocessing.Process(target=run_server, args=(pool_name,))
    server_process.start()
    
    # Give server time to start
    time.sleep(1)
    
    # Run client in separate process
    client_process = multiprocessing.Process(target=run_client, args=(pool_name,))
    client_process.start()
    
    # Wait for client to finish
    client_process.join()
    
    # Clean up server
    server_process.terminate()
    server_process.join()
