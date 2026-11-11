---
name: shino-review
description: "AI-assisted two-axis code review protocol: Standards (12 Fowler Smells, 5-Question Test Gate) vs Spec Conformance (AC, Scope Creep), Greptile 4-tier triage (Actionable, Informational, Addressed, False Positive), confidence scoring, and review loop governance (Max 3 rounds hard stop, scoped commit review, batch GraphQL thread resolution). Supports local diff, PR number, and --loop auto-fix."
version: 2.0.0
argument-hint: "[target PR, branch, commit-hash, or diff path] [--loop]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - mcp__codegraph__codegraph_explore
  - mcp__gitnexus__impact
  - mcp__gitnexus__detect_changes
  - mcp__github__pull_request_read
  - mcp__github__pull_request_review_write
  - mcp__github__add_issue_comment
  - Monitor
---

# Shino Review Protocol (`/shino-review`)

Unified AI code review protocol integrating Anthropic Claude Code review loop governance, Greptile AI review engine triage (`greptileai/skills`), and Two-Axis Isolated Auditing.

---

## 1. Negative Anchoring Table (Review Anti-Habit Invariants)

Suppresses habitual review biases and locks Claude into mandatory review invariants:

| Pre-training Habit / Bad Practice | Mandatory Invariant | Technical Rationale (Why) |
|---|---|---|
| **Performative Flattery & Rubber-Stamping** (`"Looks great! Clean code!"`) | **Refute-first adversarial stance; zero performative praise.** | Superficial praise conceals critical defects (race conditions, memory leaks, boundary bypasses) and pollutes context. |
| **Endless Ping-Pong Loops** (Re-scanning full PR on Round 2+, cycling >50 times) | **Max 3-Round Hard Stop; Scoped review on commit hash from Round 2 onwards.** | 59% of review comments in Round 3+ simply re-flag Round-1 items without catching new bugs. |
| **Scattered Symptom Patching** (Patching individual callers line-by-line) | **Pattern Grouping: Identify `file_path:line_number`, fix once at shared root-cause choke point.** | Individual patches create new surface area and leave sibling execution paths broken. |
| **Re-flagging Settled Issues** (Nhai lại bug cũ đã thống nhất) | **Frozen Review Contract: Scope is frozen after Round 1; Round 2+ verifies only fix efficacy and regressions.** | Shifting criteria mid-review destabilizes the review contract and blocks convergence. |
| **Premature Capitulation / False Retraction** (Blindly apologizing and editing on invalid bot feedback) | **Evaluate feedback technically against specs; refute false positives with concrete evidence.** | Sycophantic capitulation mutates correct code into defective implementations. |
| **Unproven Completion Claims** (`"Tests should pass now"`, `"All fixed!"`) | **The Iron Law: No completion claims without fresh execution evidence.** | Unverified assertions introduce silent regressions and corrupt audit trails. |

---

## 2. Engine Architecture (Shino Native Review Engine)

The review engine runs on `pr_agent/algo/` with a Rust native core and Python orchestration:

- **Rust Native Acceleration** (`native_rust/` → `libshino_native.so` via `rust_accel.py`): ctypes wrapper around `libshino_native.so` with a pure-Python fallback. Exposes `shino_score_file` (Risk-Priority Sorting for large PRs), `shino_estimate_tokens`, `shino_repair_yaml` (Native YAML Auto-Repair, 9/9 patterns), and `shino_extract_defs` (Symbol/Def extraction). Every native function degrades to pure-Python when `libshino_native.so` is missing or a symbol cannot be resolved; all `char*` buffers are freed via `shino_free_str` inside `try/finally`.
- **Parallel GitHub I/O**: `ThreadPoolExecutor` with thread-local `requests.Session` for concurrent provider calls; `uvloop` + `httptools` for the HTTP server.
- **9Router 3-Tier Fail-Fast Routing** (`model_routing.py`): routes small PRs to a cheaper primary model. `retry_same_model_on_timeout = false` with `openai/newapi/...` fallback. Rules are checked in order; the first rule whose diff hunk/file limits the PR fits wins. Only routes the regular model type; weak/reasoning tier choices are respected deliberately.
- **`shino_context_enricher.py`**: Path-based Rules Discovery (`.shino/rules.yaml`, `.coderabbit.yaml`, `.greptile/rules.md`), Linked Issue Context (`Closes #N` → Acceptance Criteria for Axis 2, max 3 issues, parallel fetch), Developer Feedback Learning (`false positive` / `intentional` / resolved threads → suppression keywords), Calibrated Confidence Score (1/5 – 5/5) synced across PR Body and PR Review Summary, and Real Diff Summary (file stats, extension breakdown, top changed files, linked issues).
- **3-Layer Skeptic Filter** (`shino_filter_findings`): Diff-Line Grounding / Hallucination Filter, Overlap Deduplication, Chill/Balanced/Assertive Profile Noise Filter, and Developer Suppression.
- **Bảo mật & Tri-lingual** (`vi`, `ja`, `en` only): OWASP Top 10 / STRIDE, Two-Axis Isolated Audit, 12 Fowler Code Smells, 5-Question Test Gate, Anti-Hallucination & Prompt Injection Defense.

