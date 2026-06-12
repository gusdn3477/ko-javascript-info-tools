#!/usr/bin/env python3
"""
Korean spell checker for Markdown/text files using hanspell.

The script masks Markdown/code regions before checking, runs `npx hanspell -d`,
and emits JSON that Codex can turn into a report.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def mask_text(text: str) -> str:
    """Replace non-newline characters with spaces while preserving line numbers."""
    return re.sub(r"[^\n]", " ", text)


def mask_pattern(content: str, pattern: str, flags: int = 0) -> str:
    return re.sub(pattern, lambda match: mask_text(match.group(0)), content, flags=flags)


def keep_link_text(match: re.Match[str]) -> str:
    whole = match.group(0)
    label = match.group(1)
    label_start = match.start(1) - match.start(0)
    label_end = label_start + len(label)
    return " " * label_start + label + " " * (len(whole) - label_end)


def mask_heading_marker(match: re.Match[str]) -> str:
    return " " * len(match.group(1))


def prepare_content(content: str) -> str:
    """Mask content that should not be spell-checked while preserving offsets."""
    cleaned = content.replace("“", '"').replace("”", '"')

    cleaned = mask_pattern(cleaned, r"\A---[\s\S]*?\n---[^\n]*(?:\n|$)")
    cleaned = mask_pattern(cleaned, r"```[\s\S]*?```")
    cleaned = mask_pattern(cleaned, r"~~~[\s\S]*?~~~")
    cleaned = mask_pattern(cleaned, r"<!--[\s\S]*?-->")
    cleaned = mask_pattern(cleaned, r"!\[[^\]]*\]\([^)]+\)")
    cleaned = mask_pattern(cleaned, r"`[^`\n]+`")
    cleaned = mask_pattern(cleaned, r"https?://\S+")
    cleaned = mask_pattern(cleaned, r"<[^>\n]+>")
    cleaned = re.sub(r"\[([^\]\n]+)\]\([^)]+\)", keep_link_text, cleaned)
    cleaned = re.sub(r"^(#{1,6}\s+)", mask_heading_marker, cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^(\s{0,3}>+\s*)", mask_heading_marker, cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^(\s*[-*+]\s+)", mask_heading_marker, cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("*", " ")
    return cleaned


def parse_hanspell_output(output: str) -> list[dict[str, str]]:
    """Parse hanspell stderr entries shaped like `original -> suggestion`."""
    violations: list[dict[str, str]] = []
    lines = [
        line
        for line in output.strip().splitlines()
        if not line.strip().startswith(("npm notice", "npm WARN"))
    ]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if " -> " not in line:
            i += 1
            continue

        original, suggestion = line.split(" -> ", 1)
        explanation_parts: list[str] = []
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if " -> " in next_line:
                break
            if next_line:
                explanation_parts.append(next_line)
            i += 1

        violations.append(
            {
                "original": original.strip(),
                "suggestion": suggestion.strip(),
                "explanation": " ".join(explanation_parts).strip(),
            }
        )

    return violations


def find_line(cleaned: str, original: str, start_at: int) -> tuple[int | None, int]:
    if not original:
        return None, start_at

    index = cleaned.find(original, start_at)
    if index == -1:
        index = cleaned.find(original)
    if index == -1:
        return None, start_at

    line = cleaned.count("\n", 0, index) + 1
    return line, index + len(original)


def run_hanspell(cleaned: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npx", "--yes", "hanspell", "-d"],
        input=cleaned,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )


def check_spelling(path: Path, timeout: int, include_corrected: bool) -> dict:
    if not path.is_file():
        return {"error": f"File not found: {path}"}

    content = path.read_text(encoding="utf-8")
    cleaned = prepare_content(content)

    try:
        result = run_hanspell(cleaned, timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"hanspell timed out after {timeout} seconds"}
    except FileNotFoundError:
        return {"error": "npx not found. Install Node.js first."}

    parsed = parse_hanspell_output(result.stderr)
    if result.returncode != 0 and not parsed:
        stderr = result.stderr.strip()
        return {"error": stderr or f"hanspell failed with exit code {result.returncode}"}

    search_pos = 0
    violations = []
    for item in parsed:
        line, search_pos = find_line(cleaned, item["original"], search_pos)
        violations.append(
            {
                "line": line,
                "rule_id": "SPELL",
                "source": "spell",
                "problem": item["original"],
                "suggestion": item["suggestion"],
                "explanation": item["explanation"],
                "severity": "required",
            }
        )

    payload = {
        "source": "spell",
        "file": str(path.resolve()),
        "total": len(violations),
        "violations": violations,
        "passed": ["맞춤법 오류 없음"] if not violations else [],
    }
    if include_corrected:
        payload["corrected_text"] = result.stdout.strip()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Korean spelling with hanspell.")
    parser.add_argument("file", help="Markdown or text file to check")
    parser.add_argument("--timeout", type=int, default=120, help="hanspell timeout in seconds")
    parser.add_argument(
        "--include-corrected",
        action="store_true",
        help="Include hanspell corrected text in JSON output",
    )
    args = parser.parse_args()

    payload = check_spelling(Path(args.file), args.timeout, args.include_corrected)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if "error" in payload else 0


if __name__ == "__main__":
    raise SystemExit(main())
