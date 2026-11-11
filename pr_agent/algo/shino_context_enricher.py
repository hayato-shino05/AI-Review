"""Shino PR context enrichment.

Tong hop cac co che tot nhat tu CodeRabbit, Graphite Diamond va Greptile:
quy tắc theo duong dap, ng canh lien ket, bo loc dev boc bo va diem tin chao duoc ETALON.
Tat ca cac thao tac ngoai (git provider) duoc bao bung bo try/except de khong lam
gián đoạn luot review khi co loi.
"""

from __future__ import annotations

import fnmatch
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

try:  # PyYAML la bo dau tu day trong moc truong du an.
    import yaml
except Exception:  # pragma: no cover - duoc phuc vu bo o tai sao neu thieu pyyaml.
    yaml = None

_SUPPRESSION_PHRASES = (
    "false positive",
    "intentional",
    "by design",
    "wontfix",
    "ignore",
    "bỏ qua",
    "cố ý",
)

_ISSUE_LINK_RE = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+#(\d+)", re.IGNORECASE
)

_CONFIG_FILES = (
    ".shino/rules.yaml",
    ".coderabbit.yaml",
    ".greptile/rules.md",
)


def _get_file_text(git_provider: Any, path: str) -> str | None:
    """Doc noi dung file khoi repo qua git_provider. Tra ve None neu khong doc duoc."""
    accessors = []
    repo_obj = getattr(git_provider, "repo_obj", None) or getattr(git_provider, "repo", None)
    if repo_obj is not None:
        accessors.append(lambda r=repo_obj: r.get_contents(path))
    if git_provider is not repo_obj:
        accessors.append(lambda g=git_provider: g.get_contents(path))  # type: ignore[arg-type]
        accessors.append(lambda g=git_provider: g.get_file_contents(path))  # type: ignore[arg-type]
    if repo_obj is not None and repo_obj is not git_provider:
        accessors.append(lambda r=repo_obj: r.get_file_contents(path))  # type: ignore[arg-type]

    for accessor in accessors:
        try:
            node = accessor()
        except Exception:  # keep trying other accessors
            continue
        try:
            raw = getattr(node, "decoded", None)
            if raw is None:
                raw = node
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace")
            return str(raw)
        except Exception:  # keep trying
            continue
    return None


def _iter_rules(raw: Any) -> list[dict[str, str]]:
    """Chuyen du lieu quy tac thuan gom ve list {path, instructions}."""
    rules: list[dict[str, str]] = []
    if raw is None:
        return rules
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = (
            raw.get("path_instructions")
            or raw.get("rules")
            or raw.get("path_instruction")
            or []
        )
        if not isinstance(items, list):
            items = [items] if items else []
    else:
        return rules
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or item.get("glob") or item.get("pattern") or ""
        instr = item.get("instructions") or item.get("instruction") or ""
        if path:
            rules.append({"path": str(path), "instructions": str(instr)})
    return rules


def _parse_markdown_rules(text: str) -> list[dict[str, str]]:
    """Giai ma nhat markdown chua cac cap path / instruction (trong gioi han it canh)."""
    rules: list[dict[str, str]] = []
    current_path: str | None = None
    current_instr: list[str] = []

    def flush() -> None:
        nonlocal current_path, current_instr
        if current_path:
            rules.append({"path": current_path, "instructions": " ".join(current_instr).strip()})
        current_path = None
        current_instr = []

    path_re = re.compile(r"`(?P<path>[^`]+)`|\*\*(?P<path2>[^\n*]+?)\*\*\s*$|(?m)^\s*path\s*:\s*(?P<path3>.+)$")
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = path_re.search(line)
        if m:
            path = (m.group("path") or m.group("path2") or m.group("path3") or "").strip()
            if path:
                flush()
                current_path = path
                continue
        if current_path is not None and line.strip() and not line.lstrip().startswith("#"):
            current_instr.append(line.strip())
    flush()
    return rules


