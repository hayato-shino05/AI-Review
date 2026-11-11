"""Tạo GitHub issue cảnh báo khi eval vi phạm ngưỡng chất lượng."""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional

import tomllib  # Python 3.11+

SECRETS_PATH = "/opt/devbox/opt/AI-Review/.secrets.toml"
REPO = "hayato-shino05/AI-Review"
DEFAULT_LABELS = ["quality-alert", "bug", "automated-eval"]


def _load_token() -> Optional[str]:
    """Đọc GitHub token từ .secrets.toml (user_token / app_token) hoặc env PAT."""
    env_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT")
    if env_token:
        return env_token
    try:
        with open(SECRETS_PATH, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("user_token") or data.get("app_token")
    except FileNotFoundError:
        return None
    except Exception:  # noqa: BLE001 - .secrets.toml hỏng thì bỏ qua, dùng gh CLI
        return None


def create_github_issue(
    title: str,
    body: str,
    labels: List[str] | None = None,
    dry_run: bool = False,
) -> str:
    """Tạo issue GitHub qua GitHub App token/PAT, fallback `gh issue create`.

    Trả về thông báo kết quả (issue URL hoặc lý do bỏ qua).
    """
    labels = labels or DEFAULT_LABELS
    token = _load_token()

    if dry_run:
        return (
            f"[DRY-RUN] Sẽ tạo issue '{title}' lên {REPO} "
            f"với nhãn {labels} (token={'có' if token else 'không'}); không gọi GitHub API."
        )

    if token:
        import requests  # import lười để tránh hard dependency khi chỉ dùng gh

        url = f"https://api.github.com/repos/{REPO}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        payload = {"title": title, "body": body, "labels": labels}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            issue = resp.json()
            return f"Đã tạo GitHub issue #{issue['number']}: {issue['html_url']}"
        except Exception as exc:  # noqa: BLE001
            return f"Gagal tạo issue qua API ({exc}); fallback gh CLI."

    # Không có PAT -> dùng gh CLI (cần đã auth gh auth login trước)
    label_args = []
    for label in labels:
        label_args.extend(["--label", label])
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body", body, *label_args],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return f"Đã tạo GitHub issue qua gh: {result.stdout.strip()}"
    except FileNotFoundError:
        return "Bỏ qua: không tìm thấy GitHub token và `gh` CLI."
    except subprocess.CalledProcessError as exc:  # noqa: BLE001
        return f"Gagal tạo issue qua gh: {exc.stderr.strip()}"
