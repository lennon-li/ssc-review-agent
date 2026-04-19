FROM python:3.11-slim

RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

ENV PORT=8080
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
