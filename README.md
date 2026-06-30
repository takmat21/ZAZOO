# ZAZOO

ブランド

---

## ZAZOO Amazon 広告運用 自動化ツール

ZAZOO ブランドの **Amazon スポンサープロダクト広告 (Sponsored Products)** の
運用を自動化する Python ツールです。Amazon Advertising API (v3) から
パフォーマンスレポートを取得し、ルールに基づいて入札・キーワード・予算を
自動最適化します。

### 主な機能

| 機能 | 内容 |
| --- | --- |
| **入札最適化** | 目標 ACoS を基準に、キーワードの入札を自動で引き上げ／引き下げ。売上ゼロの浪費キーワードは強めに引き下げ。 |
| **キーワード収集** | 検索語句レポートから、成果が出ているのに未登録の語句を完全一致で自動追加。 |
| **除外キーワード** | 費用を浪費しているのに成果が出ない検索語句を除外キーワードとして自動追加。 |
| **予算ペーシング** | キャンペーンの ACoS を見て日予算を自動で増減。 |
| **dry-run** | 既定では「提案のみ」を表示し、`--apply` を付けたときだけ実際に適用。 |

### アーキテクチャ

```
src/zazoo_ads/
├── config.py            # 認証情報(.env)とルール(YAML)の読み込み
├── models.py            # データモデル（ACoS/ROAS などの算出を含む）
├── automation.py        # ルール実行 → プラン生成 → 適用
├── cli.py               # コマンドラインインターフェース
├── api/
│   ├── auth.py          # LWA アクセストークンの取得・キャッシュ
│   ├── client.py        # API クライアント（リトライ・更新系操作）
│   └── reports.py       # レポート取得（作成→ポーリング→DL）
└── rules/               # 純粋ロジック（API 非依存・テスト容易）
    ├── bid_optimizer.py
    ├── keyword_harvester.py
    ├── negative_keywords.py
    └── budget_manager.py
```

ルール層 (`rules/`) は副作用のない純関数として実装しているため、API 認証
なしで単体テストできます。API 連携は `api/` に隔離しています。

### セットアップ

```bash
# 依存関係のインストール
pip install -r requirements.txt
# もしくは開発用も含めて
pip install -e ".[dev]"

# 認証情報を設定
cp .env.example .env
# .env を編集して Amazon Advertising API の資格情報を入力

# ルール設定を用意
cp config/rules.example.yaml config/rules.yaml
# config/rules.yaml をブランド方針に合わせて調整
```

必要な認証情報（`.env`）:

| 環境変数 | 説明 |
| --- | --- |
| `ADS_CLIENT_ID` | Login with Amazon アプリのクライアント ID |
| `ADS_CLIENT_SECRET` | 同 シークレット |
| `ADS_REFRESH_TOKEN` | OAuth で取得したリフレッシュトークン |
| `ADS_PROFILE_ID` | 対象プロファイル ID（出品アカウント×マーケットプレイス） |
| `ADS_REGION` | `NA` / `EU` / `FE`（日本は `FE`） |

> `.env` と `config/rules.yaml` は `.gitignore` 済み。認証情報は絶対に
> コミットしないでください。

### 使い方

```bash
# 直近 30 日のデータで「提案のみ」を表示（適用しない＝既定）
PYTHONPATH=src python -m zazoo_ads run --rules config/rules.yaml --dry-run

# 期間を指定
PYTHONPATH=src python -m zazoo_ads run --rules config/rules.yaml \
    --start 2026-06-01 --end 2026-06-30

# 提案を実際に適用する
PYTHONPATH=src python -m zazoo_ads run --rules config/rules.yaml --apply
```

`pip install -e .` 済みなら `zazoo-ads run ...` でも実行できます。

### オフラインデモ（認証情報不要）

サンプルデータでルールエンジンの動作を確認できます。

```bash
PYTHONPATH=src python examples/demo_offline.py
```

出力例:

```
=== 自動化プラン ===
入札変更 3 件 / 除外キーワード 1 件 / キーワード収集 1 件 / 予算変更 1 件

--- 入札変更 ---
  [ザズー リング] 80.00 → 68.00 (ACoS 80% > 目標 30% のため -15%)
  [ザズー ネックレス] 60.00 → 66.00 (ACoS 10% < 目標 30% のため +10%)
  ...
```

### ルール設定 (`config/rules.yaml`)

各ルールの閾値は YAML で調整します。詳細は
[`config/rules.example.yaml`](config/rules.example.yaml) を参照してください。
主な項目:

- `bid.target_acos` — 目標 ACoS（利益率に応じて設定）
- `bid.min_clicks` — 判定に必要な最小クリック数（ノイズ除去）
- `harvest.min_orders` / `harvest.max_acos` — キーワード収集の条件
- `negative.min_clicks` / `negative.min_cost` — 除外の条件
- `budget.*` — 予算増減の閾値と上下限

### テスト

```bash
python -m pytest -q
```

ルール層・設定・オーケストレーションをカバーする 35 件のテストが含まれます。

### 定期実行（例: cron）

毎朝 9 時に dry-run で提案をログ出力する例:

```cron
0 9 * * * cd /path/to/ZAZOO && PYTHONPATH=src python -m zazoo_ads run \
    --rules config/rules.yaml --dry-run >> logs/ads.log 2>&1
```

> 運用開始当初は `--dry-run` で提案内容を確認し、妥当性を見極めてから
> `--apply` に切り替えることを推奨します。

### 注意事項

- 本ツールは Sponsored Products v3 を対象としています。Sponsored Brands /
  Sponsored Display への拡張は `api/` と `rules/` に同様のモジュールを
  追加することで対応できます。
- 予算ペーシング (`adjust_budgets`) はキャンペーン一覧データを入力に取り
  ますが、現状の CLI ではキャンペーン取得を実装していないため、CLI 経由
  では予算変更は生成されません（ロジック・テスト・デモでは動作します）。
  キャンペーン一覧取得 API を `api/client.py` に追加すると有効化できます。
