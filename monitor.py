#!/usr/bin/env python3
import os
import sys
import time
import socket
import re
import subprocess
from datetime import datetime

LOG_FILE = '/opt/AI-Review/pr-agent.log'
SECRETS_FILE = '/opt/AI-Review/.secrets.toml'

def check_tcp(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except Exception:
        return False

def get_process_info():
    try:
        out = subprocess.check_output(['ps', '-eo', 'pid,%cpu,%mem,etime,cmd'], text=True)
        for line in out.splitlines():
            if 'pr_agent.servers.github_app' in line and 'grep' not in line:
                parts = line.strip().split(None, 4)
                return {
                    'pid': parts[0],
                    'cpu': parts[1] + '%',
                    'mem': parts[2] + '%',
                    'uptime': parts[3]
                }
    except Exception:
        pass
    return None

def get_config():
    config = {'model': 'Unknown', 'fallback': 'None', 'timeout': '60s', 'lang': 'vi'}
    try:
        if os.path.exists(SECRETS_FILE):
            with open(SECRETS_FILE, 'r') as f:
                c = f.read()
            m = re.search(r'model\s*=\s*"([^"]+)"', c)
            if m: config['model'] = m.group(1).replace('openai/openrouter/', '')
            m = re.search(r'fallback_models\s*=\s*\[(.*?)\]', c)
            if m and m.group(1).strip():
                config['fallback'] = m.group(1).strip().replace('"', '').replace('openai/openrouter/', '')
            m = re.search(r'ai_timeout\s*=\s*(\d+)', c)
            if m: config['timeout'] = m.group(1) + 's'
            m = re.search(r'response_language\s*=\s*"([^"]+)"', c)
            if m: config['lang'] = m.group(1)
    except Exception:
        pass
    return config

def get_recent_activity():
    events = []
    if not os.path.exists(LOG_FILE):
        return ['Waiting for incoming webhooks...']
    try:
        with open(LOG_FILE, 'r', errors='ignore') as f:
            lines = f.readlines()
        for line in reversed(lines):
            if 'Received a GitHub webhook' in line:
                events.append('Webhook received from GitHub')
            elif 'Handling request with event:' in line:
                ev = line.split('event:')[-1].strip().replace('\n', '').replace('"', '').replace('}', '')
                events.append(f'Event: {ev[:45]}')
            elif 'Reviewing PR:' in line:
                pr = line.split('Reviewing PR:')[-1].strip()
                events.append(f'Reviewing PR: {pr.split("/")[-1]}')
            elif 'Generating prediction with' in line:
                model = line.split('Generating prediction with')[-1].strip().replace('openai/openrouter/', '')
                events.append(f'Model Inference: {model[:35]}')
            elif 'Published a persistent review' in line or 'create_review' in line:
                events.append('PR Review published to GitHub!')
            elif 'ERROR' in line:
                err = line.split('ERROR')[-1].strip()[:40]
                events.append(f'Error: {err}')
            if len(events) >= 6:
                break
    except Exception:
        pass
    return events if events else ['Waiting for incoming webhooks...']

def draw_box():
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    p_info = get_process_info()
    p_3000 = check_tcp(3000)
    p_80 = check_tcp(80)
    p_20128 = check_tcp(20128)
    cfg = get_config()
    activity = get_recent_activity()

    buf = []
    buf.append('[H[2J')
    buf.append('[1;36m+----------------------------------------------------------------+[0m')
    buf.append(f'[1;36m|[0m [1;37mAI-REVIEW MONITOR & HEALTH[0m                    [1;33m{now_str}[0m [1;36m|[0m')
    buf.append('[1;36m+----------------------------------------------------------------+[0m')

    if p_info:
        status_line = f'[1;32mRUNNING[0m (PID: {p_info["pid"]}, CPU: {p_info["cpu"]}, MEM: {p_info["mem"]}, UP: {p_info["uptime"]})'
    else:
        status_line = '[1;31mSTOPPED[0m (pr-agent is down)'
    buf.append(f'[1;36m|[0m [1;34mService:[0m {status_line:<48} [1;36m|[0m')

    s_3000 = '[1;32mONLINE[0m' if p_3000 else '[1;31mOFFLINE[0m'
    s_80 = '[1;32mONLINE[0m' if p_80 else '[1;31mOFFLINE[0m'
    s_9r = '[1;32mONLINE[0m' if p_20128 else '[1;33mDOWN[0m'
    buf.append(f'[1;36m|[0m [1;34mPort 3000:[0m {s_3000:<10} [1;34mNginx (80):[0m {s_80:<10} [1;34m9Router:[0m {s_9r:<8}[1;36m|[0m')

    buf.append('[1;36m+----------------------------------------------------------------+[0m')
    buf.append(f'[1;36m|[0m [1;35mPrimary:[0m [1;37m{cfg["model"][:44]:<46}[0m [1;36m|[0m')
    buf.append(f'[1;36m|[0m [1;35mFallback:[0m {cfg["fallback"][:43]:<45} [1;36m|[0m')
    buf.append(f'[1;36m|[0m [1;35mAI Timeout:[0m {cfg["timeout"]}  [1;35mLanguage:[0m {cfg["lang"]}                       [1;36m|[0m')
    buf.append('[1;36m+----------------------------------------------------------------+[0m')
    buf.append('[1;36m|[0m [1;33mRECENT REVIEW ACTIVITY (Live Log Events):[0m                      [1;36m|[0m')

    for ev in activity[:6]:
        buf.append(f'[1;36m|[0m   {ev[:60]:<60} [1;36m|[0m')

    for _ in range(6 - len(activity[:6])):
        buf.append('[1;36m|[0m                                                                [1;36m|[0m')

    buf.append('[1;36m+----------------------------------------------------------------+[0m')
    buf.append('[1;36m|[0m [2mLogs stream in left pane | Press Ctrl+C to exit monitor[0m         [1;36m|[0m')
    buf.append('[1;36m+----------------------------------------------------------------+[0m')

    sys.stdout.write('\n'.join(buf) + '\n')
    sys.stdout.flush()

if __name__ == '__main__':
    try:
        while True:
            draw_box()
            time.sleep(2)
    except KeyboardInterrupt:
        print('\nExited monitor.')
