"""ctypes wrapper around libshino_native.so with a pure-Python fallback.

Never crashes: if the shared library is missing or a symbol cannot be
resolved, every native function degrades to a pure-Python implementation
with the same interface. All char* buffers returned by Rust are freed via
shino_free_str inside try/finally.
"""
from __future__ import annotations

import ctypes
import os
from typing import List, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB_PATH = os.path.join(_HERE, "libshino_native.so")

_lib = None
_native_loaded = False
_DISABLED = False


def _load_lib():
    global _lib, _native_loaded
    if _DISABLED:
        return None
    if _lib is not None:
        return _lib
    if not os.path.exists(_LIB_PATH):
        _native_loaded = False
        return None
    try:
        lib = ctypes.CDLL(_LIB_PATH)
        lib.shino_score_file.argtypes = [
            ctypes.c_char_p, ctypes.c_size_t,
            ctypes.c_char_p, ctypes.c_size_t,
        ]
        lib.shino_score_file.restype = ctypes.c_int
        lib.shino_estimate_tokens.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.shino_estimate_tokens.restype = ctypes.c_size_t
        lib.shino_repair_yaml.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.shino_repair_yaml.restype = ctypes.c_void_p
        lib.shino_extract_defs.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.shino_extract_defs.restype = ctypes.c_void_p
        lib.shino_free_str.argtypes = [ctypes.c_void_p]
        lib.shino_free_str.restype = None
        lib.shino_filter_findings.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.shino_filter_findings.restype = ctypes.c_void_p
        _lib = lib
        _native_loaded = True
    except OSError:
        _lib = None
        _native_loaded = False
    return _lib


def is_native_loaded() -> bool:
    """True if libshino_native.so is loaded; False means pure-Python fallback."""
    if _DISABLED:
        return False
    _load_lib()
    return _native_loaded


# ---------------------------------------------------------------------------
# Pure-Python fallbacks (same semantics as the Rust implementation)
# ---------------------------------------------------------------------------

_SENSITIVE = [
    "auth", "security", "crypto", "token", "jwt", "oauth", "session",
    "permission", "rbac", "secret", "password", "sql", "migration",
    "unsafe", "mutex", "atomic", "lock", "eval(", "exec(",
]
_TIER = [
    "controller", "route", "api", "handler", "middleware", "service",
    "db", "repository", "webhook", "kernel",
]
_SRC_EXT = (".py", ".ts", ".tsx", ".rs", ".cpp", ".hpp", ".go", ".java", ".cs", ".js")
_DOC_EXT = (".md", ".txt", ".lock", ".svg")


def _py_score(filename: str, patch: str) -> int:
    combined = (filename + " " + patch).lower()
    score = 0
    if any(kw in combined for kw in _SENSITIVE):
        score += 100
    if any(t in combined for t in _TIER):
        score += 60
    if filename.lower().endswith(_SRC_EXT):
        score += 30
    low = filename.lower()
    if low.startswith("test_") or "_test" in low or ".spec." in low or "/tests/" in low:
        score += 10
    if filename.lower().endswith(_DOC_EXT) or "package-lock" in low:
        score -= 50
    return score


def _py_estimate_tokens(text: str) -> int:
    count = 0
    in_word = False
    for b in text.encode("utf-8", errors="ignore"):
        is_word = 65 <= b <= 90 or 97 <= b <= 122 or 48 <= b <= 57 or b == 95
        if is_word:
            if not in_word:
                count += 1
                in_word = True
        elif b in (32, 9, 10, 13):
            in_word = False
        else:
            count += 1
            in_word = False
    return count


def _py_repair_yaml(text: str) -> str:
    out: List[str] = []
    in_fence = False
    started = False
    last_key: str | None = None
    for raw in text.splitlines():
        trimmed = raw.strip()
        if trimmed.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if trimmed in ("---", "..."):
            continue
        if not started:
            if not trimmed:
                continue
            if ":" in trimmed or trimmed.startswith("-"):
                started = True
            else:
                continue
        if not trimmed:
            out.append("")
            last_key = None
            continue
        if not trimmed.startswith(" ") and not trimmed.startswith("-") and ":" not in trimmed:
            break
        line = _py_fix_line(trimmed)
        if ":" in line:
            key, _, val = line.partition(":")
            if val.strip() == "":
                last_key = key.strip()
            else:
                last_key = None
        elif last_key is not None and line.startswith("-"):
            pass
        else:
            last_key = None
        out.append(line)
    return "\n".join(out)


