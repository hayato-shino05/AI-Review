#!/bin/bash
cd /opt/AI-Review
source /opt/AI-Review/venv/bin/activate
export PORT=3000
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting PR-Agent GitHub App Webhook Server on port 3000..."
exec python3 -m pr_agent.servers.github_app
