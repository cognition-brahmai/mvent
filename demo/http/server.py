from mvent.core.in_memory_http import InMemoryHTTPManager

# Create the HTTP server in memory
http = InMemoryHTTPManager(pool_name="global_http_demo")
print("Server pool records right after init:", http.pool.get_all())
print("Server shared memory filename:", getattr(http.pool, "filename", "<none>"))

@http.route("/hello")
def hello(request):
    return {"message": "Hello from in-memory server"}

@http.route("/add")
def add(request):
    data = request.get("data", {})
    a = data.get("a", 0)
    b = data.get("b", 0)
    return {"result": a + b}

# Optionally, expose the http instance for clients
server = http

if __name__ == "__main__":
    print("In-memory HTTP server registered the following endpoints (visible to all pool-attached processes):")
    endpoints = http.get_routes()
    for route, meta in endpoints.items():
        print(f"  {route} (handler: {meta.get('handler_name', '?')}, module: {meta.get('handler_module', '?')})")
    print("No real server event loop - routes will service any requests from processes using the same pool.")
    import threading
    import time

    def broker_loop(http):
        print("[Server] Starting broker event loop for remote requests.")
        while True:
            all_records = http.pool.get_all()
            # Find outstanding remote requests
            for key, req in list(all_records.items()):
                if not key.startswith("http_request:"):
                    continue
                route = req.get("route")
                method = req.get("method")
                data = req.get("data")
                req_id = req.get("request_id")
                # Only handle routes we have registered
                if route in http.routes:
                    try:
                        response = http.handle_request(route, method=method, data=data)
                        http.pool.set(f"http_response:{req_id}", {"response": response}, ttl=10)
                        # Delete request to prevent reprocessing
                        http.pool.delete(key)
                        print(f"[Server] Handled remote request {route} ({method}) id={req_id}")
                    except Exception as e:
                        http.pool.set(f"http_response:{req_id}", {"error": str(e)}, ttl=10)
                        http.pool.delete(key)
            time.sleep(0.1)

    # Start broker loop in the background
    broker_thread = threading.Thread(target=broker_loop, args=(http,), daemon=True)
    broker_thread.start()

    input("Press Enter to exit server...")