FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app.py .

RUN mkdir -p /app/data

ENV ACEEST_DB=/app/data/aceest_fitness.db
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV PYTHONPATH=/app

VOLUME /app/data
EXPOSE 5000

CMD ["python", "app.py"]
