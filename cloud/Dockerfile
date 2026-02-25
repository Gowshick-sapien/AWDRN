FROM python:3.11-slim

WORKDIR /app
COPY cloud.py .

RUN pip install fastapi uvicorn

CMD ["uvicorn", "cloud:app", "--host", "0.0.0.0", "--port", "8000"]