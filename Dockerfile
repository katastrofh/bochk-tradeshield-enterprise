FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tradeshield ./tradeshield
COPY static ./static
COPY sample_invoices ./sample_invoices
COPY scripts ./scripts

RUN mkdir -p /app/storage

EXPOSE 8000
CMD ["uvicorn", "tradeshield.main:app", "--host", "0.0.0.0", "--port", "8000"]
