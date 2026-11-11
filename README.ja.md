# Shino AI Review（PR-Agent カスタム エンジン）

Qodo PR-Agent をカスタマイズした自動 AI コード レビューです。`ja`、`vi`、`en` の 3 か国語レビュー、GitHub App と RS256 トークン認証、Greptile PR 本文レビュー ブロックと Cubic XML 違反レビュー要約によるベンチマーク形式の出力をサポートします。

## INDEX

- [概要](#概要)
- [アーキテクチャ](#アーキテクチャ)
- [主な機能](#主な機能)
- [ディレクトリ構造](#ディレクトリ構造)
- [インストールと実行](#インストールと実行)
- [systemd サービス](#systemd-サービス)
- [ヘルス モニター](#ヘルス-モニター)
- [レビューの再トリガー](#レビューの再トリガー)
- [設定（.secrets.toml）](#設定-secretstoml)

## 概要

Shino AI Review は、FastAPI と `uvloop`/`httptools` で構築した GitHub App Webhook サーバーです。Rust ネイティブ コア（`libshino_native.so`）と 9Router モデル ゲートウェイをバックエンドに持ちます。プルリクエストを「基準」と「仕様適合」の 2 軸で分離監査し、3 層懐疑フィルタ、パスベース ルール検出、リンクされた Issue コンテキスト、校正済み信頼度スコア、大規模 PR のリスク優先順位チャンク処理を用いてレビューします。レビュー結果は、持続的な GitHub プルリクエスト レビューとしてインライン コメントとインタラクティブな再トリガー バッジと共に公開されます。

## アーキテクチャ

- **FastAPI + uvloop/httptools**: 非同期 Webhook サーバー。GitHub Webhook を `/api/v1/github_webhooks` で受け、`/retrigger` エンドポイントを提供します。ポート 3000 で gunicorn が動作し、nginx がポート 80 でプロキシします。
- **Rust ネイティブ コア**（`native_rust/` → `libshino_native.so` 経由で `rust_accel.py`）: ctypes ラッパーで純粋 Python フォールバックを備えます。`shino_score_file`（リスク優先順位スコアリング）、`shino_estimate_tokens`、`shino_repair_yaml`（ネイティブ YAML 自動修復）、`shino_extract_defs`（シンボル/定義抽出）を公開します。
- **9Router**（`model_routing.py`）: 3 層フォール バック モデル ルーティング。`retry_same_model_on_timeout = false` と `openai/newapi/...` フォールバック。差分ハンク/ファイル数の制限に基づき、小規模 PR を安価なプライマリ モデルにルーティングします。
- **コンテキスト エンリッチメント**（`shino_context_enricher.py`）: パスベース ルール検出（`.shino/rules.yaml`、`.coderabbit.yaml`、`.greptile/rules.md`）、リンクされた Issue コンテキスト（`Closes #N` → 受容基準）、開発者フィードバック学習（誤検出 / 意図的抑制）、校正済み信頼度スコア（1/5 から 5/5 まで）、実際の差分サマリ。
- **3 層懐疑フィルタ**: 差分ライン接地 / ハルシネーション フィルタ、重複排除、Chill/Balanced/Assertive プロファイル ノイズ フィルタ、開発者抑制。

## 主な機能

- **2 軸分離監査**: 軸 1 で基準/クリーン コード（12 の Fowler コード臭、5 問テスト ゲート）を確認。軸 2 で仕様適合（受容基準、未処理要件、スコープ クリープ）を確認します。
- **4 段階トリアジ**: 実行可能、情報提供、既に対応済み、誤検出。各項目に信頼度スコア（1/5 から 5/5 まで）と Camo SVG バッジを付与します。
- **構造化 XML 違反タグ**: AI コーディング サブエージェントへの修復引き継ぎ用、機械解釈可能な `<review_findings>` ブロック。
- **レビュー ループ ガバナンス**: 最大 3 ラウンドのハード ストップ、ラウンド 2 以降はスコープ化されたコミット レビュー、GitHub GraphQL エイリアスによるレビュー スレッドの一括解決。
- **大規模 PR のリスク優先順位チャンク処理**: Rust ネイティブ `shino_score_file` でファイルをリスク順にソートし、リスクの高いファイルを先にレビューします。
- **インタラクティブな再トリガー バッジ**: ダーク/ライト モード対応の SVG 再トリガー バッジ。`/retrigger` Webhook エンドポイントにリンクします。
- **3 か国語レビュー**: `vi`、`ja`、`en` のみ。
- **GitHub App 認証**: `private-key.pem` による RS256 トークン認証。

## ディレクトリ構造

```
/opt/AI-Review/
├── pr_agent/
│   ├── algo/              # shino レビュー エンジン: rust_accel、model_routing、shino_context_enricher、git_patch_processing、review_merge など
│   ├── servers/           # Webhook サーバー: github_app.py（FastAPI + /retrigger）、gunicorn_config.py など
│   ├── agent/             # PRAgent オーケストレーション
│   ├── git_providers/     # GitHub/GitLab/Bitbucket/Azure DevOps プロバイダ
│   └── ...
├── native_rust/           # Rust ネイティブ コア（Cargo.toml、src/lib.rs、target/release/libshino_native.so）
├── skills/shino-review/   # shino-review スキル: SKILL.md + references/
├── monitor.py             # Herdr TUI ヘルス ダッシュボード
├── .secrets.toml          # ランタイム設定（モデル、フォールバック、タイムアウト、言語、GitHub App 認証情報）
├── requirements.txt       # Python 依存関係
└── README.md              # このファイル
```

## インストールと実行

```bash
# 仮想環境を作成して有効化する
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Rust ネイティブ コアをビルドする
cd native_rust
cargo build --release
cd ..

# ランタイムを設定する
# .secrets.toml を編集し、モデル、フォールバック モデル、タイムアウト、言語、GitHub App 認証情報を設定する。
# 実際の API キーや秘密鍵はコミットしない。

# Webhook サーバーを実行する
export PORT=3000
python3 -m pr_agent.servers.github_app
```

### systemd サービス

`pr-agent.service`（有効化済み）として実行されます。

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

次のコマンドで管理します。

```bash
sudo systemctl start pr-agent
sudo systemctl status pr-agent
sudo journalctl -u pr-agent -f
```

### ヘルス モニター

`monitor.py` で Herdr TUI ヘルス ダッシュボードを実行します。

```bash
python3 monitor.py
```

ダッシュボードはサービス実行状態（PID、CPU、メモリ、稼働時間）、ポート 3000 / nginx 80 / 9Router 20128 の正常性、アクティブ モデル、フォールバック、AI タイムアウト、言語、および `pr-agent.log` からの最近のレビュー アクティビティを表示します。

### レビューの再トリガー

PR にレビュー コメント `@shino-review review` を投稿するか、`/retrigger` Webhook エンドポイントを開きます。

```text
/retrigger?repo=<owner>/<repo>&pr=<PR_NUMBER>
```

PR レビュー概要の再トリガー バッジ（ダーク/ライト SVG バッジ）がこのエンドポイントにリンクします。

## 設定（.secrets.toml）

構造のサンプル（実際の API キーや秘密鍵はここに保存しない）:

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

`<REDACTED>` はランタイム時に実際の値に置き換えます。実際のキーはコミットしないでください。
