FROM python:3.11-slim

WORKDIR /app
COPY fog.py .
COPY sensor_public.key .

RUN pip install requests pynacl

CMD ["python", "-u", "fog.py"]