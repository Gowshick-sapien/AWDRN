import socket
import time

NETWORK_ADDR = ("network", 9000)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

counter = 0

while True:
    message = f"hello {counter}"
    sock.sendto(message.encode(), NETWORK_ADDR)
    print("Sensor sent:", message)
    counter += 1
    time.sleep(3)