def _py_fix_line(line: str) -> str:
    t = line.strip()
    if t.startswith("-") and len(t) > 1 and t[1] != " ":
        t = "- " + t[1:].lstrip()
    if ":" in t:
        key, _, val = t.partition(":")
        val = val.strip()
        if val and not val.startswith('"') and not val.startswith("'") and (": " in val or "#" in val):
            t = f'{key.strip()}: "{val}"'
    return t


def _py_extract_defs(patch: str) -> str:
    names: List[str] = []
    patterns = [
        ("export function ", "("), ("export const ", "="), ("fn ", "("),
        ("func ", "("), ("def ", " "), ("class ", " "), ("struct ", " "),
        ("enum ", " "), ("interface ", " "), ("type ", " "),
    ]
    for raw in patch.splitlines():
        t = raw.lstrip()
        name = None
        for prefix, delim in patterns:
            if t.startswith(prefix):
                rest = t[len(prefix):]
                end = len(rest)
                for i, ch in enumerate(rest):
                    if ch == delim or ch in "{<: " or ch.isspace():
                        end = i
                        break
                candidate = rest[:end].strip()
                if candidate and candidate != "(":
                    name = candidate
                break
        if name:
            names.append(name)
    if not names:
        return ""
    return "\n".join(names) + "\n"


def _py_filter_findings(
    findings: List[dict],
    diff_files: Sequence,
    suppressed: Sequence[Sequence[str]] | None = None,
    profile: str = "balanced",
) -> List[int]:
    """Pure-Python mirror of the Rust shino_filter_findings semantics.

    Keeps finding dicts that carry ``idx`` plus file/start/end/severity/header/
    content. Returns the kept idx values as a list of ints.
    """
    VAGUE = [
        "consider checking", "might want to", "could potentially",
        "maybe", "nit:", "cân nhệc kiểm tra",
    ]
    diff_set = set(diff_files)
    supp = set()
    if suppressed:
        for pair in suppressed:
            if len(pair) >= 2:
                supp.add((pair[0], pair[1]))

    def sev_rank(s: str) -> int:
        return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(s, 4)

    kept_idx: List[int] = []
    for f in findings:
        fid = int(f.get("idx", 0))
        fname = str(f.get("file", ""))
        start = int(f.get("start", 0))
        end = int(f.get("end", 0))
        sev = str(f.get("severity", ""))
        header = str(f.get("header", ""))
        content = str(f.get("content", ""))

        # 1. Hallucination / diff-line grounding filter.
        file_hunks = [
            (h[1], h[2]) for h in diff_files
            if isinstance(h, (list, tuple)) and len(h) >= 3 and h[0] == fname
        ]
        in_hunks = bool(file_hunks)
        near_hunk = any(
            not (end < s - 20 or start > e + 20) for s, e in file_hunks
        )
        is_security = sev == "P0" or "security" in (header + " " + content).lower()
        if not in_hunks or (not near_hunk and not is_security):
            continue

        # 2. Suppression filter.
        if (fname, header) in supp or (fname, content) in supp:
            continue
        if any(sf == fname and (kw in header or kw in content) for sf, kw in supp):
            continue

        # 3. Noise / profile filter.
        if profile != "assertive":
            text = (header + " " + content).lower()
            vague = any(p in text for p in VAGUE)
            short = len(header) + len(content) < 40
            if profile == "chill" and vague and short and sev in ("P2", "P3"):
                continue
            if profile == "balanced" and vague and short and sev == "P3":
                continue

        kept_idx.append(fid)

    # 4. Overlap deduplication filter.
    keep_set = set(kept_idx)
    kept_findings = [f for f in findings if int(f.get("idx", 0)) in keep_set]
    for a in range(len(kept_findings)):
        fa = kept_findings[a]
        ia = int(fa.get("idx", 0))
        if ia not in keep_set:
            continue
        for b in range(a + 1, len(kept_findings)):
            fb = kept_findings[b]
            ib = int(fb.get("idx", 0))
            if ib not in keep_set:
                continue
            if fa.get("file") != fb.get("file"):
                continue
            overlap = int(fa.get("start", 0)) <= int(fb.get("end", 0)) + 2 and \
                int(fb.get("start", 0)) <= int(fa.get("end", 0)) + 2
            same_header = str(fa.get("header", "")) == str(fb.get("header", ""))
            if overlap or same_header:
                ra = sev_rank(str(fa.get("severity", "")))
                rb = sev_rank(str(fb.get("severity", "")))
                if ra < rb:
                    keep_set.discard(ib)
                elif rb < ra:
                    keep_set.discard(ia)
                else:
                    keep_set.discard(ib)

    return sorted(i for i in kept_idx if i in keep_set)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _b(text: str) -> bytes:
    return text.encode("utf-8", errors="ignore")


