# Hub API container (M0.3)
#
# Multi-stage: uv builds `/opt/venv`; runtime runs as non-root `terra` (UID 10001).

FROM python:3.12-slim-bookworm AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/0.11.12/install.sh | sh \
    && install -m 755 /root/.local/bin/uv /usr/local/bin/uv \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements-runtime.txt .
RUN uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python --no-cache -r requirements-runtime.txt

# --- runtime ---
FROM python:3.12-slim-bookworm AS runtime

RUN groupadd --gid 10001 terra \
    && useradd --uid 10001 --gid terra --shell /usr/sbin/nologin --create-home terra

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY app ./app

USER terra
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
