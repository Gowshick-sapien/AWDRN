FROM debian:stable-slim

RUN apt-get update && \
    apt-get install -y build-essential libsodium-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY sensor.c .
COPY Makefile .
COPY keys/ ./keys/

RUN make

CMD ["./sensor"]