def score_files_priority(files: Sequence[Sequence[str]]) -> List[int]:
    """Score a list of (filename, patch) pairs. Returns risk scores."""
    lib = _load_lib()
    if lib is None:
        return [_py_score(f, p) for f, p in files]
    scores: List[int] = []
    for filename, patch in files:
        fb = _b(filename)
        pb = _b(patch)
        score = lib.shino_score_file(fb, len(fb), pb, len(pb))
        scores.append(int(score))
    return scores


def estimate_tokens_fast(text: str) -> int:
    lib = _load_lib()
    if lib is None:
        return _py_estimate_tokens(text)
    tb = _b(text)
    return int(lib.shino_estimate_tokens(tb, len(tb)))


def repair_yaml_native(text: str) -> str:
    lib = _load_lib()
    if lib is None:
        return _py_repair_yaml(text)
    tb = _b(text)
    ptr = lib.shino_repair_yaml(tb, len(tb))
    try:
        if not ptr:
            return ""
        return ctypes.string_at(ptr).decode("utf-8", errors="replace")
    finally:
        lib.shino_free_str(ptr)


def extract_defs_fast(patch: str) -> str:
    lib = _load_lib()
    if lib is None:
        return _py_extract_defs(patch)
    tb = _b(patch)
    ptr = lib.shino_extract_defs(tb, len(tb))
    try:
        if not ptr:
            return ""
        return ctypes.string_at(ptr).decode("utf-8", errors="replace")
    finally:
        lib.shino_free_str(ptr)


def filter_findings_fast(
    findings: List[dict],
    diff_files: Sequence,
    suppressed: Sequence[Sequence[str]] | None = None,
    profile: str = "balanced",
) -> List[int]:
    """Filter findings via native Rust libshino_native.so.

    ``findings`` is a list of dicts with keys: idx, file, start, end,
    severity, header, content. ``diff_files`` provides the real changed
    line ranges (as "file\\x1fstart\\x1fend" strings or (file,start,end)
    tuples) used for hallucination grounding. ``suppressed`` is a list of
    (file, keyword) pairs the developer already rejected. ``profile`` is one
    of chill / balanced / assertive. Returns the kept finding idx values.

    Falls back to a pure-Python implementation when the native library is
    unavailable. The returned char* buffer from Rust is freed via
    shino_free_str inside try/finally.
    """
    lib = _load_lib()
    if lib is None:
        return _py_filter_findings(findings, diff_files, suppressed, profile)

    US = "\u001f"
    lines: List[str] = [f"P{US}{profile}"]

    # diff hunks: accept "file\\x1fstart\\x1fend" strings or (file,start,end) tuples
    for h in diff_files:
        if isinstance(h, (list, tuple)) and len(h) >= 3:
            lines.append(f"H{US}{h[0]}{US}{int(h[1])}{US}{int(h[2])}")
        elif isinstance(h, str):
            parts = h.split(US)
            if len(parts) >= 3:
                lines.append(f"H{US}{h}")

    for pair in suppressed or []:
        if len(pair) >= 2:
            lines.append(f"S{US}{pair[0]}{US}{pair[1]}")

    for f in findings:
        lines.append(
            f"F{US}{int(f.get('idx', 0))}{US}{f.get('file', '')}"
            f"{US}{int(f.get('start', 0))}{US}{int(f.get('end', 0))}"
            f"{US}{f.get('severity', '')}{US}{f.get('header', '')}{US}{f.get('content', '')}"
        )

    payload = "\n".join(lines).encode("utf-8", errors="ignore")
    ptr = lib.shino_filter_findings(payload, len(payload))
    try:
        if not ptr:
            return []
        out = ctypes.string_at(ptr).decode("utf-8", errors="replace").strip()
        if not out:
            return []
        return [int(x) for x in out.split(",") if x.strip()]
    finally:
        lib.shino_free_str(ptr)