def collect_path_based_rules(
    git_provider: Any, changed_filenames: list[str], max_chars: int = 1500
) -> str:
    """Lay cac quy tắc duong dan khop voi cac file duoc doi trong PR, cat theo max_chars."""
    changed_filenames = changed_filenames or []
    collected: list[str] = []

    for config_path in _CONFIG_FILES:
        try:
            text = _get_file_text(git_provider, config_path)
        except Exception:
            text = None
        if not text:
            continue

        rules: list[dict[str, str]] = []
        if config_path.endswith(".md"):
            rules = _parse_markdown_rules(text)
        elif yaml is not None:
            try:
                parsed = yaml.safe_load(text)
            except Exception:
                parsed = None
            rules = _iter_rules(parsed)

        for rule in rules:
            try:
                matched = any(fnmatch.fnmatchcase(name, rule["path"]) for name in changed_filenames)
            except Exception:
                matched = False
            if matched and rule["instructions"]:
                collected.append(f"[{config_path}] {rule['path']}: {rule['instructions']}")

    if not collected:
        return ""

    out = "\n".join(collected)
    if len(out) > max_chars:
        out = out[: max_chars - 3].rstrip() + "..."
    return out


def _extract_acceptance_criteria(body: str) -> str:
    if not body:
        return ""
    marker = re.compile(r"acceptance criteria", re.IGNORECASE)
    match = marker.search(body)
    if match:
        segment = body[match.end(): match.end() + 300]
        lines = [ln.strip() for ln in segment.splitlines() if ln.strip()][:4]
        return "AC: " + " | ".join(lines)
    return body.strip().replace("\n", " ")[:220]


def _fetch_one_issue(repo_obj: Any, num: int) -> str:
    try:
        issue = repo_obj.get_issue(num)
    except Exception:
        return f"Issue #{num}: (khong lay duoc thong tin)"
    title = getattr(issue, "title", "") or ""
    ac = _extract_acceptance_criteria(getattr(issue, "body", "") or "")
    parts = [p for p in [title, ac] if p]
    return f"Issue #{num}: " + " - ".join(parts) if parts else f"Issue #{num}: (trong)"


def fetch_linked_issues_context(
    git_provider: Any, pr_title: str, pr_body: str, max_chars: int = 1200
) -> str:
    """Lay tieu de + Acceptance Criteria toi da 3 issue duoc lien ket trong PR."""
    repo_obj = getattr(git_provider, "repo_obj", None) or getattr(git_provider, "repo", None)
    if repo_obj is None:
        return ""

    text = " ".join([pr_title or "", pr_body or ""])
    ids: list[int] = []
    for m in _ISSUE_LINK_RE.finditer(text):
        try:
            num = int(m.group(1))
        except ValueError:
            continue
        if num not in ids:
            ids.append(num)
        if len(ids) >= 3:
            break

    if not ids:
        return ""

    results: list[str] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        future_to_num = {pool.submit(_fetch_one_issue, repo_obj, num): num for num in ids}
        for future in as_completed(future_to_num):
            try:
                results.append(future.result())
            except Exception:
                results.append(f"Issue #{future_to_num[future]}: (loi lay thong tin)")

    def _issue_num(r: str) -> int:
        m = re.search(r"#(\d+)", r)
        return int(m.group(1)) if m else 9999

    results.sort(key=_issue_num)
    out = " | ".join(results)
    if len(out) > max_chars:
        out = out[: max_chars - 3].rstrip() + "..."
    return out


def extract_developer_suppressions(git_provider: Any) -> list[tuple[str, str]]:
    """Trich xuat (path, tu khoa) tu cac phan hoi bac bo cua developer tren PR."""
    pr = getattr(git_provider, "pr", None)
    if pr is None:
        return []

    comments: list[Any] = []
    for attr in ("get_review_comments", "get_issue_comments"):
        try:
            comments.extend(getattr(pr, attr)() or [])
        except Exception:
            continue

    suppressions: list[tuple[str, str]] = []
    for comment in comments:
        body = getattr(comment, "body", "") or ""
        body_lower = body.lower()
        matched_phrase = next((p for p in _SUPPRESSION_PHRASES if p in body_lower), None)
        if not matched_phrase:
            continue
        path = getattr(comment, "path", None) or getattr(comment, "file", None) or ""
        header = (body.splitlines()[0] if body.splitlines() else body)[:80]
        suppressions.append((str(path), header))
    return suppressions


