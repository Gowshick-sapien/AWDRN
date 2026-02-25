import socket

LISTEN_PORT = 9000
FOG_ADDR = ("fog", 9100)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))

print("Network listening on UDP 9000")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"Network received {len(data)} bytes")

    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    forward_sock.sendto(data, FOG_ADDR)
    forward_sock.close()