FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV SERVICE_NAME=control-api

COPY control_api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY shared /app/shared
COPY control_api /app/control_api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "/app/control_api", "--host", "0.0.0.0", "--port", "8000"]

