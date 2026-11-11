"""ctypes wrapper around libshino_native.so with a pure-Python fallback.

Never crashes: if the shared library is missing or a symbol cannot be
resolved, every native function degrades to a pure-Python implementation
with the same interface. All char* buffers returned by Rust are freed via
shino_free_str inside try/finally.
"""
from __future__ import annotations

import ctypes
import os
import re
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

    ranked = [( _rank(f), f) for f in items]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [f for _, f in ranked]
