# Amazon Advertising API 認証情報の取得手順（日本 / FE リージョン）

ZAZOO の Amazon 広告自動化ツールを動かすには、以下 4 つの認証情報を
`.env` に設定します。本書は **日本（FE リージョン）** を前提に取得手順を
まとめたものです。

| 環境変数 | 取得元 |
| --- | --- |
| `ADS_CLIENT_ID` | LWA セキュリティプロファイル（ウェブ設定） |
| `ADS_CLIENT_SECRET` | 同上 |
| `ADS_REFRESH_TOKEN` | OAuth 認可フロー |
| `ADS_PROFILE_ID` | Profiles API（`countryCode: "JP"`） |

リージョンは日本なので `ADS_REGION=FE` を設定します。

---

## ステップ 0: 前提条件

- 大口出品者（またはベンダー）の **Amazon 広告アカウント**があること
- スポンサー広告を**配信中**であること
- アカウント管理者権限を持つ Amazon アカウント

---

## ステップ 1: Amazon Ads API の利用申請（最重要・先にやる）

LWA アプリを作るだけでは API は叩けません。**先に / 並行して** Amazon Ads API
の利用申請が必要です。

1. [オンボーディング概要](https://advertising.amazon.com/API/docs/en-us/onboarding/overview) を開く
2. 「**2. Apply for API access**」から申請フォームを記入
   - 用途は「自社（ZAZOO）の広告を自動管理するため」＝ **Direct advertiser**
3. **承認は最大 1 営業日**
4. 承認後、「**3. Assign API access to an LwA application**」で、
   ステップ 2 で作る LWA アプリにアクセス権を**割り当て**る

> ⚠️ この割り当てが終わるまで、ステップ 4 の OAuth 認可画面はエラーになります
> （`apac.account.amazon.com/ap/oa` で「リクエストの処理中に問題が発生しました」等）。

---

## ステップ 2: LWA セキュリティプロファイル作成 → client_id / client_secret

1. [LWA コンソール](https://developer.amazon.com/settings/console/securityprofile) を開く
2. 「**セキュリティプロファイルを新規作成**」
   - 名前: 例 `ZAZOO Ads API`
   - 説明: 例 `ZAZOO 広告運用自動化ツール`
   - プライバシー規約同意書 URL: **実在する公開 URL**（自社サイト等）
3. 作成後、一覧 → 歯車 ⚙️ → **ウェブ設定（Web Settings）**
   - **クライアントID** → `ADS_CLIENT_ID`
   - **クライアントシークレット**（「シークレットを表示」）→ `ADS_CLIENT_SECRET`
4. 同画面の **許可された返信 URL** に `https://localhost:443` を追加して保存
   - 「許可されたオリジン」は空でよい（認可コードグラントを使うため）

> 🔐 シークレットは「パスワード級」。スクリーンショットやチャットで共有しない。
> 露出した場合は「シークレットのリセット（即時）」で再発行する。

---

## ステップ 3 & 4: refresh_token / profile_id の取得

付属の対話ヘルパーを使うのが最も確実です（リージョン別 URL を自動使用）。

```bash
ADS_CLIENT_ID=【クライアントID】 \
ADS_CLIENT_SECRET=【シークレット】 \
ADS_REGION=FE \
PYTHONPATH=src python examples/get_refresh_token.py
```

1. 表示される**認可 URL をブラウザで開く** → 広告アカウントの所有者でログイン → 「許可」
2. `https://localhost:443?code=...` にリダイレクトされる
   （ページが表示されなくても、**アドレスバーの URL 全体**をコピー）
3. ヘルパーに貼り付けると `refresh_token` を取得し、続けてプロファイル一覧を表示
4. `countryCode: "JP"` の `profileId` が `ADS_PROFILE_ID`

### 手動でやる場合（参考）

認可（ブラウザ）:

```
https://apac.account.amazon.com/ap/oa?client_id=【CLIENT_ID】&scope=advertising::campaign_management&response_type=code&redirect_uri=https://localhost:443
```

code → refresh_token（日本は `api.amazon.co.jp`）:

```bash
curl -X POST https://api.amazon.co.jp/auth/o2/token \
  -d "grant_type=authorization_code" -d "code=【code】" \
  -d "redirect_uri=https://localhost:443" \
  -d "client_id=【CLIENT_ID】" -d "client_secret=【CLIENT_SECRET】"
```

profile_id（日本は `advertising-api-fe.amazon.com`）:

```bash
curl https://advertising-api-fe.amazon.com/v2/profiles \
  -H "Amazon-Advertising-API-ClientId: 【CLIENT_ID】" \
  -H "Authorization: Bearer 【access_token】"
```

---

## リージョン別エンドポイント早見表

| 用途 | NA | EU | FE（日本） |
| --- | --- | --- | --- |
| 認可画面 | `www.amazon.com/ap/oa` | `eu.account.amazon.com/ap/oa` | `apac.account.amazon.com/ap/oa` |
| トークン交換 | `api.amazon.com` | `api.amazon.co.uk` | `api.amazon.co.jp` |
| 広告 API | `advertising-api.amazon.com` | `advertising-api-eu.amazon.com` | `advertising-api-fe.amazon.com` |

---

## よくあるエラー

| 症状 | 原因と対処 |
| --- | --- |
| 認可画面で「リクエストの処理中に問題が発生しました」 | Ads API アクセスが LWA アプリに**未割り当て**（ステップ 1 の Assign access が未完了）。承認・割り当て後に再試行。 |
| 認可画面で redirect_uri エラー | 認可 URL の `redirect_uri` が、ウェブ設定の「許可された返信 URL」と**完全一致**していない。 |
| トークン交換が `invalid_client` | リージョンの取り違え（日本なのに `api.amazon.com` を使う等）。FE は `api.amazon.co.jp`。 |
| profiles が 401/403 | access_token 失効、または Ads API 未割り当て。 |
