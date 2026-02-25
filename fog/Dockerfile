FROM python:3.11-slim

WORKDIR /app
COPY fog.py .

RUN pip install requests

CMD ["python", "fog.py"]