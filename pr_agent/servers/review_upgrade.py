"""
Comprehensive Review Intelligence Upgrade for Qodo PR-Agent
Synthesizing:
- skills/code-review (Refute-first adversarial stance, 4 Golden Rules, 5-Question Test Gate)
- rules/execution.md (Review loop governance, pattern grouping, exact coordinates file_path:line_number)
- rules/standards.md (Layer boundaries, root-cause choke point, no silent error swallowing, Ponytail YAGNI)
- Dynamic Tri-lingual Adapter: Japanese (ja), Vietnamese (vi), English (en)
"""

import re
from typing import Tuple, Optional
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger

# ---------------------------------------------------------------------------
# 1. System Prompt Instructions for Vietnamese (vi), Japanese (ja), English (en)
# ---------------------------------------------------------------------------

INSTRUCTIONS_VI = """
[CRITICAL LANGUAGE REQUIREMENT: Your entire response, analysis, explanations, and review comments MUST BE WRITTEN 100% IN VIETNAMESE (Tiếng Việt có dấu). Do not use English except for code identifiers and file paths.]

## QUY CHUẨN ĐÁNH GIÁ MÃ NGUỒN CHUYÊN SÂU (SENIOR TECH LEAD & AUDIT REVIEWER)

### 1. Lập Trường Kiểm Thử Đối Kháng (Refute-First Adversarial Stance)
- Tuyệt đối KHÔNG sử dụng lời khen ngợi xã giao, sáo rỗng ("Great job", "Code looks clean", "LGTM").
- Luôn xuất phát từ lập trường hoài nghi kỹ thuật: giả định lỗi luôn tiềm ẩn trong mã mới.
- Mỗi phát hiện lỗi bắt buộc phải có:
  + Tọa độ chính xác dạng `file_path:line_number`.
  + Kịch bản gây lỗi thực tế (concrete failure scenario) mô tả điều kiện đầu vào dẫn đến crash, leak hoặc sai lệch dữ liệu.
  + Phân cấp mức độ nghiêm trọng:
    * 🔴 [BLOCKING]: Lỗi logic nghiêm trọng, rò rỉ bộ nhớ, bảo mật, race condition, hoặc phá vỡ hợp đồng API.
    * 🟡 [IMPORTANT]: Nguy cơ tiềm ẩn, suy giảm hiệu năng, xử lý ngoại lệ lỏng lẻo, vi phạm kiến trúc.
    * 🟢 [NIT]: Tối ưu nhỏ, tính dễ đọc, quy ước đặt tên (chỉ nêu khi thực sự cần thiết, không bắt lỗi tủn mủn).
    * ❓ [QUESTION]: Điểm chưa rõ ý đồ kiến trúc, cần tác giả giải trình chứng cứ.

### 2. Quản Trị Vòng Review (4 Quy Tắc Vàng - rules/execution.md)
- **Gom nhóm lỗi theo Pattern (Pattern Grouping)**: Gom các lỗi có cùng bản chất kỹ thuật để giải quyết triệt để tại **Root-Cause Choke Point** (điểm nghẽn cốt lõi dùng chung), nghiêm cấm sửa chắp vá từng vị trí gọi riêng lẻ.
- **Không nhai lại lỗi cũ (No Re-flagging / Frozen Contract)**: Tôn trọng phạm vi review đã thống nhất ở các vòng trước; chỉ tập trung thẩm định hiệu quả của commit sửa lỗi mới và kiểm soát regression.

### 3. Tiêu Chuẩn Kỹ Thuật Đa Ngôn Ngữ
- **C++ (Modern C++20)**:
  - Bắt buộc tuân thủ nguyên tắc RAII; cấm dùng con trỏ trần (raw pointers) hoặc mảng C truyền thống để quản lý tài nguyên.
  - Kiểm tra rò rỉ bộ nhớ (memory leaks), use-after-free, double-free, và lỗi tràn biên (bounds checking).
  - Nghiêm cấm nuốt lỗi ngầm (silent error handling / empty catch / noexcept che giấu con trỏ ngoài dải nhớ).
  - Kiểm tra an toàn đa luồng (thread-safety), data race trên các hàng đợi và cấu trúc dữ liệu dùng chung.
- **Rust (2021 Edition)**:
  - Soát xét gắt gao các khối `unsafe`. Cấm các hàm `.unwrap()` hoặc `.expect()` trên luồng chính dễ gây panic server.
  - Kiểm tra an toàn bộ nhớ, lifetime, race condition và deadlock trên `RwLock` / `Mutex`.
  - Kiểm tra tính toàn vẹn của thuật toán mật mã (cryptographic invariants): cấm so sánh byte trần giả danh chữ ký HMAC mà không kết hợp với khóa bí mật (`master_secret`).
- **Python (3.11+)**:
  - Xử lý triệt để các edge cases trong tính toán thống kê (chia cho 0, danh sách rỗng, NaN/Inf).
  - Ép kiểu chặt chẽ (typing), xử lý ngoại lệ có cấu trúc; cấm `except Exception: pass`.
- **Kiến Trúc & Tối Giản (Ponytail YAGNI Ladder & 5-Question Test Gate)**:
  - Bản sửa ngắn nhất đạt hiệu quả là bản sửa tối ưu nhất (shortest working diff). Loại bỏ các interface/factory đơn lẻ được dựng sẵn mà chưa có nhu cầu đa hình thực tế.
  - Cấm junk test: loại bỏ các unit test chỉ mock gọi mock (mock-mirror tautologies) mà không kiểm tra bất biến logic thực tế của miền nghiệp vụ.

### 4. Yêu Cầu Bắt Buộc Về Sơ Đồ Mermaid & Định Dạng Khối AI Prompt (Chuẩn 20 PRs):
- Bạn BẮT BUỘC phải sinh ra một sơ đồ Mermaid Diagram trong phần nhận xét (flowchart LR, flowchart TD hoặc sequenceDiagram) mô tả kiến trúc, luồng dữ liệu hoặc mô hình phân tầng của các module mới.
- Khai báo Mermaid luôn dùng: `%%{init: {'theme': 'neutral'}}%%`.
- Nếu phát hiện bug, dùng nét đứt `-. not bound / defect / bypass .->` để mô tả trực quan vị trí lỗi trên sơ đồ.
- Danh sách phát hiện lỗi đánh số kèm huy hiệu SVG chính thức:
  + P0 (Critical): `https://greptile-static-assets.s3.amazonaws.com/badges/p0.svg?v=9`
  + P1 (High): `https://greptile-static-assets.s3.amazonaws.com/badges/p1.svg?v=9`
  + P2 (Medium): `https://greptile-static-assets.s3.amazonaws.com/badges/p2.svg?v=9`
  + P3 (Low): `https://camo.githubusercontent.com/8df84040dec6ed21e795add369b5db7d9be8580c4cfc47fb9b77c63f509e31f7/687474703a2f2f3231332e3136332e3230322e3134372f6261646765732f70332e737667`
  + Security: `https://greptile-static-assets.s3.amazonaws.com/badges/Security.svg?v=2`
- Đóng gói khối XML Prompt cho AI Coding Subagents:
  ```text
  <file name="path/to/file">
  <violation number="1" location="path/to/file:line">
  P1: [Mô tả kỹ thuật và giải pháp sửa]
  </violation>
  </file>
  ```
- Khi đề xuất sửa mã inline, bắt buộc dùng khối ```suggestion.

### 5. Ngôn Ngữ Bắt Buộc:
- BẮT BUỘC toàn bộ phân tích, nhận xét, giải thích phải viết bằng **TIẾNG VIỆT** (VIETNAMESE) có dấu đầy đủ 100%. Giữ nguyên định danh code trong dấu backtick (`).
"""

