from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_EXCLUDES = {
	".git",
	".venv",
	"__pycache__",
	"build",
	"dist",
	"logs",
	"find_todos.py",
}

DEFAULT_EXTENSIONS = {
	".py",
	".md",
	".toml",
	".json",
	".ps1",
	".txt",
	".yml",
	".yaml",
}

DEFAULT_PATTERN = re.compile(r"\b(TODO|FIXME|TBD|XXX|HACK)\b", re.IGNORECASE)


def _should_skip(path: Path, excluded_names: set[str]) -> bool:
	return any(part in excluded_names for part in path.parts)


def scan_repo(
	root: Path,
	pattern: re.Pattern[str],
	included_extensions: set[str],
	excluded_names: set[str],
) -> list[tuple[Path, int, str]]:
	matches: list[tuple[Path, int, str]] = []
	for file_path in root.rglob("*"):
		if not file_path.is_file():
			continue
		if _should_skip(file_path.relative_to(root), excluded_names):
			continue
		if file_path.suffix.lower() not in included_extensions:
			continue
		try:
			content = file_path.read_text(encoding="utf-8", errors="ignore")
		except OSError:
			continue
		for idx, line in enumerate(content.splitlines(), start=1):
			if pattern.search(line):
				matches.append((file_path.relative_to(root), idx, line.strip()))
	return matches


def main() -> int:
	parser = argparse.ArgumentParser(description="Scan repository source files for TODO markers.")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path(__file__).resolve().parents[1],
		help="Repository root to scan (default: project root).",
	)
	parser.add_argument(
		"--allow",
		type=str,
		default="",
		help="Pipe-separated markers to allow (example: TODO|TBD).",
	)
	args = parser.parse_args()

	root = args.root.resolve()
	if not root.exists() or not root.is_dir():
		print(f"FAIL: invalid root directory: {root}")
		return 2

	pattern = DEFAULT_PATTERN
	if args.allow.strip():
		allowed = {token.strip().upper() for token in args.allow.split("|") if token.strip()}
		blocked_terms = [term for term in ("TODO", "FIXME", "TBD", "XXX", "HACK") if term not in allowed]
		if blocked_terms:
			pattern = re.compile(r"\\b(" + "|".join(blocked_terms) + r")\\b", re.IGNORECASE)
		else:
			print("PASS: all markers allowed by policy.")
			return 0

	matches = scan_repo(
		root=root,
		pattern=pattern,
		included_extensions=DEFAULT_EXTENSIONS,
		excluded_names=DEFAULT_EXCLUDES,
	)

	if not matches:
		print("PASS: no blocked TODO markers found in project-owned files.")
		return 0

	print("FAIL: blocked TODO markers found:")
	for path, line_no, line in matches:
		print(f"{path}:{line_no}: {line}")
	return 1


if __name__ == "__main__":
	raise SystemExit(main())
