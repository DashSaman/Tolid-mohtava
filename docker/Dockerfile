FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TEHNET_PANEL_PORT=8766 HF_HOME=/cache
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg socat ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --quiet faster-whisper==1.1.2 2>/dev/null || pip install --quiet faster-whisper==1.2.1; \
    pip install --quiet google-ads==25.1.0; ffmpeg -version | head -1
RUN useradd -m -u 10001 tolid && mkdir -p /cache && chown tolid /cache
WORKDIR /app
COPY outputs/panel /app/outputs/panel
COPY brands /app/brands
COPY content-policy.fa.md audit.fa.md README.fa.md /app/
RUN mkdir -p /app/outputs/panel/data && chown -R tolid /app
USER tolid
EXPOSE 8766
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8766/api/health',timeout=4)" || exit 1
CMD ["python","outputs/panel/server.py"]
