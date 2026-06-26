#!/usr/bin/env python3
"""
Glossary-based translation consistency checker for ko.javascript.info.

Compares 한국어(영어) 병기 patterns in the input file against the
ko.javascript.info Google Sheets glossary (cached locally under glossary/).
Refreshes cache on every run via sha256 comparison; falls back to cache on
network failure.

Usage: python3 check_glossary.py <file_path>
Output (stdout): JSON with violations, passed list, and cache metadata.
"""

import csv
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from _text_utils import strip_non_korean_content


SPREADSHEET_ID = "1fYaEI8vz26N3R2VaxrlNnk9fMQ8zIy4RpvjRp4jZd0Q"
SHEETS = {
    "sheet1": "1401860741",
    "sheet2": "843106813",
}
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    + SPREADSHEET_ID
    + "/gviz/tq?tqx=out:csv&gid={gid}"
)
FETCH_TIMEOUT = 5  # seconds
CACHE_TTL_SECONDS = 24 * 60 * 60  # freshness 윈도: 이 시간 내 확인했으면 페치 생략

GLOSSARY_DIR = Path(__file__).resolve().parent.parent / "glossary"

KST = datetime.timezone(datetime.timedelta(hours=9))


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """임시 파일에 쓴 뒤 os.replace로 교체 — 동시 실행 시 부분/손상 파일 방지."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)

# 한국어(영어) 병기 패턴 — 영어는 알파벳으로 시작, 콤마/공백/언더스코어/하이픈 허용
PAIR_RE = re.compile(
    r"([가-힣][가-힣\s·]{0,20})\(([A-Za-z][A-Za-z0-9 ,_\-]{0,60})\)"
)

# 단독 표기 뒤에 붙을 수 있는 조사 (긴 것부터 — 정규식 좌→우 우선 매칭).
# 조사 외 한글이 이어지면(예: '큐레이션') 단독 등장으로 보지 않는다.
JOSA = (
    "으로|에서|에게|이나|이란|라도|처럼|보다|부터|까지|마다|조차|마저|"
    "은|는|이|가|을|를|에|의|도|만|과|와|로|나|란"
)


def resolve_korean(korean_text: str, candidates: list[str]) -> tuple[str, bool]:
    """본문의 한국어 부분에서 실제 사용된 용어를 추출하고 표준 일치 여부 반환.

    정규식이 앞 단어까지 욕심부려 잡는 경우에 대비해, 후보 표기가 suffix로
    들어있으면 통과로 본다.
    """
    korean_text = korean_text.strip()
    for cand in sorted(candidates, key=len, reverse=True):
        if korean_text == cand:
            return cand, True
        if korean_text.endswith(cand):
            cut = len(korean_text) - len(cand)
            if cut > 0 and korean_text[cut - 1].isspace():
                return cand, True
    tokens = korean_text.split()
    return (tokens[-1] if tokens else korean_text), False


def _is_fresh(last_checked: str | None, now: datetime.datetime) -> bool:
    """last_checked가 TTL 윈도 안이면 True. 없거나 파싱 실패 시 stale로 간주."""
    if not last_checked:
        return False
    try:
        checked = datetime.datetime.fromisoformat(last_checked)
    except ValueError:
        return False
    return (now - checked).total_seconds() < CACHE_TTL_SECONDS


def refresh_cache() -> dict:
    """Fetch sheets, update files if hash changed. Returns cache status dict.

    TTL(freshness) 윈도: 마지막 확인(last_checked) 후 CACHE_TTL_SECONDS 이내면
    네트워크 페치와 파일 쓰기를 모두 생략한다.
    """
    meta_path = GLOSSARY_DIR / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {
            "spreadsheet_id": SPREADSHEET_ID,
            "last_fetched": None,
            "last_checked": None,
            "sheets": {name: {"gid": gid, "sha256": ""} for name, gid in SHEETS.items()},
        }

    now = datetime.datetime.now(KST)
    if _is_fresh(meta.get("last_checked"), now):
        return {
            "last_fetched": meta.get("last_fetched"),
            "refreshed": False,
            "network_warning": None,
        }

    refreshed = False
    fetch_failed = False
    warning = None

    for name, gid in SHEETS.items():
        url = CSV_URL.format(gid=gid)
        try:
            with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as resp:
                body = resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            warning = f"network fetch failed for {name}: {exc}"
            fetch_failed = True
            continue

        new_hash = hashlib.sha256(body).hexdigest()
        old_hash = meta["sheets"].get(name, {}).get("sha256", "")
        if new_hash != old_hash:
            _atomic_write_bytes(GLOSSARY_DIR / f"{name}.csv", body)
            meta["sheets"][name] = {"gid": gid, "sha256": new_hash}
            refreshed = True

    now_iso = now.isoformat(timespec="seconds")
    if refreshed:
        meta["last_fetched"] = now_iso
    if not fetch_failed:
        # 모든 시트를 성공적으로 확인했을 때만 윈도 전진(실패 시 다음 실행에서 재시도)
        meta["last_checked"] = now_iso
    if refreshed or not fetch_failed:
        _atomic_write_bytes(
            meta_path,
            json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    return {
        "last_fetched": meta.get("last_fetched"),
        "refreshed": refreshed,
        "network_warning": warning,
    }


def load_glossary() -> dict[str, list[str]]:
    """Read both CSVs, return {english_lower: [korean_candidate, ...]}."""
    glossary: dict[str, list[str]] = {}
    for name in SHEETS:
        path = GLOSSARY_DIR / f"{name}.csv"
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if len(row) < 2:
                    continue
                english = row[0].strip()
                korean = row[1].strip()
                if not english or not korean:
                    continue
                if not re.match(r"^[A-Za-z]", english):
                    # Skip symbol-only entries from sheet2 (병기 패턴 키와 매칭 불가)
                    continue
                key = english.lower()
                # 슬래시/콤마 분리 표기는 모두 정답 후보 (예: "문, 구문", "세미콜론/쌍반점")
                parts = re.split(r"\s*[/,]\s*", korean)
                candidates = [c for c in parts if c]
                glossary[key] = candidates
    return glossary


def check_file(file_path: str) -> dict:
    cache_status = refresh_cache()
    glossary = load_glossary()

    raw = Path(file_path).read_text(encoding="utf-8")
    cleaned = strip_non_korean_content(raw)
    lines = cleaned.splitlines()

    # 모든 표준 번역어 집합 — 비표준 표기가 그 자체로 다른 용어의 표준어이면
    # (예: '객체'는 object의 표준어) 동음이의 오탐을 막기 위해 일관성 학습에서 제외한다.
    standard_terms = {c for cands in glossary.values() for c in cands}

    violations = []
    passed = []
    learned: dict[str, str] = {}  # 비표준 한국어 표기 -> 표준 대표어
    pair_spans: dict[int, list[tuple[int, int]]] = {}  # line_num -> PAIR_RE 매치 위치

    # 1차 패스: 병기 검사 + 비표준 표기 학습
    for line_num, line in enumerate(lines, start=1):
        for match in PAIR_RE.finditer(line):
            pair_spans.setdefault(line_num, []).append(match.span())
            korean_raw = match.group(1).strip()
            english_raw = match.group(2).strip()
            english_key = english_raw.split(",")[0].strip().lower()
            candidates = glossary.get(english_key)
            if not candidates:
                continue
            korean_used, is_match = resolve_korean(korean_raw, candidates)
            if is_match:
                passed.append(f"{korean_used}({english_raw}) — 표준 번역어 일치")
            else:
                violations.append(
                    {
                        "line": line_num,
                        "rule_id": "GLOSSARY-mismatch",
                        "problem": f"{korean_used}({english_raw})",
                        "suggestion": f"{candidates[0]}({english_raw})",
                        "severity": "recommended",
                    }
                )
                if korean_used not in standard_terms:
                    # 동음이의(다른 용어의 표준어)는 학습 제외 — 단독 등장 오탐 방지
                    learned[korean_used] = candidates[0]

    # 2차 패스: 학습된 비표준 표기의 '단독' 등장 검출
    for term, standard in learned.items():
        term_re = re.compile(
            r"(?<![가-힣])" + re.escape(term) + r"(?:" + JOSA + r")?(?![가-힣])"
        )
        for line_num, line in enumerate(lines, start=1):
            spans = pair_spans.get(line_num, [])
            for m in term_re.finditer(line):
                if any(s <= m.start() < e for (s, e) in spans):
                    continue  # 병기 자체는 mismatch로 이미 처리됨
                violations.append(
                    {
                        "line": line_num,
                        "rule_id": "GLOSSARY-inconsistent",
                        "problem": term,
                        "suggestion": standard,
                        "severity": "recommended",
                    }
                )

    violations.sort(key=lambda v: v["line"])  # 보고서 가독성

    return {
        "source": "glossary",
        "violations": violations,
        "passed": passed,
        "cache": cache_status,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file_path>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    if not os.path.exists(target):
        print(json.dumps({"error": f"File not found: {target}"}))
        sys.exit(1)

    result = check_file(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
