# Vault R2-pull worker.
# Build context: deploy/workers/r2-pull/ (vault.yml: context: ../workers/r2-pull).

FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSL https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz \
      | tar xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/litestream \
    && pip install --no-cache-dir prometheus-client==0.21.1 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10002 terra \
    && useradd --uid 10002 --gid terra --shell /usr/sbin/nologin terra \
    && mkdir -p /var/lib/vault/db \
               /var/lib/vault/litestream \
               /var/lib/vault/snapshots/manifest \
    && chown -R terra:terra /var/lib/vault

WORKDIR /app
COPY pull.py .

USER terra

EXPOSE 8081
EXPOSE 8082

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os; assert os.path.isdir('/var/lib/vault/db')"

CMD ["python", "pull.py"]
