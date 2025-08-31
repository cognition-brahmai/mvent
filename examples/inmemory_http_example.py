"""
InMemoryHTTPManager example: Simulate HTTP requests and handler routing in RAM.
"""
from mvent.core.in_memory_http import InMemoryHTTPManager

def main():
    http = InMemoryHTTPManager()

    @http.route("/greet")
    def greet_handler(request):
        data = request["data"]
        return {"greeting": f"Hello, {data['name']}!"}

    # Regular request
    resp = http.send_request("/greet", method="POST", data={"name": "Alice"})
    print("HTTP Response:", resp)

    # Streaming response (using StreamingEvent)
    @http.route("/stream")
    def stream_handler(request, stream_event=None):
        for i in range(3):
            stream_event.publish(f"Chunk {i}")
        return stream_event

    stream = http.send_request("/stream", stream=True)
    def stream_receiver(msg): print("STREAM CHUNK:", msg)
    stream.subscribe(stream_receiver)
    import time
    time.sleep(1)
    stream.stop()

if __name__ == "__main__":
    main()