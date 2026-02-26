import socket
import requests
import json
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

UDP_PORT = 9100

SIGNATURE_SIZE = 64

with open("sensor_public.key", "rb") as f:
    public_key_bytes = f.read()

verify_key = VerifyKey(public_key_bytes)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))

print("Fog listening on UDP 9100")


import struct

last_counter = -1

while True:
    data, addr = sock.recvfrom(2048)

    signature = data[-SIGNATURE_SIZE:]
    structured = data[:-SIGNATURE_SIZE]

    try:
        verify_key.verify(structured, signature)
    except BadSignatureError:
        print("Signature INVALID - dropped")
        continue

    # Parse structured data
    counter = struct.unpack(">Q", structured[0:8])[0]
    payload_len = struct.unpack(">H", structured[8:10])[0]
    payload = structured[10:10+payload_len]

    # Replay protection
    if counter <= last_counter:
        print(f"Replay detected (counter {counter}) - dropped")
        continue

    last_counter = counter

    print(f"VALID packet counter={counter}")
    print("Payload:", payload.decode())

    json_payload = {"message": payload.decode(), "counter": counter}

    try:
        requests.post("http://cloud:8000/ingest", json=json_payload)
    except Exception as e:
        print("Cloud unreachable:", e)