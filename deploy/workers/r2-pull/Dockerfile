# Vault R2-pull worker.
# Build context: deploy/workers/r2-pull/ (vault.yml: context: ../workers/r2-pull).
#
# M1.10 adds litestream binary and replaces pull.py scaffold with the real
# restore loop + Prometheus metrics on :8081/metrics.

FROM python:3.12-slim-bookworm

RUN groupadd --gid 10002 terra \
    && useradd --uid 10002 --gid terra --shell /usr/sbin/nologin terra \
    && mkdir -p /var/lib/vault/db \
               /var/lib/vault/litestream \
               /var/lib/vault/snapshots/manifest \
    && chown -R terra:terra /var/lib/vault

WORKDIR /app
COPY pull.py .

USER terra

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os; assert os.path.isdir('/var/lib/vault/db')"

CMD ["python", "pull.py"]
