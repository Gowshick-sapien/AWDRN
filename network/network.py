import socket
import random
import time

LISTEN_PORT = 9000
FOG_ADDR = ("fog", 9100)

LOSS_RATE = 0.2   # 20% packets dropped
MAX_DELAY = 0.5   # up to 500 ms delay

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))

print("Network emulator listening on UDP 9000")

while True:

    data, addr = sock.recvfrom(2048)

    # Packet loss simulation
    if random.random() < LOSS_RATE:
        print("Packet dropped")
        continue

    # Latency simulation
    delay = random.random() * MAX_DELAY
    time.sleep(delay)

    sock.sendto(data, FOG_ADDR)

    print(f"Forwarded packet with delay {delay:.3f}s")