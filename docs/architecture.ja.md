# アーキテクチャ

Shino AI Review のシステム構成要素とデータ フローを説明します。

## コンポーネント構成

- **Webhook サーバー** (`pr_agent/servers/github_app.py`): FastAPI ルータ。GitHub Webhook を `/api/v1/github_webhooks` で受信し、`/retrigger` でレビューの再トリガーを処理します。`uvloop` と `httptools` を非同期 ランタイムとして使用します。
- **レビュー エンジン** (`pr_agent/algo/`): `rust_accel.py`、`model_routing.py`、`shino_context_enricher.py`、`git_patch_processing.py`、`review_merge.py` など。2 軸分離監査、4 段階トリアジ、信頼度スコアリング、XML 違反タグ生成を担います。
- **Rust ネイティブ コア** (`native_rust/src/lib.rs` → `libshino_native.so`): `shino_score_file`、`shino_estimate_tokens`、`shino_repair_yaml`、`shino_extract_defs` を C インターフェイスで公開。ctypes ラッパー経由で Python から呼び出し、ライブラリが利用できない場合は純粋 Python にフォールバックします。
- **9Router モデル ゲートウェイ** (`model_routing.py`): プルリクエストの差分ハンク数とファイル数に基づき、プライマリ モデルを選択。`retry_same_model_on_timeout = false` でフォール バック モデルへ切り替えます。
- **Git プロバイダ** (`pr_agent/git_providers/`): GitHub App、GitLab、Bitbucket、Azure DevOps などの Git ホスティング サービスとの連携。RS256 トークン認証と Webhook 署名検証を行います。
- **ヘルス モニター** (`monitor.py`): Herdr TUI ダッシュボード。サービス状態、ポート正常性、アクティブ モデル、最近のレビュー アクティビティを表示します。

## データ フロー

1. GitHub が Webhook イベントを `/api/v1/github_webhooks` に送信します。
2. Webhook サーバーが署名を検証し、バックグラウンド タスクとしてレビュー処理を開始します。
3. レビュー エンジンが差分を取得し、2 軸分離監査（基準 軸と仕様適合 軸）を実行します。
4. Rust ネイティブ コアがリスク優先順位スコアリングを行い、3 層懐疑フィルタが検出結果を精査します。
5. 9Router がプルリクエスト規模に応じたモデルで AI レビューを生成します。
6. 結果を 4 段階トリアジと信頼度スコア、Camo SVG バッジ、構造化 XML 違反タグと共に GitHub プルリクエスト レビューとして公開します。
7. `/retrigger` エンドポイントまたは `@shino-review review` コメントでレビューを再トリガーできます。