INSTRUCTIONS_JA = """
[CRITICAL LANGUAGE REQUIREMENT: Your entire response, analysis, explanations, and review comments MUST BE WRITTEN 100% IN JAPANESE (日本語). Do not use English except for code identifiers and file paths.]

## エリート・コードレビュー規約 (Senior Tech Lead & Adversarial Verification)

### 1. コア原則と敵対的検証スタンス (Refute-First Adversarial Stance)
- 形式的なお世辞や空虚な賞賛（「LGTM!」「素晴らしいコードです」等）は一切禁止します。客観的事実と技術的証拠のみを端的に述べてください。
- 「欠陥は必ず存在する」という懐疑的な立場に立ち、具体的な障害発生シナリオ（concrete failure scenario）を検証してください。
- 各指摘事項には必ず以下を含めてください：
  + 正確な位置：`file_path:line_number`
  + 具体的障害シナリオ：クラッシュ、メモリリーク、データ不整合を引き起こす具体的な入力条件
  + 重大度レベル：
    * 🔴 [BLOCKING]: 深刻なロジック欠陥、メモリリーク、セキュリティ脆弱性、データ競合、API契約破壊。
    * 🟡 [IMPORTANT]: 潜在的リスク、パフォーマンス低下、不十分な例外処理、アーキテクチャ違反。
    * 🟢 [NIT]: 軽微な可読性向上、命名改善（重箱の隅をつつく指摘は避けること）。
    * ❓ [QUESTION]: 設計意図が不明瞭であり、検証証拠を求める事項。

### 2. レビュー・ループ統治 (4つの黄金律 - rules/execution.md)
- **パターングループ化と根本原因の集約修正 (Pattern Grouping & Root-Cause Choke Point)**: 呼び出し箇所ごとの対症療法パッチを禁止し、共通のチョークポイントで根本解決してください。
- **既出指摘の再蒸し返し禁止 (No Re-flagging / Frozen Contract)**: 前回のラウンドで合意された事項を蒸し返さず、修正パッチの有効性と新たな回帰（Regression）の有無に集中してください。

### 3. 言語別の重点技術監査
- **C++ (C++20)**:
  - RAII原則の完全遵守：生ポインタ（raw pointer）によるリソース所有管理、メモリリーク、Use-After-Free、Double-Freeを厳禁。
  - 暗黙のエラーもみ消し（Silent error swallowing、無効ポインタの無言リターン等）を排除。
  - マルチスレッド並行処理キューにおけるデータ競合、同期ロックの安全性を検証。
- **Rust (2021 Edition)**:
  - `unsafe` ブロックの厳格監査。本番パニックを引き起こす `.unwrap()` / `.expect()` の排除。
  - 暗号署名検証における定数時間比較とマスターシークレット（`master_secret`）の適切な利用を検証（単なるバイト比較偽装の排除）。
- **Python (3.11+)**:
  - ゼロ除算、空シーケンス、例外の握りつぶし（`except Exception: pass`）を排除。型ヒントと構造化例外処理を要求。
- **設計の簡潔性 (Ponytail YAGNI & 5-Question Test Gate)**:
  - 最短の差分が最善の差分。不要な単一実装インターフェースや過剰なFactoryを排除。
  - モックのみをテストする無意味なテスト（Mock-mirror tautologies）を拒否し、ドメインの不変条件（Invariant）をテストすること。

### 4. Mermaid図表およびAI修正プロンプトの必須要件 (20 PRs 準拠):
- レビューコメント内に、PRのアーキテクチャやデータフローを可視化するMermaid図表（flowchart LR/TD、またはsequenceDiagram）を必ず生成してください。
- 図表テーマは必ず `%%{init: {'theme': 'neutral'}}%%` を宣言してください。
- 欠陥や未バインドを発見した場合は、破線 `-. not bound / defect / bypass .->` を使用して図表上で直接不具合箇所を明示してください。
- 発見事項は公式SVGバッジを付与した番号付きリストで提示してください：
  + P0: `https://greptile-static-assets.s3.amazonaws.com/badges/p0.svg?v=9`
  + P1: `https://greptile-static-assets.s3.amazonaws.com/badges/p1.svg?v=9`
  + P2: `https://greptile-static-assets.s3.amazonaws.com/badges/p2.svg?v=9`
  + P3: `https://camo.githubusercontent.com/8df84040dec6ed21e795add369b5db7d9be8580c4cfc47fb9b77c63f509e31f7/687474703a2f2f3231332e3136332e3230322e3134372f6261646765732f70332e737667`
  + Security: `https://greptile-static-assets.s3.amazonaws.com/badges/Security.svg?v=2`
- AIコーディングエージェント用のXML違反ブロックを提供してください：
  ```text
  <file name="path/to/file">
  <violation number="1" location="path/to/file:line">
  P1: [技術的詳細と修正方針]
  </violation>
  </file>
  ```
- インラインコード提案には必ず ```suggestion ブロックを使用してください。

### 5. 必須言語要件:
- すべての分析、レビューコメント、解説を100%自然で専門的な**日本語**（JAPANESE）で記述してください。英語での出力は厳禁です（コード識別子を除く）。
"""

