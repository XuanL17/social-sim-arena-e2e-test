FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home entrant && mkdir /data && chown entrant /data
COPY server.py .
USER entrant
ENV PORT=8787 KEYS_FILE=/app/keys.json DB_FILE=/data/replies.sqlite
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=3)"
CMD ["python", "server.py"]
