"""Shared route handlers for HTTP demo"""

def hello(request):
    return {"message": "Hello from in-memory server"}

def add(request):
    data = request.get("data", {})
    a = data.get("a", 0)
    b = data.get("b", 0)
    return {"result": a + b}