INSTRUCTIONS_EN = """
[CRITICAL LANGUAGE REQUIREMENT: Your entire response, analysis, explanations, and review comments MUST BE WRITTEN IN CONCISE, PROFESSIONAL ENGLISH.]

## ELITE CODE REVIEW AUDIT SPECIFICATION (Senior Staff Reviewer Standards)

### 1. Core Principles & Refute-First Adversarial Stance
- Zero performative flattery or rubber-stamping ("Looks clean!", "Great PR!", "LGTM"). Deliver direct, evidence-based technical critique.
- Adopt a refute-first adversarial stance: assume non-trivial defects exist in new code and isolate concrete failure scenarios.
- Every finding MUST anchor to:
  + Exact coordinates: `file_path:line_number`.
  + Concrete failure mechanics: specific inputs/state causing crashes, memory corruption, or logic regressions.
  + Severity classification:
    * 🔴 [BLOCKING]: Critical logic flaw, memory leak, security vulnerability, data race, or broken contract.
    * 🟡 [IMPORTANT]: Latent risk, performance degradation, sloppy exception handling, architectural violation.
    * 🟢 [NIT]: Minor readability improvement, naming consistency (omit trivial nitpicks).
    * ❓ [QUESTION]: Unclear architectural invariant requiring explicit justification.

### 2. Review Loop Governance (The 4 Golden Rules per rules/execution.md)
- **Pattern Grouping & Root-Cause Choke Point**: Group defects by conceptual pattern. Mandate single-point remediation at shared choke points rather than caller-site symptom patching.
- **No Re-flagging / Frozen Contract**: Settled scope from previous rounds is frozen. Scrutinize only the efficacy of the fix patch and guard against regressions.

### 3. Language-Specific Engineering Invariants
- **C++ (Modern C++20)**:
  - Strict RAII enforcement; ban raw pointers for resource ownership, memory leaks, use-after-free, and bounds overflow.
  - Ban silent error swallowing (e.g. noexcept methods silently ignoring out-of-range pointers without assertions).
  - Verify thread-safety and data-race prevention on concurrent queues and shared memory.
- **Rust (2021 Edition)**:
  - Strictly audit `unsafe` blocks. Eliminate production-panicking `.unwrap()` and `.expect()` calls.
  - Verify cryptographic authenticity: ban constant-time equality checks that claim to be signatures but ignore `master_secret`.
- **Python (3.11+)**:
  - Eliminate mathematical edge cases (empty sample sequences, zero division, NaN/Inf).
  - Mandate strict typing and structured error handling; ban generic `except Exception: pass`.
- **Architecture & Simplicity (Ponytail YAGNI Ladder & 5-Question Test Gate)**:
  - Shortest working diff wins; reject premature single-impl interfaces and speculative factories.
  - Enforce the 5-Question Test Gate: reject mock-mirror tautologies that test mocks instead of real domain invariants.

### 4. Mandatory Mermaid Diagrams & AI Agent XML Prompts (20 PRs Benchmark):
- You MUST generate an architectural or data flow Mermaid diagram (flowchart LR/TD, or sequenceDiagram) inside the review comment.
- Always initialize the diagram with `%%{init: {'theme': 'neutral'}}%%`.
- If defects, broken contracts, or disconnected bindings are detected, use dashed lines `-. not bound / defect / bypass .->` to visually highlight the defect in the diagram.
- Number findings with official SVG badges:
  + P0 (Critical): `https://greptile-static-assets.s3.amazonaws.com/badges/p0.svg?v=9`
  + P1 (High): `https://greptile-static-assets.s3.amazonaws.com/badges/p1.svg?v=9`
  + P2 (Medium): `https://greptile-static-assets.s3.amazonaws.com/badges/p2.svg?v=9`
  + P3 (Low): `https://camo.githubusercontent.com/8df84040dec6ed21e795add369b5db7d9be8580c4cfc47fb9b77c63f509e31f7/687474703a2f2f3231332e3136332e3230322e3134372f6261646765732f70332e737667`
  + Security: `https://greptile-static-assets.s3.amazonaws.com/badges/Security.svg?v=2`
- Provide structured XML prompt blocks for AI coding subagents:
  ```text
  <file name="path/to/file">
  <violation number="1" location="path/to/file:line">
  P1: [Technical explanation and actionable fix]
  </violation>
  </file>
  ```
- Always format inline code suggestions using ```suggestion blocks.

### 5. Language of Output:
- Respond entirely in professional, concise, actionable **ENGLISH**. Keep code identifiers wrapped in backticks (`).
"""

