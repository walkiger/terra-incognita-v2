"""Vault R2-pull worker — periodic Litestream restore from Hub replica (M1.10)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from prometheus_client import Counter, Gauge, start_http_server

CONFIG_PATH = Path(os.environ.get("LITESTREAM_CONFIG", "/etc/litestream.yml"))
DB_PATH = Path(os.environ.get("VAULT_DB_PATH", "/var/lib/vault/db/terra.sqlite"))
WORKER_VERSION = os.environ.get("WORKER_VERSION", "0.1.0-m110")

INTERVAL_DEFAULT_S = 30
BACKOFF_MAX_S = 300

restore_failures_total = Counter(
    "vault_litestream_restore_failures_total",
    "Litestream restore iterations that exited non-zero",
)
restore_success_total = Counter(
    "vault_litestream_restore_success_total",
    "Litestream restore iterations that exited zero",
)
restore_duration_seconds = Gauge(
    "vault_litestream_restore_duration_seconds",
    "Wall duration of last Litestream restore subprocess",
)
restore_lag_seconds = Gauge(
    "vault_litestream_lag_seconds",
    "Approx lag from DB mtime to wall clock after successful restore",
)
db_file_bytes = Gauge(
    "vault_litestream_db_file_bytes",
    "Observed local replica SQLite size after restore",
)

STATE_LOCK = threading.Lock()
STATE: dict[str, Any] = {
    "ok": False,
    "last_pull_ts": None,
    "lag_s": None,
    "db_size_bytes": None,
    "version": WORKER_VERSION,
}

LOG = logging.getLogger("r2-pull")


def _log_json(level: str, msg: str, **fields: object) -> None:
    payload = {"ts": time.time(), "level": level, "msg": msg, **fields}
    print(json.dumps(payload), flush=True)


def _update_state(**fields: Any) -> None:
    with STATE_LOCK:
        STATE.update(fields)


class _StatusHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.debug(fmt, *args)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/vault/status":
            self.send_response(404)
            self.end_headers()
            return
        with STATE_LOCK:
            body = json.dumps(dict(STATE)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_status_server() -> tuple[HTTPServer, threading.Thread]:
    host = os.environ.get("STATUS_BIND", "0.0.0.0")
    port = int(os.environ.get("STATUS_PORT", "8082"))
    server = HTTPServer((host, port), _StatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _run_litestream_restore() -> subprocess.CompletedProcess[str]:
    cmd = [
        "litestream",
        "restore",
        "-config",
        str(CONFIG_PATH),
        "-if-replica-exists",
        str(DB_PATH),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("RESTORE_TIMEOUT_SEC", "900")),
        check=False,
    )


async def _restore_iteration(backoff_s: float) -> float:
    loop = asyncio.get_running_loop()
    t0 = time.perf_counter()
    proc = await loop.run_in_executor(None, _run_litestream_restore)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    restore_duration_seconds.set(time.perf_counter() - t0)

    if proc.returncode != 0:
        restore_failures_total.inc()
        _log_json(
            "error",
            "litestream restore failed",
            lag_seconds=None,
            bytes_pulled=None,
            restore_duration_ms=duration_ms,
            stderr_tail=proc.stderr[-400:] if proc.stderr else "",
            stdout_tail=proc.stdout[-400:] if proc.stdout else "",
        )
        _update_state(ok=False)
        next_sleep = min(BACKOFF_MAX_S, max(backoff_s * 2, INTERVAL_DEFAULT_S))
        if next_sleep >= BACKOFF_MAX_S:
            _log_json(
                "critical",
                "restore failures backing off to ceiling",
                lag_seconds=None,
                bytes_pulled=None,
                restore_duration_ms=duration_ms,
            )
        return next_sleep

    restore_success_total.inc()
    lag_s_val: float | None = None
    bytes_val = 0
    try:
        st = DB_PATH.stat()
        bytes_val = st.st_size
        lag_s_val = max(0.0, time.time() - st.st_mtime)
        restore_lag_seconds.set(lag_s_val)
        db_file_bytes.set(float(bytes_val))
    except OSError:
        pass

    _log_json(
        "info",
        "litestream restore ok",
        lag_seconds=lag_s_val,
        bytes_pulled=bytes_val,
        restore_duration_ms=duration_ms,
    )
    _update_state(
        ok=True,
        last_pull_ts=time.time(),
        lag_s=lag_s_val,
        db_size_bytes=bytes_val,
        version=WORKER_VERSION,
    )
    return INTERVAL_DEFAULT_S


async def main() -> None:
    metrics_port = int(os.environ.get("METRICS_PORT", "8081"))
    start_http_server(metrics_port)
    _start_status_server()

    _log_json("info", "r2-pull worker starting", metrics_port=metrics_port)
    backoff = float(INTERVAL_DEFAULT_S)
    while True:
        sleep_for = await _restore_iteration(backoff)
        backoff = sleep_for
        await asyncio.sleep(sleep_for)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _log_json("info", "r2-pull shutting down")
