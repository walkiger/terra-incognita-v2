import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_ROOT = ROOT / "memory"

TYPE_TO_DIR = {
    "system": MEMORY_ROOT / "system",
    "agents": MEMORY_ROOT / "agents",
    "features": MEMORY_ROOT / "features",
    "runtime": MEMORY_ROOT / "runtime",
}


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {' '.join(cmd)}")


def write_memory(mem_type: str, key: str, content: str, append: bool) -> Path:
    if mem_type not in TYPE_TO_DIR:
        raise ValueError(f"Unsupported memory type: {mem_type}")

    target_dir = TYPE_TO_DIR[mem_type]
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{key}.md"

    stamp = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    block = f"\n\n---\nUpdated: {stamp}\n\n{content.strip()}\n"

    if append and path.exists():
        path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
    else:
        path.write_text(content.strip() + "\n", encoding="utf-8")

    return path


def maybe_commit(path: Path, message: str) -> None:
    run(["git", "add", str(path)])
    run(["git", "commit", "-m", message])


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Agent OS memory entries.")
    parser.add_argument("--type", required=True, choices=TYPE_TO_DIR.keys())
    parser.add_argument("--key", required=True, help="Memory key -> filename without .md")
    parser.add_argument("--content", required=True, help="Content to write.")
    parser.add_argument("--append", action="store_true", help="Append with timestamp block.")
    parser.add_argument("--commit", action="store_true", help="Commit memory update.")
    parser.add_argument("--commit-message", default="docs(memory): update memory entry")
    args = parser.parse_args()

    path = write_memory(args.type, args.key, args.content, args.append)
    print(f"Wrote memory: {path.relative_to(ROOT)}")

    if args.commit:
        maybe_commit(path, args.commit_message)
        print("Committed memory update.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