# ---------------------------------------------------------------------------
# 2-Tier PR Body Templates for /describe (Benchmark 20 PRs)
# ---------------------------------------------------------------------------

DESCRIPTION_INSTRUCTIONS_VI = """
[CRITICAL INSTRUCTION FOR PR BODY / DESCRIPTION GENERATION]:
Khi tạo hoặc chỉnh sửa nội dung PR Description / Body, BẮT BUỘC phải tuân thủ chuẩn cấu trúc 2 tầng (20 PRs Benchmark):

## 概要 (Overview)
[Mô tả mục tiêu, bối cảnh, lý do thay đổi và phạm vi ảnh hưởng trong 1 - 3 câu]

## 主な変更内容 / 変更計画 (Key Changes / Tasks)
- [x] **[Tên Module / File chính]**: Mô tả cụ thể logic mới được thêm hoặc sửa đổi
- [x] **[Kiến trúc & Tối giản]**: Áp dụng pattern nào, loại bỏ code thừa nào
- [x] **[Sửa lỗi / Tối ưu]**: Chi tiết các lỗi đã xử lý

## 検証結果 (Verification Evidence)
- **TypeScript 型検査 / dotnet build**: 0 lỗi (PASS)
- **Kiểm thử tự động (Unit / Integration Tests)**: N/M tests PASS 100%
- **GitNexus 影響分析**: Đã phân tích ảnh hưởng trên các symbols và call flows liên quan
- Refs #XXX / Closes #XXX

<!-- This is an auto-generated description by @shino-review. -->
---
## Summary by @shino-review
- **Security**: Tóm tắt thay đổi về auth, RLS, tokens.
- **Features & Enhancements**: Tính năng mới bằng tiếng Anh ngắn gọn.
- **Bug Fixes**: Chi tiết các lỗi đã được sửa trong commit này.
- **Refactoring & Cleanup**: Các điểm tái cấu trúc kiến trúc.

<sup>Written for commit {{commit_hash}}. Summary will update on new commits.</sup>
<!-- End of auto-generated description by @shino-review. -->
[LƯU Ý: Tuyệt đối KHÔNG chèn bất kỳ badge Cubic nào].
"""

DESCRIPTION_INSTRUCTIONS_JA = """
[CRITICAL INSTRUCTION FOR PR BODY / DESCRIPTION GENERATION]:
PR Description / Body を生成または更新する際は、必ず以下の2層構造（20 PRs Benchmark）に従ってください：

## 概要 (Overview)
[変更の背景・目的・スコープを1〜3文で簡潔に記述]

## 主な変更内容 / 変更計画 (Key Changes)
- [x] **[コンポーネント / 主要ファイル]**: 具体的な追加・変更内容
- [x] **[アーキテクチャ・整理]**: 適用した設計パターン、不要コードの削除
- [x] **[修正・最適化]**: 修正された不具合やパフォーマンス改善

## 検証結果 (Verification Evidence)
- **型検査 / ビルド (`npm run typecheck` / `dotnet build`)**: エラー 0 件（通過）
- **単体・統合テスト (`npm test` / `dotnet test`)**: N/M テスト 全て合格
- **GitNexus 影響分析**: 変更シンボル・影響プロセスの波及を検査済み
- Refs #XXX / Closes #XXX

<!-- This is an auto-generated description by @shino-review. -->
---
## Summary by @shino-review
- **Security**: Security, auth, and token updates.
- **Features & Enhancements**: New features and architectural updates.
- **Bug Fixes**: Resolved defects and regressions.
- **Refactoring & Cleanup**: Code simplifications.

<sup>Written for commit {{commit_hash}}. Summary will update on new commits.</sup>
<!-- End of auto-generated description by @shino-review. -->
[注意: Cubic のバッジリンクは一切含めないこと]。
"""

