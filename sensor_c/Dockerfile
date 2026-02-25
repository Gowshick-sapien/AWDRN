FROM gcc:12

WORKDIR /app

COPY sensor.c .
COPY Makefile .

RUN make

CMD ["./sensor"]