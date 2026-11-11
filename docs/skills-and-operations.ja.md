# スキルと運用

shino-review スキルの構成と、Shino AI Review の日常運用手順を説明します。

## shino-review スキル

スキルは `/opt/AI-Review/skills/shino-review/` に配置されます。

- `SKILL.md`: スキル定義。`/shino-review` スラッシュ コマンドの説明、2 軸分離監査、4 段階トリアジ、レビュー ループ ガバナンス、コマンド リファレンス、修復ワークフロー（`--loop` モード）を定義します。
- `references/review-templates.md`: Markdown レポート テンプレート、Camo / Shields.io SVG バッジ形式、構造化 XML 違反タグ、AI コーディング サブエージェント向け修復プロンプト テンプレート。
- `references/graphql-queries.md`: GitHub プルリクエスト レビュー スレッドの取得、単一スレッド解決、スレッドへの返信、エイリアスを用いた一括スレッド解決の GraphQL クエリと変換。

スキル キャッシュは `node tools/sync-skills.js` で再インデックス化します。

## 運用手順

### サービスの起動と停止

```bash
sudo systemctl start pr-agent
sudo systemctl stop pr-agent
sudo systemctl restart pr-agent
sudo systemctl status pr-agent
```

### ログの確認

```bash
sudo journalctl -u pr-agent -f
```

レビュー ログは `/opt/AI-Review/pr-agent.log` に出力されます。

### ヘルス モニターの実行

```bash
python3 monitor.py
```

ポート 3000、nginx（ポート 80）、9Router（ポート 20128）の正常性と、サービスの稼働状態をリアルタイムで確認できます。

### レビューの再トリガー

プルリクエストに `@shino-review review` とコメントするか、`/retrigger?repo=<owner>/<repo>&pr=<PR_NUMBER>` にアクセスします。

### 設定の変更

`.secrets.toml` を編集してモデル、フォールバック モデル、タイムアウト、応答言語、GitHub App 認証情報を変更します。変更後は `pr-agent` サービスを再起動して反映させます。

### Rust ネイティブ コアの再ビルド

`native_rust/src/lib.rs` を変更した場合は、次のコマンドで再ビルドします。

```bash
cd native_rust
cargo build --release
cd ..
```

ビルド成果物は `target/release/libshino_native.so` に出力され、`rust_accel.py` から読み込まれます。
