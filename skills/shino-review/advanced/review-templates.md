# AI Review Report Templates & Formats (`review-templates.md`)

This reference defines standard Markdown report layouts, Camo / Shields.io SVG badges, structured XML violation tags, and AI coding subagent prompts.

---

## 1. Two-Axis Isolated Review Report Template

Use this template when outputting review results to PR comments, terminal output, or local summaries:

```markdown
# AI Code Review Report

**Target**: `[PR #<number> | branch: <name> | commit: <sha> | local diff]`
**Review Round**: `[Round 1 (Full Diff) | Round 2 (Scoped Commit) | Round 3 (Final Scoped)]`
**Blast Radius**: `[Upstream callers d=1: <count>, d=2: <count> | Risk: <LOW|MEDIUM|HIGH>]`

---

## Executive Summary & Triage Matrix

| Tier | Total | High Confidence (>= 4/5) | Low Confidence (< 4/5) |
|---|---|---|---|
| **Actionable** | `<count>` | `<count>` | `<count>` |
| **Informational** | `<count>` | `<count>` | `<count>` |
| **Already Addressed** | `<count>` | `<count>` | `<count>` |
| **False Positive** | `<count>` | `<count>` | `<count>` |

**Verdict**: `[PASSED | CHANGES_REQUIRED | APPROACH_REVIEW_ESCALATION]`

---

## Axis 1: Standards, Architecture & Clean Code

### Findings Summary
- Rules evaluated: `rules/standards.md`, 12 Fowler Code Smells, 5-Question Test Gate.

### Detailed Findings

#### 1. `[Defect Title]`
- **Coordinates**: `file_path:line_number`
- **Badges**: ![Actionable](https://img.shields.io/badge/Triage-Actionable-critical.svg) ![Confidence 5/5](https://img.shields.io/badge/Confidence-5%2F5-brightgreen.svg)
- **Violation Category**: `[12 Fowler Smell / rules/standards.md section / 5-Question Test Gate]`
- **Observable Defect**: `<Clear explanation of the invariant breach or failure mode>`
- **Root Cause & Shared Choke Point**:
  * Root Cause: `<Why this occurs at the design/data flow level>`
  * Shared Choke Point: `<The single upstream path to fix once across all callers>`
- **Suggested Fix**:
  ```language
  // Target fix at shared choke point
  ```

---

## Axis 2: Spec Conformance, Acceptance Criteria & Scope

### Acceptance Criteria Checklist
- [x] AC 1: `<Requirement description>` — *Verified in `<test_file>`*
- [ ] AC 2: `<Requirement description>` — *MISSING: `<reason>`*

### Missing Requirements & Unhandled Edge Cases
- **Missing Invariant**: `<e.g. Rate-limit header missing in 429 response>`
  * Impact: `<Client cannot determine backoff delay>`
  * Location: `src/middleware/rate-limiter.ts:35`

### Scope Creep Detection
- **Unrelated Modifications**:
  * `src/utils/legacy-formatter.ts`: Formatted lines 10-120 with no relation to task spec.
  * Recommendation: Revert opportunistic changes to preserve minimal clean diff.

---

## Next Steps & Loop Governance
- **Current Round**: Round `<N>` of 3.
- **Action Plan**:
  * [ ] Fix `<M>` actionable defects at shared choke points.
  * [ ] Re-run verification suite: `<test_command>`.
  * [ ] Commit fix and trigger Scoped Review: `/shino-review <fix-commit-hash>`.
```

---

## 2. Camo & Shields.io SVG Badges Format

Use standard shields.io SVG URLs in GitHub Markdown:

### Confidence Score Badges
| Score | Markdown Badge Syntax |
|---|---|
| **5/5** | `![Confidence 5/5](https://img.shields.io/badge/Confidence-5%2F5-brightgreen.svg)` |
| **4/5** | `![Confidence 4/5](https://img.shields.io/badge/Confidence-4%2F5-green.svg)` |
| **3/5** | `![Confidence 3/5](https://img.shields.io/badge/Confidence-3%2F5-yellow.svg)` |
| **2/5** | `![Confidence 2/5](https://img.shields.io/badge/Confidence-2%2F5-orange.svg)` |
| **1/5** | `![Confidence 1/5](https://img.shields.io/badge/Confidence-1%2F5-red.svg)` |

### Triage Tier Badges
| Tier | Markdown Badge Syntax |
|---|---|
| **Actionable** | `![Actionable](https://img.shields.io/badge/Triage-Actionable-critical.svg)` |
| **Informational** | `![Informational](https://img.shields.io/badge/Triage-Informational-blue.svg)` |
| **Already Addressed** | `![Addressed](https://img.shields.io/badge/Triage-Addressed-lightgrey.svg)` |
| **False Positive** | `![False Positive](https://img.shields.io/badge/Triage-False_Positive-inactive.svg)` |

### Review Round Badges
| Round | Markdown Badge Syntax |
|---|---|
| **Round 1** | `![Round 1](https://img.shields.io/badge/Round-1%20Full%20Diff-blue.svg)` |
| **Round 2** | `![Round 2](https://img.shields.io/badge/Round-2%20Scoped-yellow.svg)` |
| **Round 3** | `![Round 3](https://img.shields.io/badge/Round-3%20Final-orange.svg)` |

---

## 3. Structured XML Violation Tags (Subagent Handoff)

When delegating remediation to coding subagents (`issue-resolver`, `frontend-developer`, etc.), format actionable findings inside `<review_findings>` XML blocks:

```xml
<review_findings target_commit="a1b2c3d" round="1">
  <violation id="VIO-01" tier="actionable" confidence="5/5" file="src/services/billing.ts" line="112">
    <category>Fowler Smell: Shotgun Surgery</category>
    <rule>standards.md §5.1 Identifier Unity & Canonical Ownership</rule>
    <defect>Currency calculation uses binary floating-point arithmetic (number * 0.1).</defect>
    <root_cause>Direct mathematical operations on float primitives instead of minor unit integers.</root_cause>
    <choke_point>Encapsulate money math in MoneyValueObject class using integer cents.</choke_point>
    <remediation>
      Replace raw multiplication with Money.fromDollars(amount).multiply(0.1).toCents() at the domain boundary.
    </remediation>
  </violation>

  <violation id="VIO-02" tier="actionable" confidence="4/5" file="src/api/routes/orders.ts" line="45">
    <category>Spec Conformance: Missing Error Handling</category>
    <rule>standards.md §7.1 Structured Error Handling</rule>
    <defect>Catch block logs error to console and returns generic 500 without structured domain error envelope.</defect>
    <root_cause>Missing global exception mapping in route handler.</root_cause>
    <choke_point>Route error through standard formatErrorResponse() handler.</choke_point>
    <remediation>
      Invoke formatErrorResponse(err, res) to preserve request correlation ID and sanitization.
    </remediation>
  </violation>
</review_findings>
```

---

## 4. Remediation Prompt Template for AI Coding Subagents

When running `/shino-review --loop`, supply the following prompt to the delegated coding subagent:

```markdown
You are assigned to remediate Actionable code review findings.

### Review Findings XML:
[PASTE <review_findings> BLOCK HERE]

### Mandatory Execution Invariants:
1. **Root-Cause Choke Point Discipline**: Fix every defect once at its shared upstream choke point. Do NOT patch symptoms line-by-line across multiple callers.
2. **Scope Lock**: Confine modifications strictly to the files declared in the findings and their companion test files. Do NOT refactor neighboring code.
3. **Red-Green TDD Discipline**: Write or run a minimal reproduction test proving the defect before applying the fix. Re-run after fixing to prove resolution.
4. **Zero Performative Code**: Follow Ponytail YAGNI ladder. The shortest working diff that satisfies the invariant wins.
5. **No AI Filler Comments**: Do NOT add explanatory comments unless explaining non-obvious hidden constraints.

Execute the fixes, run the test suite, and report verified exit codes.
```
