"""
StreamingEvent example: Real-time publish/subscribe in RAM.
"""
from mvent.core.streaming_event import StreamingEvent

def main():
    stream = StreamingEvent(stream_key="chatroom1")

    def receiver(data):
        print("STREAMED MESSAGE:", data)

    stream.subscribe(receiver)

    # Simulate publishing several messages ("chunks")
    for i in range(5):
        stream.publish(f"Live chunk {i}")
    import time
    time.sleep(1)
    stream.stop()

if __name__ == "__main__":
    main()