def _issue_priority(issue: Any) -> str:
    if isinstance(issue, dict):
        for key in ("priority", "severity", "level"):
            val = issue.get(key)
            if val is not None:
                return str(val)
        return ""
    for attr in ("priority", "severity", "level"):
        val = getattr(issue, attr, None)
        if val is not None:
            return str(val)
    return ""


def calculate_calibrated_confidence_score(
    issues: list[Any],
    relevant_tests: str = "Yes",
    remaining_files_count: int = 0,
    security_concerns: str = "No",
) -> int:
    """Tinh diem tin chao dinh luong thang 1..5 (Greptile + Cubic)."""
    score = 5.0

    p0_or_security = False
    for issue in issues or []:
        prio = _issue_priority(issue).strip().upper()
        if prio.startswith("P0"):
            p0_or_security = True
            score -= 2.5
        elif prio.startswith("P1"):
            score -= 1.0
        elif prio.startswith("P2"):
            score -= 0.5
        elif prio.startswith("P3"):
            score -= 0.15

    if str(security_concerns).strip().lower() not in ("no", "none", ""):
        p0_or_security = True

    if str(relevant_tests).strip().lower() == "no":
        score -= 0.5

    cap = 5.0
    if p0_or_security:
        cap = min(cap, 2.0)
    if remaining_files_count > 0:
        cap = min(cap, 4.0)

    score = min(score, cap)
    score = max(score, 1.0)
    return int(round(score))


def _file_stats(diff_file: Any) -> dict[str, Any]:
    if isinstance(diff_file, dict):
        return {
            "filename": diff_file.get("filename") or diff_file.get("path") or "",
            "additions": int(diff_file.get("additions") or 0),
            "deletions": int(diff_file.get("deletions") or 0),
            "status": diff_file.get("status") or diff_file.get("edit_type") or "",
        }
    return {
        "filename": getattr(diff_file, "filename", None) or getattr(diff_file, "path", "") or "",
        "additions": int(getattr(diff_file, "additions", 0) or 0),
        "deletions": int(getattr(diff_file, "deletions", 0) or 0),
        "status": getattr(diff_file, "status", None) or getattr(diff_file, "edit_type", "") or "",
    }


def build_real_diff_summary(
    diff_files: list[Any], issues: list[Any], max_bullets: int = 4
) -> str:
    """Sinh phan tich diff thuc te (khong chua text mau co san)."""
    files = [_file_stats(f) for f in (diff_files or [])]
    total_add = sum(f["additions"] for f in files)
    total_del = sum(f["deletions"] for f in files)

    ext_counts: dict[str, int] = {}
    for f in files:
        name = f["filename"]
        ext = name.rsplit(".", 1)[-1] if "." in name else "no-ext"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    issue_count = len(issues or [])
    top_files = sorted(files, key=lambda f: f["additions"] + f["deletions"], reverse=True)[:3]

    bullets: list[str] = []
    if files:
        ext_summary = ", ".join(f"{k}:{v}" for k, v in sorted(ext_counts.items()))
        bullets.append(f"Tong {len(files)} file duoc doi ({total_add} them / {total_del} xoa), loai file: {ext_summary}.")
        if top_files:
            named = "; ".join(f"{f['filename']}(+{f['additions']}/-{f['deletions']})" for f in top_files)
            bullets.append(f"File co thay doi nhieu nhat: {named}.")
    else:
        bullets.append("Khong co file nao duoc thong qua diff.")

    if issue_count:
        bullets.append(f"Co {issue_count} issue lien ket can kiem tra tuong phap.");
    else:
        bullets.append("Khong co issue nao duoc lien ket.")

    return "\n".join(f"- {b}" for b in bullets[:max_bullets])
