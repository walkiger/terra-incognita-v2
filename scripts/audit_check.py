import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".cursor",
    ".agent-os",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}
MAX_FILES_PER_LAYER = 2000


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def find_code_files(base: pathlib.Path) -> list[pathlib.Path]:
    if not base.exists():
        return []
    exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
    files: list[pathlib.Path] = []
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        files.append(p)
        if len(files) >= MAX_FILES_PER_LAYER:
            break
    return files


def main() -> None:
    violations: list[str] = []

    backend_dir = ROOT / "archive" / "legacy-terra" / "backend"
    frontend_dir = ROOT / "archive" / "legacy-terra" / "frontend"
    research_dir = ROOT / "research"

    backend_files = find_code_files(backend_dir)
    frontend_files = find_code_files(frontend_dir)

    # Rule: no UI logic in backend
    for file_path in backend_files:
        content = read(file_path)
        if re.search(r"\bReact\b|three\.js|\buseState\b|\buseEffect\b", content):
            violations.append(f"{file_path.relative_to(ROOT)}: potential UI logic in backend")

    # Rule: no backend internals directly in frontend
    for file_path in frontend_files:
        content = read(file_path)
        if re.search(r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b", content):
            violations.append(f"{file_path.relative_to(ROOT)}: potential business/data logic in UI")

    # Rule: research outputs should be structured
    if research_dir.exists():
        structured = list(research_dir.rglob("*.json")) + list(research_dir.rglob("*.yaml"))
        if not structured:
            violations.append("research/: no structured output files (.json/.yaml) detected")

    if violations:
        print("Audit check failed:")
        for item in violations:
            print(f"- {item}")
        sys.exit(1)

    print("Audit check passed.")


if __name__ == "__main__":
    main()