---

## 3. Four-Stage Review Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   STAGE 1: INTAKE & SURFACE DETECTION                  │
│  - Detect surface: Local Diff | Working Branch | Remote PR (gh/glab)   │
│  - Graph intelligence: CodeGraph exploration & GitNexus blast radius   │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   STAGE 2: TWO-AXIS ISOLATED AUDIT                     │
│  ┌─────────────────────────────────┐ ┌───────────────────────────────┐ │
│  │ Axis 1: Standards & Clean Code  │ │ Axis 2: Spec Conformance      │ │
│  │ - rules/standards.md compliance │ │ - Acceptance Criteria check   │ │
│  │ - 12 Fowler Code Smells         │ │ - Missing requirements audit  │ │
│  │ - 5-Question Test Gate quality  │ │ - Scope Creep identification │ │
│  └─────────────────────────────────┘ └───────────────────────────────┘ │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│               STAGE 3: SHINO REVIEW ENGINE & TRIAGE INTEGRATION        │
│  - Local CLI or Remote trigger (`@shino-review review`)                │
│  - 4-Tier Triage: Actionable | Informational | Addressed | False-Pos   │
│  - Confidence Scoring (1/5 - 5/5) & Camo SVG badge rendering           │
│  - Structured XML violation tags for AI coding subagents remediation   │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│            STAGE 4: REVIEW LOOP GOVERNANCE & RESOLUTION                │
│  - Max 3-Round Hard Stop (Escalate to Approach Review on round 3)      │
│  - Scoped commit review for Rounds 2 & 3 (/shino-review <commit-hash>) │
│  - Batch thread resolution via GitHub GraphQL Aliases                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Stage 1: Intake & Surface Detection

Identify review target surface and evaluate structural blast radius:

1. **Surface Classification**:
   - **Local Working Diff**: `git diff` (unstaged) + `git diff --cached` (staged) when working uncommitted.
   - **Branch / Head**: `git diff main...HEAD` for local branch comparison against baseline.
   - **Remote PR**: PR number provided (e.g. `/shino-review 142`). Inspect via `gh pr view <PR> --json title,body,baseRefName,headRefName` and `gh pr diff <PR>`.
   - **Specific Commit**: Commit hash provided (e.g. `/shino-review a1b2c3d`). Inspect via `git show <commit-hash>`.

2. **Code Intelligence Pre-flight**:
   - Query CodeGraph (`mcp__codegraph__codegraph_explore`): retrieve verbatim source, AST callers/callees, and dynamic-dispatch hops for touched symbols.
   - Upstream Impact Analysis (`mcp__gitnexus__impact`): analyze blast radius (`direction: "upstream"`) to discover upstream callers at depth d=1 (WILL BREAK), d=2 (LIKELY AFFECTED), d=3 (MAY NEED TESTING).
   - Pre-commit Diff Audit (`mcp__gitnexus__detect_changes`): verify that only intended execution flows are affected.

---

### Stage 2: Two-Axis Isolated Audit

