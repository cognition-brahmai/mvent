from mvent.core.in_memory_http import InMemoryHTTPManager

# Create the HTTP server in memory
http = InMemoryHTTPManager()

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
    print("In-memory HTTP server loaded endpoints: /hello, /add")
    print("No real server event loop, but blocking so you can inspect or import.")
    input("Press Enter to exit server...")