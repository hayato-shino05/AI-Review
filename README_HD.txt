================================================================================
 HƯỚNG DẪN CẤU HÌNH VÀ SỬ DỤNG PR-AGENT TRÊN DEVBOX (TEST2)
================================================================================

1. ĐƯỜNG DẪN CẤU HÌNH:
   - File cấu hình API key: /opt/pr-agent/.secrets.toml
   (Nếu ở ngoài host Ubuntu: /opt/devbox/opt/pr-agent/.secrets.toml)

2. CẤU HÌNH AI PROVIDER:
   Mở file /opt/pr-agent/.secrets.toml và điền key:
   - Dùng OpenAI: [openai] key = sk-...
   - Dùng Anthropic/Claude: [anthropic] key = sk-ant-...
   - Dùng Gemini: [google_ai_studio] gemini_api_key = ...
   - Dùng mô hình khác qua LiteLLM (OpenRouter, DeepSeek, Ollama...): cấu hình phần tương ứng trong file.

3. HAI CÁCH SỬ DỤNG:

   CÁCH A: DÙNG TRỰC TIẾP QUA CLI (BÊN TRONG DEVBOX)
   - Vào devbox: devbox
   - Kiểm tra kết nối AI: pr-agent doctor
   - Yêu cầu review một PR bất kỳ:
     pr-agent --pr_url https://github.com/owner/repo/pull/123 review
   - Yêu cầu gợi ý code:
     pr-agent --pr_url https://github.com/owner/repo/pull/123 improve
   - Hỏi đáp về PR:
     pr-agent --pr_url https://github.com/owner/repo/pull/123 ask PR này thay đổi những gì?

   CÁCH B: TỰ ĐỘNG REVIEW TRÊN GITHUB (GITHUB APP WEBHOOK)
   - Service đã được tạo và chạy nền: pr-agent.service (Port nội bộ 3000)
   - Nginx cổng 443 đã forward endpoint webhook ra internet:
     URL Webhook: https://213.163.197.46/api/v1/github_webhooks
   - Khi tạo GitHub App trên GitHub:
     + Webhook URL: https://213.163.197.46/api/v1/github_webhooks
     + Webhook Secret: điền vào phần [github] webhook_secret trong .secrets.toml
     + Private Key (.pem): dán vào [github] private_key trong .secrets.toml
     + App ID: điền vào [github] app_id trong .secrets.toml
   - Xem log xử lý: journalctl -u pr-agent -f

================================================================================
