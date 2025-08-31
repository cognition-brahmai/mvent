"""
SocketsManager example: In-memory, room-based messaging (like pub/sub sockets).
"""
from mvent.core.sockets_manager import SocketsManager

def main():
    sockets = SocketsManager()

    def chat_handler(msg):
        print("ROOM GOT:", msg)

    room = "general"
    sockets.connect(room)
    sockets.subscribe(room, chat_handler)
    sockets.send(room, "Hello, room!")
    sockets.send(room, "mvent sockets, in RAM only.")

    import time
    time.sleep(1)
    sockets.disconnect(room)

if __name__ == "__main__":
    main()