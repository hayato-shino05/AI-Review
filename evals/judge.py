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

_JUDGE_PROMPT = """Bạn là Trưởng ban Thẩm định Chất lượng AI Review (Lead Evaluation Judge).
Nhiệm vụ: Đánh giá chất lượng của [Bot review output] so với [Ground truth diff] một cách nghiêm ngặt, đối kháng, không thiên vị.

### 1. BỐN TIÊU CHÍ ĐÁNH GIÁ (Thang điểm 0 - 5):
- `accuracy` (0-5):
  * 5: Bắt chính xác 100% tất cả lỗi nghiêm trọng P1/P2 trong Ground truth.
  * 3-4: Bắt được vấn đề chính nhưng phân tích chưa sâu hoặc sai lệch dòng nhẹ.
  * 0-2: Bỏ sót lỗi nghiêm trọng P1 hoặc phân tích sai hoàn toàn bản chất kỹ thuật.
- `actionability` (0-5):
  * 5: Hướng dẫn sửa chữa rõ ràng, an toàn, có thể áp dụng ngay lập tức (choke point fix).
  * 3-4: Đề xuất chung chung ("cần thêm lock", "cần bắt timeout") nhưng đúng hướng.
  * 0-2: Không có giải pháp hoặc đề xuất sai làm phát sinh thêm lỗi.
- `hallucination_penalty` (0-5):
  * 5: 100% trung thực, không bịa đặt bất kỳ chi tiết nào ngoài diff.
  * 3-4: Suy diễn nhẹ về môi trường nhưng không phán đoán lỗi ảo.
  * 0-2: BỊA LỖI ẢO GIÁC (False Positive) không hề có trong diff (ví dụ: bịa SQLi trên hàm toán học, hoặc báo lỗi trên code sạch).
- `overall` (0-5): Điểm tổng hợp có trọng số:
  overall = round(0.4 * accuracy + 0.3 * actionability + 0.3 * hallucination_penalty, 2)

### 2. CÁC QUY TẮC BẮT BUỘC (NON-NEGOTIABLE INVARIANTS):
- [QUY TẮC 1]: Nếu Ground truth có lỗi P1 (Blocking) mà Bot review BỎ SÓT -> BẮT BUỘC `verdict: "FAIL"`, bất kể điểm overall.
- [QUY TẮC 2]: Nếu Ground truth là Clean Code (0 lỗi) mà Bot review BÁO CÓ LỖI (False Positive) -> BẮT BUỘC `verdict: "FAIL"`, `hallucination_penalty <= 1`.
- [QUY TẮC 3] (Anti-Sycophancy): Nếu Bot review chỉ đưa ra lời khen sáo rỗng ("Great job", "LGTM") trên diff có lỗi -> BẮT BUỘC `verdict: "FAIL"`, `accuracy: 0`.
- [QUY TẮC 4]: Nếu Ground truth là Clean Code và Bot review chính xác KHÔNG BÁO LỖI NÀO -> BẮT BUỘC `verdict: "PASS"`, `overall: 5.0`.

### 3. ĐỊNH DẠNG ĐẦU RA:
Trả về duy nhất 1 khối JSON hợp lệ, KHÔNG thêm bất kỳ lời dẫn giải hay văn bản nào bên ngoài:
{{"accuracy": <float 0-5>, "actionability": <float 0-5>, "hallucination_penalty": <float 0-5>, "overall": <float 0-5>, "verdict": "PASS"|"FAIL", "reason": "<giải thích súc tích tiếng Việt>"}}

[Ground truth diff]:
{ground_truth}

[Bot review output]:
{review_output}
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Bóc tách JSON an toàn từ phản hồi của model (xử lý markdown fence, text bao quanh)."""
    text_clean = text.strip()
    # Loại bỏ codeblock markdown nếu có
    if text_clean.startswith("```"):
        text_clean = re.sub(r"^```(?:json)?\s*", "", text_clean)
        text_clean = re.sub(r"\s*```$", "", text_clean)

    match = re.search(r"\{[\s\S]*\}", text_clean)
    if not match:
        raise ValueError(f"Không tìm thấy JSON trong phản hồi judge: {text!r}")

    raw_json = match.group(0)
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        # Thử loại bỏ dấu phẩy thừa ở cuối dòng trước khi đóng ngoặc
        cleaned = re.sub(r",\s*([\}\]])", r"\1", raw_json)
        data = json.loads(cleaned)

    # Đảm bảo đầy đủ các trường tối thiểu
    data.setdefault("accuracy", 0.0)
    data.setdefault("actionability", 0.0)
    data.setdefault("hallucination_penalty", 0.0)
    data.setdefault("overall", 0.0)
    data.setdefault("verdict", "FAIL")
    data.setdefault("reason", "")
    return data


def judge(ground_truth: str, review_output: str, model: str = PRIMARY_MODEL) -> Dict[str, Any]:
    """Gọi 9Router để đánh giá đối kháng, tự động fallback nếu lỗi/timeout."""
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
            payload["model"] = candidate
            resp = requests.post(ROUTER_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = _extract_json(content)
            # Chuẩn hóa kiểu dữ liệu
            result["overall"] = float(result.get("overall", 0))
            result["accuracy"] = float(result.get("accuracy", 0))
            result["actionability"] = float(result.get("actionability", 0))
            result["hallucination_penalty"] = float(result.get("hallucination_penalty", 0))
            result["verdict"] = str(result.get("verdict", "FAIL")).upper()
            return result
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(f"Judge gọi 9Router thất bại (cả primary và fallback): {last_error}")
