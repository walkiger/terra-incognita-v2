"""Vault R2-pull worker — Python scaffold for M1.10 implementation.

M1.10 replaces this stub with an async loop that:
  - Runs `litestream restore -if-replica-exists ... /var/lib/vault/db/terra.sqlite`
    every 30 s.
  - Exposes Prometheus lag metrics on :8081/metrics.
  - Logs JSON-Lines with fields: ts, level, lag_seconds, bytes_pulled,
    restore_duration_ms.
  - Backs off to 5 min on restore failure and emits an alarm-level log.

See M1-data-foundation.md §M1.10 for full acceptance criteria.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time


def _log(level: str, msg: str, **fields: object) -> None:
    print(
        json.dumps({"ts": time.time(), "level": level, "msg": msg, **fields}),
        flush=True,
    )


async def _pull_loop() -> None:
    _log("info", "r2-pull scaffold active — full implementation arrives in M1.10")
    while True:
        await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(_pull_loop())
    except KeyboardInterrupt:
        _log("info", "r2-pull shutting down")
        sys.exit(0)
