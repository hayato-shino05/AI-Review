---
name: shino-review
description: "Two-axis review protocol: Standards (12 Fowler Smells, 5-Question Test Gate) vs Spec Conformance (AC, Scope Creep), 4-tier triage (Actionable, Informational, Addressed, False Positive), evidence-labeled findings, review loop governance (Max 3 rounds, scoped commit review)."
version: 2.1.0
---

# Shino Review Protocol (Compressed for LLM Context)

## 1. Negative Anchoring Table (Review Anti-Habit Invariants)

| Bad Habit | Mandatory Invariant |
|---|---|
| Performative flattery ("Looks great!", "LGTM") | Refute-first adversarial stance; zero praise filler. |
| Endless re-review (>3 rounds, full re-scan) | Max 3-Round Hard Stop; Round 2+ reviews only the fix diff. |
| Scattered symptom patching | Pattern Grouping: fix once at shared root-cause choke point. |
| Re-flagging settled issues | Frozen Review Contract: Round 2+ verifies fix efficacy + regressions only. |
| Blind capitulation to feedback | Evaluate feedback technically; refute false positives with evidence. |
| Unproven completion claims | Iron Law: no claims without fresh execution evidence. |

## 2. Two-Axis Isolated Audit

Prevents single-agent conflation (style noise crowding out real defects):

**Axis 1 — Standards, Clean Code & Test Quality:**
- Layer boundaries (Presentation / Application / Domain / Infrastructure), strict typing, identifier unity, structured error handling, zero secret exposure.
- 12 Fowler Smells: Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.
- 5-Question Test Gate: pins behavior? fails if broke? duplicates? snapshot/private-shape? mock-only tautology?

**Axis 2 — Spec Conformance, Acceptance Criteria & Scope Creep:**
- Map every requirement from PR/Issue description to concrete code and tests.
- Flag missing acceptance criteria as REQUIREMENTS MISSING; unrelated changes as SCOPE CREEP.
- Verify claimed behavior against actual diff, never against the PR description alone.

## 3. Four-Tier Issue Triage

Classify EVERY finding with exactly one tier label:
- **[Actionable]**: defect, security risk, invariant violation, logic bug, broken test. Must fix at root cause.
- **[Informational]**: non-blocking suggestion or trade-off question. Apply if beneficial.
- **[Already-Addressed]**: code already fixed in later commits. Verify diff, mark resolved.
- **[False-Positive]**: hallucination or invalid assumption. Refute with concrete evidence.

## 4. Evidence-Labeling Mandate

Every technical claim inside a finding carries exactly one evidence label:
- `[measured]` — verified from the diff itself (line numbers, exact calls).
- `[inferred]` — grounded deduction from call patterns or invariants.
- `[guess]` — hypothesis; MUST state the assumption and what would confirm it.
Findings without labels, or with [guess] used for BLOCKING severity, are invalid output.

## 5. Review Loop Governance

- Round 1: full diff review. Round 2+: only the fix commit's patch. Never re-scan the whole PR.
- Max 3 rounds; beyond that, escalate to architectural review instead of patching.
- Every finding: `file_path:line_number` + concrete failure scenario (inputs/state -> crash/leak/corruption).
- Severity ladder: [BLOCKING] logic flaw/memory/security/race/contract break; [IMPORTANT] latent risk/perf/loose exceptions; [NIT] readability only when needed; [QUESTION] unclear intent needing justification.

## 6. Confidence Calibration

Score 1-5 calibrated: 5 = safe, zero outstanding findings; 4 = minor edge cases; 3 = architectural issues present; <=2 = not safe to merge (security or race outstanding). Deduct one level if any finding lacks evidence label.