def risk_priority_sort(diff_files: Sequence) -> List:
    """Sort files so high-risk ones come first, using Rust native shino_score_file.

    Reads ``filename`` and ``patch`` from each item via getattr. Returns a new
    list sorted by descending risk score. Falls back to pure-Python scoring when
    the native library is unavailable.
    """
    lib = _load_lib()
    items = list(diff_files)

    def _rank(f):
        name = getattr(f, "filename", "") or ""
        patch = getattr(f, "patch", "") or ""
        fb = _b(name)
        pb = _b(patch)
        if lib is not None:
            score = int(lib.shino_score_file(fb, len(fb), pb, len(pb)))
        else:
            score = _py_score(name, patch)
        return score, str(name)


# ---------------------------------------------------------------------------
# Smart Router: per-model circuit breaker (Rust-native, Python fallback)
# ---------------------------------------------------------------------------

_PY_BREAKERS: dict = {}


def _coerce_circuit_args(model, kind):
    if isinstance(model, bytes):
        model_b = model
    else:
        model_b = str(model).encode("utf-8")
    if kind is None:
        kind_b = b"ok"
    elif isinstance(kind, bytes):
        kind_b = kind
    else:
        kind_b = str(kind).encode("utf-8")
    return model_b, kind_b


def circuit_check(model) -> bool:
    """True if the model may be called now; False while its breaker is open."""
    lib = _load_lib()
    model_b, _ = _coerce_circuit_args(model, None)
    if lib is not None and hasattr(lib, "shino_circuit_check"):
        lib.shino_circuit_check.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        lib.shino_circuit_check.restype = ctypes.c_int
        return bool(lib.shino_circuit_check(model_b, len(model_b)))
    import time
    entry = _PY_BREAKERS.get(str(model))
    if entry is None:
        return True
    return (time.time() - entry[0]) >= entry[1]


def circuit_report(model, kind) -> bool:
    """Report a model outcome; returns True if its circuit is now open."""
    lib = _load_lib()
    model_b, kind_b = _coerce_circuit_args(model, kind)
    if lib is not None and hasattr(lib, "shino_circuit_report"):
        lib.shino_circuit_report.argtypes = [
            ctypes.c_char_p, ctypes.c_size_t,
            ctypes.c_char_p, ctypes.c_size_t,
        ]
        lib.shino_circuit_report.restype = ctypes.c_int
        return bool(lib.shino_circuit_report(model_b, len(model_b), kind_b, len(kind_b)))
    import time
    cooldowns = {"rate_limit": 180, "auth": 600, "timeout": 90,
                 "empty": 60, "server": 120}
    if kind is None or str(kind) == "ok":
        _PY_BREAKERS.pop(str(model), None)
        return False
    cooldown = cooldowns.get(str(kind), 30)
    entry = _PY_BREAKERS.get(str(model))
    if entry is not None and entry[1] == cooldown:
        opened_at = entry[0]
    else:
        opened_at = time.time()
    _PY_BREAKERS[str(model)] = (opened_at, cooldown)
    return True