To prevent **Single-Agent Conflation** (where style and formatting discussions crowd out domain logic defects and scope creep), run two isolated audits:

#### Axis 1: Standards, Clean Code & Test Quality
- **`rules/standards.md` Compliance**: Layer boundaries (Presentation, Application, Domain, Infrastructure), strict typing (`unknown` + parse over `any`), identifier unity (§5.1), structured error handling, zero secret exposure.
- **12 Fowler Code Smells Audit**:
  1. *Mysterious Name*: ambiguous identifiers hiding intent.
  2. *Duplicated Code*: identical/similar logic repeated across files.
  3. *Feature Envy*: method accessing external class data more than its own.
  4. *Data Clumps*: parameters/fields repeatedly passed together.
  5. *Primitive Obsession*: using raw strings/numbers instead of domain value objects.
  6. *Repeated Switches*: duplicate branching on the same type conditions.
  7. *Shotgun Surgery*: single change forcing scattered edits across many files.
  8. *Divergent Change*: single module altered for unrelated business reasons.
  9. *Speculative Generality*: premature interfaces, single-product factories, unrequested config.
  10. *Message Chains*: deep property navigation (`a.b.c.d()`).
  11. *Middle Man*: class merely delegating calls without value-add.
  12. *Refused Bequest*: subclass inheriting methods it rejects or throws on.
- **5-Question Test Quality Gate**:
  1. Pins behavior changed?
  2. Fails if behavior broke?
  3. Duplicates existing test?
  4. Fragile snapshot or private call-shape test?
  5. Mock-only tautology?

#### Axis 2: Spec Conformance, Acceptance Criteria & Scope Creep
- **AC Verification**: Map every requirement from the Issue/PR description to concrete code and tests.
- **Missing Requirements**: Identify unhandled edge cases, missing error paths, or absent business validations.
- **Scope Creep Audit**: Detect opportunistic refactoring, unrelated file modifications, and unrequested feature bloat outside the task boundaries.

---

### Stage 3: Shino Review Engine & Triage Integration

Integrates unified two-axis audit and triage patterns:

1. **Triggering Review**:
   - **Local Execution**: Run `/shino-review` or `/shino-review --loop` locally for instant feedback before pushing.
   - **Remote PR Trigger**: Post review comment via `mcp__github__add_issue_comment({ issue_number: PR, body: "@shino-review review" })` AND immediately launch asynchronous `Monitor` in the **exact same turn**:
     ```json
     Monitor({
       "command": "while true; do has_review=$(gh pr view <PR> --json comments,reviews --jq '[.comments[], .reviews[]] | any(.author.login == \"shino-review\" or (.body | test(\"shino-review|review\"; \"i\")))' 2>/dev/null); if [ \"$has_review\" = \"true\" ]; then echo \"SHINO_REVIEW_RECEIVED\"; break; fi; sleep 10; done",
       "description": "Wait for @shino-review review on PR #<PR>",
       "timeout_ms": 300000
     })
     ```

2. **Four-Tier Issue Triage**:
   - **Tier 1 — Actionable**: Defect, security risk, invariant violation, logic bug, broken test. Must be fixed immediately at root-cause choke point.
   - **Tier 2 — Informational**: Non-blocking architectural suggestion or question. Evaluate trade-offs; apply if beneficial or provide concise technical rationale.
   - **Tier 3 — Already Addressed**: Comment pointing to code already modified in later commits. Verify commit diff, mark resolved.
   - **Tier 4 — False Positive**: AI hallucination or invalid assumption. Refute politely with technical evidence, cite specifications/tests, and mark resolved.

3. **Confidence Scoring & Camo Badges**:
   - Every finding is rated from `1/5` (speculative/low certainty) to `5/5` (verified/reproducible invariant breach).
   - Render Shields.io / GitHub Camo SVG badges in PR review summaries:
     * Confidence: `![Confidence: 5/5](https://img.shields.io/badge/Confidence-5%2F5-brightgreen.svg)`
     * Triage Status: `![Actionable](https://img.shields.io/badge/Triage-Actionable-red.svg)`

