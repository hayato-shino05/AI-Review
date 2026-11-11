"""LLM judge for AI-Review eval results via 9Router."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict

import requests

ROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"
ROUTER_KEY = "sk-dc042321c94f2e3e-3nvxhz-8f0ac825"
PRIMARY_MODEL = "newapi/nvidia/nemotron-3.5-super-vl-120b-a12b"
FALLBACK_MODEL = "openai/openrouter/nvidia/nemotron-3.5-super-vl:free"
TIMEOUT_SECONDS = 45

_JUDGE_PROMPT = """Bạn là một thẩm phán đánh giá kết quả review code tự động so với ground truth diff.

Nhiệm vụ: cho điểm theo 4 tiêu chí (thang 0-5):
- accuracy: độ chính xác so với ground truth
- actionability: tính khả thi hành động của findings
- hallucination_penalty: 5 = không bịa vấn đề không tồn tại
- overall: điểm tổng-quát (0-5)

verdict: "PASS" nếu overall >= 3.8 VÀ không bỏ sót lỗi P1, ngược lại "FAIL".
reason: tóm tắt ngắn gọn.

Trả về JSON duy nhất, không kèm markdown code fence:
{{"accuracy": <int>, "actionability": <int>, "hallucination_penalty": <int>, "overall": <float>, "verdict": "PASS"|"FAIL", "reason": "<str>"}}

Ground truth diff: {ground_truth}
Bot review output: {review_output}
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Bóc tách JSON an toàn từ văn bản model (có thể kèm markdown fence)."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Không tìm thấy JSON trong phản hồi judge: {text!r}")
    return json.loads(match.group(0))


def judge(ground_truth: str, review_output: str, model: str = PRIMARY_MODEL) -> Dict[str, Any]:
    """Gọi 9Router để đánh giá, fallback sang model phụ nếu lỗi/timeout."""
    prompt = _JUDGE_PROMPT.format(ground_truth=ground_truth, review_output=review_output)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    last_error: str = ""
    for candidate in (model, FALLBACK_MODEL if model == PRIMARY_MODEL else PRIMARY_MODEL):
        try:
            headers = {"Authorization": f"Bearer {ROUTER_KEY}"}
            resp = requests.post(ROUTER_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return _extract_json(content)
        except Exception as exc:  # noqa: BLE001 - ghi lại và thử fallback
            last_error = str(exc)
            payload["model"] = candidate
    raise RuntimeError(f"Judge gọi 9Router thất bại (cả primary và fallback): {last_error}")
