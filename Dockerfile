FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.15
COPY requirements.txt ./
RUN uv pip install --system --no-cache --torch-backend cu128 -r requirements.txt
COPY shunt/ ./shunt/
COPY scripts/download.py scripts/make_data.py scripts/train.py scripts/docker-entrypoint.sh ./scripts/
ENTRYPOINT ["sh", "/app/scripts/docker-entrypoint.sh"]
