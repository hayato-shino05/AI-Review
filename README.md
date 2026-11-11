# Shino AI Review (PR-Agent Custom Engine)

Customized Qodo PR-Agent automated AI code reviewer, customized for tri-lingual review (`ja`, `vi`, `en`), GitHub App integration with RS256 token authentication, and pixel-perfect benchmark formatting (Greptile PR Body review block + Cubic XML violation review summaries).

## Overview

Shino AI Review is a GitHub App webhook server built on FastAPI with `uvloop`/`httptools`, backed by a Rust native core (`libshino_native.so`) and a 9Router model gateway. It reviews pull requests using a two-axis isolated audit (Standards vs Spec Conformance), a 3-layer skeptic filter, path-based rules discovery, linked issue context, calibrated confidence scoring, and large-PR risk-priority chunking. Reviews are published as persistent GitHub PR reviews with inline comments and an interactive retrigger badge.

## Architecture

- **FastAPI + uvloop/httptools**: async webhook server serving GitHub webhooks at `/api/v1/github_webhooks` and the `/retrigger` endpoint, run under gunicorn on port 3000 and proxied by nginx on port 80.
- **Rust Native Core** (`native_rust/` → `libshino_native.so` via `rust_accel.py`): ctypes wrapper with pure-Python fallback. Exposes `shino_score_file` (risk-priority scoring), `shino_estimate_tokens`, `shino_repair_yaml` (native YAML auto-repair), and `shino_extract_defs` (symbol/definition extraction).
- **9Router** (`model_routing.py`): 3-tier fail-fast model routing. `retry_same_model_on_timeout = false` with `openai/newapi/...` fallback; routes small PRs to a cheaper primary model based on diff hunk/file limits.
- **Context Enrichment** (`shino_context_enricher.py`): path-based rules discovery (`.shino/rules.yaml`, `.coderabbit.yaml`, `.greptile/rules.md`), linked issue context (`Closes #N` → acceptance criteria), developer feedback learning (false positive / intentional suppression), calibrated confidence score (1/5 – 5/5), and real diff summary.
- **3-Layer Skeptic Filter**: diff-line grounding / hallucination filter, overlap deduplication, chill/balanced/assertive profile noise filter, and developer suppression.
- **Herdr TUI Monitor** (`monitor.py`): live terminal dashboard showing service status, port health (3000/80/20128), active model, timeout, language, and recent review activity streamed from `pr-agent.log`.

## Core Features

- **Two-Axis Isolated Audit**: Axis 1 checks standards/clean code (12 Fowler Code Smells, 5-Question Test Gate); Axis 2 checks spec conformance (acceptance criteria, missing requirements, scope creep).
- **4-Tier Triage**: Actionable, Informational, Already Addressed, False Positive, each with confidence scoring (1/5 – 5/5) and Camo SVG badges.
- **Structured XML Violation Tags**: machine-parsable `<review_findings>` blocks for AI coding subagent remediation handoff.
- **Review Loop Governance**: max 3 rounds hard stop, scoped commit review from round 2 onwards, batch review thread resolution via GitHub GraphQL aliases.
- **Large PR Risk-Priority Chunking**: Rust-native `shino_score_file` sorts files by risk so high-risk files are reviewed first.
- **Interactive Re-trigger Button**: SVG retrigger badge (dark/light mode) linking to `/retrigger` webhook endpoint.
- **Tri-lingual Review**: `vi`, `ja`, `en` only.
- **GitHub App Auth**: RS256 token authentication via `private-key.pem`, webhook secret, app ID.

## Directory Structure

```
/opt/AI-Review/
├── pr_agent/
│   ├── algo/              # shino review engine: rust_accel, model_routing, shino_context_enricher, git_patch_processing, review_merge, ...
│   ├── servers/           # webhook servers: github_app.py (FastAPI + /retrigger), gunicorn_config.py, ...
│   ├── agent/             # PRAgent orchestration
│   ├── git_providers/     # GitHub/GitLab/Bitbucket/Azure DevOps providers
│   └── ...
├── native_rust/           # Rust native core (Cargo.toml, src/lib.rs, target/release/libshino_native.so)
├── skills/shino-review/   # shino-review skill: SKILL.md + references/
├── monitor.py             # Herdr TUI health dashboard
├── .secrets.toml          # runtime config (model, fallbacks, timeouts, GitHub app keys)
├── requirements.txt       # Python dependencies
└── README.md              # this file
```

## Installation & Running

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build the Rust native core
cd native_rust
cargo build --release
cd ..

# Configure runtime
# Edit .secrets.toml with model, fallback models, timeout, language, and GitHub App credentials.
# Never commit real API keys or private keys.

# Run the webhook server
export PORT=3000
python3 -m pr_agent.servers.github_app
```

### systemd service

The service runs as `pr-agent.service` (enabled):

```ini
[Unit]
Description=Qodo PR-Agent Webhook Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/chroot /opt/devbox /bin/bash -c "cd /opt/AI-Review && source venv/bin/activate && export PORT=3000 && exec python3 -m pr_agent.servers.github_app"
Restart=always
RestartSec=5
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

Manage it with:

```bash
sudo systemctl start pr-agent
sudo systemctl status pr-agent
sudo journalctl -u pr-agent -f
```

### Health monitor

Run the Herdr TUI monitor for live health status:

```bash
python3 monitor.py
```

The dashboard shows service running state (PID, CPU, memory, uptime), port 3000 / nginx 80 / 9Router 20128 health, active model, fallback, AI timeout, language, and recent review activity from `pr-agent.log`.

### Re-trigger a review

Post a review comment with `@shino-review review` on a PR, or open the `/retrigger` webhook endpoint:

```text
/retrigger?repo=<owner>/<repo>&pr=<PR_NUMBER>
```

The retrigger button in the PR review summary (dark/light SVG badge) links to this endpoint.

## Configuration (`.secrets.toml`)

Sample structure (do not store real API keys or private keys here):

```toml
[config]
ai_timeout = 60
response_language = "vi"
model = "openai/openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
fallback_models = ["openai/openrouter/nvidia/nemotron-3.5-super-vl:free", "openai/newapi/nvidia/nemotron-3.5-super-vl-120b-a12b"]
custom_model_max_tokens = 32000
retry_same_model_on_timeout = false
max_skills_tokens = 3500

[openai]
key = "<REDACTED>"
api_base = "http://127.0.0.1:20128/v1"

[github]
deployment_type = "app"
app_id = 5611054
webhook_secret = "<REDACTED>"
user_token = ""
private_key = """
-----BEGIN RSA PRIVATE KEY-----
<REDACTED>
-----END RSA PRIVATE KEY-----
"""

[pr_reviewer]
inline_key_issues = true
persistent_inline_comments = true
final_update_message = false
enable_large_pr_chunking = true
max_number_of_calls = 5
num_max_findings = 6

[skills]
enabled = true
paths = ["/opt/AI-Review/skills", "skills"]
max_skills_tokens = 8000
```

Replace `<REDACTED>` values with actual credentials at runtime only. Never commit real keys.
