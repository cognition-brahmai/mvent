"""
Benchmark: mvent SocketsManager vs traditional Python sockets.
Compares pub/sub and send/recv reliability and throughput.
"""
import time
import threading
import socket

SOCKET_PORT = 9009
HOST = "127.0.0.1"

# --- Traditional socket server/client ---

def socket_server(msg_count, ack: bool = False):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind((HOST, SOCKET_PORT))
    srv.listen(1)
    conn, _ = srv.accept()
    received = 0
    while received < msg_count:
        data = conn.recv(1024)
        if data:
            received += 1
            if ack:
                conn.sendall(b"ACK")
    conn.close()
    srv.close()

def socket_client(msg_count, ack: bool = False):
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect((HOST, SOCKET_PORT))
    for _ in range(msg_count):
        cli.sendall(b"x")
        if ack:
            cli.recv(1024)
    cli.close()

# --- mvent SocketsManager setup ---
from mvent.core.sockets_manager import SocketsManager

def benchmark(label, run_func):
    t0 = time.time()
    run_func()
    dt = time.time() - t0
    print(f"{label}: {dt:.4f}s")

if __name__ == "__main__":
    N = 100

    # --- Socket benchmark (1-way, no ACK) ---
    srv = threading.Thread(target=socket_server, args=(N,))
    srv.start()
    time.sleep(0.5)
    benchmark("Traditional sockets: send/recv", lambda: socket_client(N))
    srv.join()

    # --- mvent sockets benchmark ---
    sockets = SocketsManager()
    room = "bench"
    msg_recv = []

    def handler(msg):
        msg_recv.append(msg)

    sockets.connect(room)
    sockets.subscribe(room, handler)

    def send_n():
        for i in range(N):
            sockets.send(room, f"x{i}")

    t0 = time.time()
    send_n()
    # Wait for delivery
    while len(msg_recv) < N and time.time()-t0 < 5:
        time.sleep(0.01)
    dt = time.time() - t0
    print(f"mvent SocketsManager: {len(msg_recv)} msgs in {dt:.4f}s")
    sockets.disconnect(room)