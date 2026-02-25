import socket
import requests
import json

UDP_PORT = 9100

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

print("Fog listening on UDP 9100")

while True:
    data, addr = sock.recvfrom(2048)
    print("Fog received:", data.decode())

    payload = {"message": data.decode()}

    try:
        requests.post("http://cloud:8000/ingest", json=payload)
    except Exception as e:
        print("Cloud unreachable:", e)