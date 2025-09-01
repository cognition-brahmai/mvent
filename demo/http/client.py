from mvent.core.in_memory_http import InMemoryHTTPManager

POOL_NAME = "global_http_demo"

def main():
    import time

    # Create a new HTTP client connected to the same pool as server.py
    client = InMemoryHTTPManager(pool_name=POOL_NAME)
    print("Client shared memory filename:", getattr(client.pool, "filename", "<none>"))
    print("Client pool records before polling:", client.pool.get_all())

    print("Client shared memory filename:", getattr(client.pool, "filename", "<none>"))
    print("Client sees global endpoints (current):", list(client.get_routes().keys()))

    # Wait for /hello endpoint to appear in manager cache (up to 5 seconds)
    for wait in range(20):
        endpoints = client.get_routes()
        print(f"Polling pool for endpoints: {list(endpoints.keys())}")
        if "/hello" in endpoints:
            break
        time.sleep(0.25)
    else:
        print("ERROR: /hello endpoint not globally available in HTTP route registry.")
        return

    # Demonstrate remote-call via shared memory: place request, wait for server to reply
    import uuid
    import time

    def remote_call(route, method="GET", data=None, pool=None, timeout=5.0):
        req_id = str(uuid.uuid4())
        pool.set(f"http_request:{req_id}", {
            "route": route,
            "method": method,
            "data": data,
            "request_id": req_id
        }, ttl=10)
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = pool.get(f"http_response:{req_id}")
            if resp is not None:
                pool.delete(f"http_response:{req_id}")
                return resp.get("response") if "response" in resp else resp.get("error")
            time.sleep(0.05)
        return "ERROR: Timeout waiting for response."

    print("Making remote call to /hello (GET)...")
    result = remote_call("/hello", method="GET", pool=client.pool)
    print("Response from /hello:", result)
    print("Making remote call to /add (POST)...")
    result = remote_call("/add", method="POST", data={"a": 7, "b": 5}, pool=client.pool)
    print("Response from /add:", result)

if __name__ == "__main__":
    main()