4. **Structured XML Violation Tags for AI Coding Subagents**:
   When handoff to remediation subagents (`issue-resolver`, `frontend-developer`, etc.) occurs, findings must be formatted as machine-parsable XML:
   ```xml
   <review_findings>
     <violation tier="actionable" confidence="5/5" file="src/services/auth.ts" line="84">
       <rule>standards.md §5.1 Identifier Unity</rule>
       <defect>Variable user_id breaks canonical userId naming convention.</defect>
       <root_cause>Direct persistence entity leak into service domain layer.</root_cause>
       <choke_point>Map database row in repository layer before service ingestion.</choke_point>
     </violation>
   </review_findings>
   ```

---

### Stage 4: Review Loop Governance & Resolution

Prevents endless ping-pong loops between coder and reviewer:

1. **Max 3-Round Hard Stop**:
   - Review iterations are strictly limited to **3 rounds**.
   - If findings remain unresolved after Round 3: **HALT AUTOMATED PATCHING IMMEDIATELY**.
   - Trigger an **Approach Review (Architectural Redirection)**: re-evaluate the foundational design rather than continuing to stack fragile symptom patches.

2. **Scoped Commit Review (Round 2+)**:
   - Round 1 reviews the full PR diff.
   - Round 2 and Round 3 review **strictly the commit diff of the fix** (`/shino-review <commit-hash>`).
   - Forbid re-scanning untouched legacy code or reopening settled discussions (Frozen Review Contract).

3. **Batch Thread Resolution via GraphQL Aliases**:
   - When resolving multiple GitHub PR review threads, avoid sequential API calls.
   - Use batched GraphQL mutations with query aliases (`res1: resolveReviewThread(...)`, `res2: resolveReviewThread(...)`) via `gh api graphql` to resolve all addressed threads in a single round-trip.
   - Detailed query and mutation templates are documented in `references/graphql-queries.md`.

---

## 3. Slash Command Reference (`/shino-review`)

| Command | Target Scope | Use Case |
|---|---|---|
| `/shino-review` | Local diff / current branch | Pre-commit sanity check; scans uncommitted changes or working branch against main. |
| `/shino-review <PR_NUMBER>` | Remote PR | Pulls PR diff, comments, threads; triggers remote AI review or performs 2-axis audit. |
| `/shino-review <COMMIT_HASH>` | Single commit diff | Round 2 and Round 3 scoped review of applied fix; verifies fix efficacy and regression absence. |
| `/shino-review --loop` | Active branch / PR | Autonomous review-and-fix loop: runs 2-axis audit, generates XML violation tags, dispatches fixes, re-audits up to Max 3 rounds. |
| `/shino-review low` | Local diff or PR | Noise reduction mode: filters out low-confidence suggestions, displaying only findings with confidence >= 4/5. |

---

## 4. Remediation Workflow (`--loop` Mode)

When `/shino-review --loop` is invoked:

1. **Cycle 1 (Round 1 - Full Surface)**:
   - Execute Stage 1 (Intake) and Stage 2 (Two-Axis Audit).
   - Filter findings into 4-Tier Triage.
   - If zero Actionable findings: Report `STATUS: DONE` and exit.
2. **Autonomous Remediation**:
   - Package all Actionable findings into `<review_findings>` XML block.
   - Dispatch remediation tasks directly or via domain subagent (`issue-resolver`).
   - Fix defects strictly at root-cause choke points.
   - Execute native test command to prove Red-Green resolution.
   - Commit changes: `git commit -m "fix(review): resolve Round 1 actionable findings"`.
3. **Cycle 2 & 3 (Scoped Commits)**:
   - Run scoped review on the fix commit hash (`/shino-review <commit-hash>`).
   - Verify fix effectiveness; check for newly introduced regressions.
   - Batch resolve addressed review threads via GraphQL.
   - If clean: Report `STATUS: DONE`.
   - If unresolved after Round 3: **Hard Stop**. Emit `STATUS: DONE_WITH_CONCERNS` or `BLOCKED` with escalation report for Approach Review.

---

## 5. Detailed Reference Links

- **GraphQL Batch Queries & Mutations**: `references/graphql-queries.md`
- **Markdown Report Templates & Badges**: `references/review-templates.md`