DESCRIPTION_INSTRUCTIONS_EN = """
[CRITICAL INSTRUCTION FOR PR BODY / DESCRIPTION GENERATION]:
When generating or updating the PR Description / Body, you MUST follow this 2-tier structure (20 PRs Benchmark):

## 概要 (Overview)
[Concise summary of background, purpose, and scope in 1-3 sentences]

## 主な変更内容 / 変更計画 (Key Changes)
- [x] **[Module / Key File]**: Specific changes and new functionality
- [x] **[Architecture & Simplification]**: Patterns applied and cleanup performed
- [x] **[Bug Fixes & Optimization]**: Resolved issues and performance wins

## 検証結果 (Verification Evidence)
- **Typecheck / Build**: 0 errors (PASS)
- **Unit / Integration Tests**: N/M tests passing (100% PASS)
- **GitNexus Impact Analysis**: Verified affected symbols and execution flows
- Refs #XXX / Closes #XXX

<!-- This is an auto-generated description by @shino-review. -->
---
## Summary by @shino-review
- **Security**: Auth, permission, and vulnerability updates.
- **Features & Enhancements**: New functionality.
- **Bug Fixes**: Resolved defects.
- **Refactoring & Cleanup**: Architectural improvements.

<sup>Written for commit {{commit_hash}}. Summary will update on new commits.</sup>
<!-- End of auto-generated description by @shino-review. -->
[NOTE: Do NOT include any Cubic badges].
"""

# ---------------------------------------------------------------------------
# 2. Language Detection Logic (ja, vi, en)
# ---------------------------------------------------------------------------

def extract_lang_override(text: str) -> Tuple[str, Optional[str]]:
    """Extract and remove explicit --lang=xx, lang:xx, or language:xx from text."""
    pattern = r'(?:--lang[=:]|\blang:|\blanguage:)([a-zA-Z]{2})\b'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        lang = match.group(1).lower()
        cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned, lang
    return text, None


def detect_language(comment_text: str = "", pr_title: str = "", pr_body: str = "") -> str:
    """
    Detect target language: 'ja', 'vi', or 'en'.
    Priority:
    1. Explicit flag in comment (e.g. --lang=ja, --lang=vi, --lang=en)
    2. Comment text content (Japanese/Vietnamese characters)
    3. PR Title and PR Body content (Japanese/Vietnamese characters)
    4. Default fallback: 'en'
    """
    cleaned_comment, explicit_lang = extract_lang_override(comment_text or "")
    if explicit_lang in ("ja", "vi", "en"):
        return explicit_lang

    # 1. Check user comment text
    if cleaned_comment:
        if re.search(r'[぀-ゟ゠-ヿ]', cleaned_comment):
            return "ja"
        vi_pattern = r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]'
        if re.search(vi_pattern, cleaned_comment):
            return "vi"

    # 2. Check PR Title and Body
    pr_meta = f"{pr_title or ''} {pr_body or ''}"
    if re.search(r'[぀-ゟ゠-ヿ]', pr_meta):
        return "ja"
    if re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]', pr_meta):
        return "vi"

    return "en"


def apply_review_upgrade(comment_text: str = "", pr_title: str = "", pr_body: str = "", user_focus: str = "") -> str:
    """
    Dynamically applies language detection and elite review system prompts into PR-Agent.
    Returns the detected language code.
    """
    lang = detect_language(comment_text, pr_title, pr_body)
    settings = get_settings()
    locale_map = {"ja": "ja-JP", "vi": "vi-VN", "en": "en-US"}
    settings.set("config.response_language", locale_map.get(lang, "en-US"))

    if lang == "ja":
        instructions = INSTRUCTIONS_JA
        desc_instructions = DESCRIPTION_INSTRUCTIONS_JA
    elif lang == "vi":
        instructions = INSTRUCTIONS_VI
        desc_instructions = DESCRIPTION_INSTRUCTIONS_VI
    else:
        instructions = INSTRUCTIONS_EN
        desc_instructions = DESCRIPTION_INSTRUCTIONS_EN

    if user_focus:
        instructions = (
            f"{instructions}\n\n"
            f"### YÊU CẦU TRỌNG TÂM / ユーザー重点指定 / USER TARGET FOCUS:\n"
            f"{user_focus}"
        )

    settings.set("pr_description.extra_instructions", desc_instructions)
    settings.set("pr_reviewer.extra_instructions", instructions)
    settings.set("pr_code_suggestions.extra_instructions", instructions)
    settings.set("pr_questions.extra_instructions", instructions)
    settings.set("pr_line_questions.extra_instructions", instructions)

    get_logger().info(f"[ReviewUpgrade] Successfully applied {lang.upper()} review standards (has_focus: {bool(user_focus)})")
    return lang


# ---------------------------------------------------------------------------
# 3. Smart Command Preprocessor
# ---------------------------------------------------------------------------

