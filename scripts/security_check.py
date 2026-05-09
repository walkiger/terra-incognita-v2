import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".cursor",
    ".agent-os",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
}
MAX_FILES_TO_SCAN = 8000

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)secret\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)token\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]

UNSAFE_EXEC_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
]


def iter_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        files.append(path)
        if len(files) >= MAX_FILES_TO_SCAN:
            break
    return files


def main() -> None:
    violations: list[str] = []

    for file_path in iter_files():
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = file_path.relative_to(ROOT)

        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(f"{rel}: possible hardcoded secret ({pattern.pattern})")

        for pattern in UNSAFE_EXEC_PATTERNS:
            if pattern.search(content):
                violations.append(f"{rel}: unsafe dynamic execution ({pattern.pattern})")

    if violations:
        print("Security check failed:")
        for item in violations:
            print(f"- {item}")
        sys.exit(1)

    print("Security check passed.")


if __name__ == "__main__":
    main()
