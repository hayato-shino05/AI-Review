# Shino AI Review (PR-Agent Custom Engine)

Customized Qodo PR-Agent automated AI code reviewer, customized for tri-lingual review (`ja`, `vi`, `en`), GitHub App integration with RS256 token authentication, and pixel-perfect benchmark formatting (Greptile PR Body review block + Cubic XML violation review summaries).

## Features
- **3-Tier PR Body Updates**: Automatically updates GitHub PR descriptions with Human Overview, Summary by @shino-review, and Greptile Review Block (Confidence score, findings, Camo SVG badges, Important Files Changed table, and Mermaid diagram).
- **GitHub Pull Request Review & Inline Diff Comments**: Submits full GitHub Pull Request Reviews with inline line-by-line violation comments and `<details><summary>Prompt To Fix With AI</summary>`.
- **Interactive Re-trigger Button**: Visual SVG Retrigger badge with dark/light mode support linking to `/retrigger` webhook endpoint.
- **Natural Trigger Commands**: Supports `@shino-review`, `@shino-review review`, `@shino-review improve`, `@shino-review describe`, and natural language queries without leading slashes.
- **AI Gateway Integration**: Connects to local 9Router (`http://127.0.0.1:20128/v1`) using Nemotron-3-Ultra-550B.

## Quickstart
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run webhook server
python3 -m pr_agent.servers.github_app
```
