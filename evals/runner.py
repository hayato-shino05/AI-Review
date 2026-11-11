"""Chạy Daily Eval cho AI-Review trên VPS test."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .alert import create_github_issue
    from .judge import judge
except ImportError:  # cho phép chạy trực tiếp: python3 evals/runner.py
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evals.alert import create_github_issue
    from evals.judge import judge

BASE_DIR = Path(__file__).resolve().parent
CORPUS_PATH = BASE_DIR / "corpus" / "review_cases.json"
HISTORY_DIR = BASE_DIR / "history"

# Bot review placeholder: gửi diff qua LLM review module nếu có, ngược lại giả lập.
# Ở đây ta nhận đầu vào là diff của case; tìm review_module nếu tồn tại.
REVIEW_MODULE_PATH = BASE_DIR.parent / "review_module.py"

RECALL_THRESHOLD = 0.90
FP_THRESHOLD = 0
SCORE_THRESHOLD = 3.8


def _load_cases() -> list[dict]:
    with open(CORPUS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def _simulate_review(diff: str) -> str:
    """Giả lập output review bot (thay bằng review_module khi có)."""
    if REVIEW_MODULE_PATH.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("review_module", REVIEW_MODULE_PATH)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module.review(diff)  # type: ignore[attr-defined]
    # Giả lập đơn giản: bot phát hiện đúng ground truth (để kiểm tra pipeline).
    return f"Phát hiện vấn đề theo diff:\n{diff}\nKết luận: có lỗi cần sửa."


def run_all(dry_run: bool = False) -> dict:
    cases = _load_cases()
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    start = time.perf_counter()
    total_p1 = 0
    caught_p1 = 0
    fp_cases = 0

    for case in cases:
        case_start = time.perf_counter()
        review_output = _simulate_review(case["diff"])
        try:
            scores = judge(case["ground_truth"], review_output)
            verdict = scores.get("verdict", "FAIL")
            overall = float(scores.get("overall", 0))
        except Exception as exc:  # noqa: BLE001
            scores = {"error": str(exc)}
            verdict = "FAIL"
            overall = 0.0

        is_p1 = case.get("severity") == "P1"
        is_clean = case.get("id") == "CLEAN-CODE-01"
        if is_p1:
            total_p1 += 1
            if verdict == "PASS":
                caught_p1 += 1
        if is_clean and verdict != "PASS":
            fp_cases += 1

        results.append(
            {
                "case_id": case["id"],
                "severity": case.get("severity"),
                "verdict": verdict,
                "overall": overall,
                "scores": scores,
                "duration_seconds": round(time.perf_counter() - case_start, 3),
            }
        )

    total_duration = round(time.perf_counter() - start, 3)
    recall_rate = (caught_p1 / total_p1) if total_p1 else 1.0
    fp_rate = fp_cases  # số case sạch bị false positive
    avg_score = (
        sum(r["overall"] for r in results if isinstance(r.get("overall"), (int, float)))
        / len(results)
        if results
        else 0.0
    )

    violations = []
    if recall_rate < RECALL_THRESHOLD:
        violations.append(f"Recall {recall_rate:.0%} < {RECALL_THRESHOLD:.0%}")
    if fp_rate > FP_THRESHOLD:
        violations.append(f"False positives {fp_rate} > {FP_THRESHOLD}")
    if avg_score < SCORE_THRESHOLD:
        violations.append(f"Điểm trung bình {avg_score:.2f} < {SCORE_THRESHOLD}")

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(cases),
        "total_duration_seconds": total_duration,
        "recall_rate": round(recall_rate, 4),
        "caught_p1": caught_p1,
        "total_p1": total_p1,
        "false_positives": fp_rate,
        "average_judge_score": round(avg_score, 4),
        "violations": violations,
        "results": results,
    }

    out_path = HISTORY_DIR / f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    if violations and not dry_run:
        title = f"[AI-Review Eval] Chất lượng review vi phạm ngưỡng ({', '.join(violations)})"
        body = (
            f"Kết quả eval lúc {summary['run_at']} UTC:\n\n"
            f"- Recall P1: {recall_rate:.0%} ({caught_p1}/{total_p1})\n"
            f"- False positives: {fp_rate}\n"
            f"Điểm trung bình: {avg_score:.2f}\n"
            f"- Tổng thời gian: {total_duration}s\n\n"
            f"Chi tiết: {out_path}\n"
        )
        create_github_issue(title, body, dry_run=False)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy Daily Eval AI-Review")
    parser.add_argument("--dry-run", action="store_true", help="Chạy không tạo issue GitHub")
    args = parser.parse_args()
    run_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