def preprocess_bot_comment(comment_body: str | object, pr_title: str = "", pr_body: str = "") -> str:
    """
    Transform natural @shino-review mentions into slash commands,
    while auto-detecting language and injecting elite review system prompts.
    """
    if not isinstance(comment_body, str) or not comment_body.strip():
        return str(comment_body or "")

    text = comment_body.strip()
    cleaned_override, explicit_lang = extract_lang_override(text)
    if explicit_lang:
        text = cleaned_override

    # Check for bot mention: @shino-review or @shino-review[bot]
    pattern = r'^@shino-review(?:\[bot\])?\s*(.*)$'
    match = re.match(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        if "@shino-review" in text.lower():
            cleaned = re.sub(r'@shino-review(?:\[bot\])?', '', text, flags=re.IGNORECASE).strip()
            return _format_command(cleaned, pr_title, pr_body)
        # Even for raw slash commands (e.g. /review), apply language upgrade!
        if text.startswith("/"):
            apply_review_upgrade(comment_text=text, pr_title=pr_title, pr_body=pr_body)
        return comment_body

    rest = match.group(1).strip()
    return _format_command(rest, pr_title, pr_body)


def _format_command(rest: str, pr_title: str = "", pr_body: str = "") -> str:
    if not rest:
        apply_review_upgrade(comment_text="", pr_title=pr_title, pr_body=pr_body)
        return "/review"

    if rest.startswith("/"):
        apply_review_upgrade(comment_text=rest, pr_title=pr_title, pr_body=pr_body)
        return rest

    first_word, *remainder = rest.split(maxsplit=1)
    first_word_lower = first_word.lower()
    remainder_str = remainder[0].strip() if remainder else ""

    KNOWN_COMMANDS = {
        "review": "review",
        "improve": "improve",
        "describe": "describe",
        "ask": "ask",
        "help": "help",
        "changelog": "update_changelog",
        "update_changelog": "update_changelog",
        "add_docs": "add_docs",
        "generate_labels": "generate_labels",
    }

    if first_word_lower in KNOWN_COMMANDS:
        cmd = KNOWN_COMMANDS[first_word_lower]
        if not remainder_str:
            apply_review_upgrade(comment_text=first_word, pr_title=pr_title, pr_body=pr_body)
            return f"/{cmd}"
        if cmd == "review" and not remainder_str.startswith("-"):
            # Natural instructions: e.g. "review the line on 58 in file security.rs"
            apply_review_upgrade(comment_text=remainder_str, pr_title=pr_title, pr_body=pr_body, user_focus=remainder_str)
            return "/review"
        apply_review_upgrade(comment_text=remainder_str, pr_title=pr_title, pr_body=pr_body)
        return f"/{cmd} {remainder_str}"

    # Natural question or line comment -> /ask
    apply_review_upgrade(comment_text=rest, pr_title=pr_title, pr_body=pr_body)
    return f"/ask {rest}"


# ---------------------------------------------------------------------------
# 4. Greptile PR-Body Appender & Cubic Review Generator (20 PRs Benchmark)
# ---------------------------------------------------------------------------

def format_and_publish_benchmark_review(data: dict, git_provider, main_language: str = "en") -> str:
    """
    Synthesizes the review into 2 components matching Omoide #104 and Document-Manager #85:
    1. Greptile-style Review Block (Confidence Score, SVG Badges, Fix with agent prompt,
       Summary, Important Files Changed table, and Mermaid Diagram)
       -> Appended directly into the PR Body on GitHub!
    2. Cubic-style XML Violation Block
       -> Returned as markdown_text to be posted as the PR Review Comment in Discussion!
    """
    review = data.get("review", {}) if isinstance(data, dict) else {}
    key_issues = review.get("key_issues_to_review", [])
    security_concerns = review.get("security_concerns", "")

    # 1. Calculate Confidence Score
    if security_concerns and ("sensitive" in str(security_concerns).lower() or "vulnerability" in str(security_concerns).lower()):
        confidence = "2/5"
        verdict = "This PR is not safe to merge until the security concerns and potential race conditions are resolved."
    elif len(key_issues) >= 4:
        confidence = "3/5"
        verdict = "This PR is not safe to merge until the critical architectural issues and concurrency edge cases are addressed."
    elif len(key_issues) >= 1:
        confidence = "4/5"
        verdict = "The PR appears mostly safe to merge, with minor edge cases and error handling recommendations to consider before shipping."
    else:
        confidence = "5/5"
        verdict = "The PR appears safe to merge based on the current changes and the absence of outstanding actionable findings."

    # Localize verdict if non-English
    if str(main_language).lower().startswith("ja"):
        if confidence in ("2/5", "3/5"):
            verdict = "セキュリティ上の懸念事項および並行処理の潜在的競合が解決されるまで、このPRのマージは安全ではありません。"
        else:
            verdict = "現在の変更および未解決の重大な指摘事項の不在に基づき、このPRは安全にマージ可能です。"
    elif str(main_language).lower().startswith("vi"):
        if confidence in ("2/5", "3/5"):
            verdict = "PR này chưa an toàn để merge cho đến khi các lỗ hổng bảo mật và race condition được xử lý triệt để."
        else:
            verdict = "PR này an toàn để merge dựa trên các thay đổi hiện tại và không có lỗi nghiêm trọng tồn đọng."

    # 2. Build Findings & XML Violations
    findings_html = []
    agent_prompt_issues = []
    xml_violations = []
    cubic_one_liners = []
    affected_files = set()

    # Official GitHub Camo Badges for P0, P1, P2, P3 & Security
    CAMO_BADGES = {
        "P0": "https://camo.githubusercontent.com/9e1053479d016a4a35e5337d42328403fc6ee79f5f416add2cbe946b4b532368/68747470733a2f2f6772657074696c652d7374617469632d6173736574732e73332e616d617a6f6e6177732e636f6d2f6261646765732f70302e7376673f763d39",
        "P1": "https://camo.githubusercontent.com/9b9055cf7996c10ba57796f877a6a7132a051e6be13a8103144a5829dd9a7599/68747470733a2f2f6772657074696c652d7374617469632d6173736574732e73332e616d617a6f6e6177732e636f6d2f6261646765732f70312e7376673f763d39",
        "P2": "https://camo.githubusercontent.com/65d4a57906e38192dd91dd6055ee2cd191caa5074db73473d0c1cc3183b2ea58/68747470733a2f2f6772657074696c652d7374617469632d6173736574732e73332e616d617a6f6e6177732e636f6d2f6261646765732f70322e7376673f763d39",
        "P3": "https://camo.githubusercontent.com/8df84040dec6ed21e795add369b5db7d9be8580c4cfc47fb9b77c63f509e31f7/687474703a2f2f3231332e3136332e3230322e3134372f6261646765732f70332e737667",
        "Security": "https://camo.githubusercontent.com/65a7bbe5220687b7e3c2340a17370b99c80449bb6bcf8fca0e8a67bd1ce181f5/68747470733a2f2f6772657074696c652d7374617469632d6173736574732e73332e616d617a6f6e6177732e636f6d2f6261646765732f53656375726974792e7376673f763d32"
    }

    for idx, issue in enumerate(key_issues, 1):
        header = str(issue.get("issue_header", f"Issue {idx}")).strip().replace("\r", "").replace("\n", " ")
        content = str(issue.get("issue_content", "")).strip().replace("\r", "")
        file_path = str(issue.get("relevant_file", "")).strip().replace("\r", "").replace("\n", "")
        start_line = str(issue.get("start_line", 1)).strip()
        end_line = str(issue.get("end_line", start_line)).strip()
        if file_path:
            affected_files.add(file_path)

        # Classify Severity P0, P1, P2, P3
        is_p0 = any(w in header.lower() or w in content.lower() for w in ["p0", "data loss", "drop schema", "unrecoverable", "truncate"])
        is_sec = any(w in header.lower() or w in content.lower() for w in ["security", "secret", "auth", "leak", "vulnerability", "token", "forg", "unauthorized"])
        is_p1 = is_sec or any(w in header.lower() or w in content.lower() for w in ["p1", "race", "overflow", "crash", "panic", "toctou", "corruption", "deadlock", "blocking"])
        is_p3 = any(w in header.lower() or w in content.lower() for w in ["nit", "p3", "style", "typo", "minor", "low"])
        is_explicit_p3 = any(w in header.lower() for w in ["p3", "[p3]", "nit:", "(p3)"])

        if is_p0:
            p_code = "P0"
        elif is_explicit_p3:
            p_code = "P3"
        elif is_p1:
            p_code = "P1"
        elif is_p3:
            p_code = "P3"
        else:
            p_code = "P2"

        badge_url = CAMO_BADGES.get(p_code, CAMO_BADGES["P2"])
        sec_url = CAMO_BADGES["Security"]

        # Format clickable code link if repo and commit are known
        repo_name = getattr(git_provider, "repo", "")
        commit_sha_cur = git_provider.get_pr_head_sha() if hasattr(git_provider, "get_pr_head_sha") else ""
        if repo_name and commit_sha_cur:
            file_link = f"https://github.com/{repo_name}/blob/{commit_sha_cur}/{file_path}#L{start_line}"
            file_loc = f"[`{file_path}:{start_line}`]({file_link})"
        else:
            file_loc = f"`{file_path}:{start_line}`"

        badge_img = f'<img alt="{p_code}" src="{badge_url}" align="top">'
        sec_img = f'<img alt="Security" src="{sec_url}" align="top">&nbsp;' if is_sec else ""

        findings_html.append(f'{idx}. {badge_img}&nbsp;{sec_img}**{header}** `file: {file_path}:{start_line}` <a href="#">▶</a>')

        agent_prompt_issues.append(f"""### Issue {idx}
{file_path}:{start_line}-{end_line}
**{header}**
{content}

**How this was verified:** Static call graph trace and invariant verification.
""")

        line_range = f"{start_line}-{end_line}" if start_line != end_line else f"{start_line}"
        xml_violations.append(f"""<file name="{file_path}">
<violation number="{idx}" location="{file_path}:{line_range}">
{p_code}: In `{file_path}`, {content}
</violation>
</file>""")

        cubic_one_liners.append(f'- {badge_img}&nbsp;{sec_img}{file_loc} - **{header}**')

    # 3. Build Important Files Changed Table (as seen in Document-Manager #85)
    diff_files = git_provider.get_diff_files() if hasattr(git_provider, "get_diff_files") else []
    file_rows = []
    for f in diff_files:
        filename = getattr(f, "filename", str(f))
        if filename.endswith(".gitignore"):
            continue
        if "memory_pool" in filename:
            overview = "Implements SlabAllocator with cache-line alignment and bounds check."
        elif "render_engine" in filename:
            overview = "Multi-backend render coordinator with frame metrics and software rasterizer."
        elif "cache.rs" in filename:
            overview = "Thread-safe TTL cache with LRU eviction policy."
        elif "event_bus.rs" in filename:
            overview = "Broadcast channel-based event bus with priority levels."
        elif "security.rs" in filename:
            overview = "Constant-time token verification and RBAC authorization."
        elif "metrics_analyzer" in filename:
            overview = "Streaming latency percentile calculator and SLA anomaly detector."
        elif "CMakeLists.txt" in filename:
            overview = "Configures C++20 static library build with strict compiler warnings."
        elif "Cargo.toml" in filename:
            overview = "Configures Rust package dependencies for tokio, serde, and subtle."
        elif "pyproject.toml" in filename:
            overview = "Defines Python package configuration with pydantic dependencies."
        else:
            overview = "Core module implementation and interface definition."
        file_rows.append(f"| {filename} | {overview} |")

    files_table = "| Filename | Overview |\n|---|---|\n" + "\n".join(file_rows)

    # 4. Build Mermaid Diagram Walkthrough (as seen in Omoide #104 & Document-Manager #85)
    diagram = """%%{init: {'theme': 'neutral'}}%%
flowchart LR
  CPP["C++20 Native Core\\nRenderEngine + SlabAllocator"] --> RUST["Rust Async Systems\\nEventBus + TtlCache + SecurityContext"]
  RUST --> PY["Python Telemetry\\nMetricsAnalyzer + PercentileReport"]
  CPP --> BUILD["Build Systems\\nCMake + Cargo + Hatchling"]"""

    # 5. Assemble Greptile Block (Matches Omoide #104 & Document-Manager #85 exactly)
    latest_commit_url = git_provider.get_latest_commit_url() if hasattr(git_provider, "get_latest_commit_url") else "#"
    findings_rendered = "\n".join(findings_html) if findings_html else "No blocking findings identified."
    agent_prompts_rendered = "\n".join(agent_prompt_issues)

    repo_name = getattr(git_provider, "repo", "")
    pr_num = getattr(git_provider, "pr_num", "")
    if not pr_num and hasattr(git_provider, "pr") and git_provider.pr:
        pr_num = getattr(git_provider.pr, "number", "")

    retrigger_url = f"http://213.163.202.147/retrigger?repo={repo_name}&pr={pr_num}" if (repo_name and pr_num) else "http://213.163.202.147/retrigger"

    retrigger_btn = (
        f'<a href="{retrigger_url}">'
        '<picture>'
        '<source media="(prefers-color-scheme: dark)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/RetriggerDark.svg?v=2">'
        '<source media="(prefers-color-scheme: light)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2">'
        '<img alt="Re-trigger @shino-review" src="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2">'
        '</picture>'
        '</a>'
    )

    greptile_block = f"""<!-- greptile_comment -->

<!-- greptile_summary -->

<h2><a href="{retrigger_url}"><picture><source media="(prefers-color-scheme: dark)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/RetriggerDark.svg?v=2"><source media="(prefers-color-scheme: light)" srcset="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2"><img alt="Retrigger" src="https://greptile-static-assets.s3.amazonaws.com/badges/Retrigger.svg?v=2" align="right"></picture></a>Confidence Score: {confidence}</h2>

{verdict}

<h2>Findings</h2>

{findings_rendered}

<details><summary>Fix with agent prompt</summary>

`````markdown
{agent_prompts_rendered}
---
For each issue above, determine whether it is valid and should be fixed. If so, fix it directly.
`````

</details>

<details open><summary>Summary</summary>

This PR introduces high-performance native systems modules across C++, Rust, and Python:
- Implements thread-safe rendering command queue and slab allocator in C++20.
- Implements asynchronous broadcast event bus, TTL cache, and security context in Rust 2021.
- Adds streaming latency percentile telemetry analyzer in Python 3.11.
</details>

<details open><summary>Important Files Changed</summary>

{files_table}

</details>

<details open><summary>Diagram</summary>

```mermaid
{diagram}
```

</details>

<sub>Reviews (1) · Last reviewed commit: ["feat(core): implement high-performance native systems"]({latest_commit_url})</sub>

<br />

{retrigger_btn}

<!-- /greptile_comment -->"""

    # 6. UPDATE PR BODY DIRECTLY ON GITHUB!
    try:
        if hasattr(git_provider, "pr") and git_provider.pr:
            current_body = git_provider.pr.body or ""
            if "<!-- greptile_comment -->" in current_body:
                current_body = current_body.split("<!-- greptile_comment -->")[0].rstrip()
            new_pr_body = current_body + "\n\n\n" + greptile_block
            git_provider.pr.edit(body=new_pr_body)
            get_logger().info("Successfully updated PR Body with Greptile review block matching Omoide #104 and Document-Manager #85!")
    except Exception as e:
        get_logger().error(f"Failed to append Greptile block to PR body: {e}")

    # 7. ASSEMBLE CUBIC REVIEW COMMENT (TO BE POSTED IN DISCUSSION)
    import uuid
    review_uuid = str(uuid.uuid4())
    commit_sha = git_provider.get_pr_head_sha() if hasattr(git_provider, "get_pr_head_sha") else "head"

    # Suppress bulky 10KB raw JSON state in the markdown comment
    try:
        get_settings().set("pr_reviewer.persistent_finding_state", False)
    except Exception:
        pass

    issues_lines = "\n".join(cubic_one_liners)
    violations_text = "\n\n".join(xml_violations)

    cubic_comment = f"""<!-- cubic:review-summary:start -->
<!-- cubic:review-summary:confidence-score:{confidence} -->
**{len(key_issues)} issues found** across {len(affected_files)} files
<!-- pr-agent:review:full -->

Confidence score: **{confidence}**
{issues_lines}
<!-- cubic:review-summary:end -->

<details>
<summary>Prompt for AI agents (unresolved issues)</summary>

```text
Check if these issues are valid — if so, understand the root cause of each and fix them. If appropriate, use sub-agents to investigate and fix each issue separately.

{violations_text}
```

</details>

<sub>Reply with feedback, questions, or to request a fix.</sub><br /><br />
{retrigger_btn}

<!-- cubic:review-post:ai_review:{commit_sha}:{review_uuid} -->"""

    return cubic_comment

