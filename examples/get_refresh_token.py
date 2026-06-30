"""refresh_token と profile_id を対話的に取得するヘルパー.

LWA セキュリティプロファイル作成後に一度だけ実行する。リージョンに応じた
正しい認可 URL / トークン URL / API エンドポイントを自動で使う。

前提:
  - 環境変数 ADS_CLIENT_ID / ADS_CLIENT_SECRET を設定済み
  - 任意で ADS_REGION（既定 FE=日本）, ADS_REDIRECT_URI（既定 https://localhost:443）
  - その LWA アプリに Amazon Ads API アクセスが「割り当て済み」であること
    （未割り当てだと認可画面でエラーになる）

実行:
  ADS_CLIENT_ID=... ADS_CLIENT_SECRET=... PYTHONPATH=src \
    python examples/get_refresh_token.py
"""

from __future__ import annotations

import os
import sys
import urllib.parse

import requests

# src をインポートパスに追加（直接実行できるように）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from zazoo_ads.config import (  # noqa: E402
    LWA_AUTH_URLS,
    LWA_TOKEN_URLS,
    REGION_ENDPOINTS,
)

SCOPE = "advertising::campaign_management"


def main() -> int:
    client_id = os.environ.get("ADS_CLIENT_ID")
    client_secret = os.environ.get("ADS_CLIENT_SECRET")
    region = os.environ.get("ADS_REGION", "FE")
    redirect_uri = os.environ.get("ADS_REDIRECT_URI", "https://localhost:443")

    if not client_id or not client_secret:
        print("ADS_CLIENT_ID と ADS_CLIENT_SECRET を環境変数に設定してください")
        return 1
    if region not in LWA_AUTH_URLS:
        print(f"未知のリージョン: {region}（NA/EU/FE のいずれか）")
        return 1

    # 1) 認可 URL を組み立てて表示
    params = {
        "client_id": client_id,
        "scope": SCOPE,
        "response_type": "code",
        "redirect_uri": redirect_uri,
    }
    auth_url = f"{LWA_AUTH_URLS[region]}?{urllib.parse.urlencode(params)}"
    print("\n=== ステップ1: 下の URL をブラウザで開いて『許可』 ===")
    print(auth_url)
    print(
        "\n許可後、ブラウザは "
        f"{redirect_uri}?code=... へリダイレクトします。"
        "\nページが表示されなくても、アドレスバーの URL 全体をコピーしてください。"
    )

    # 2) リダイレクト URL（または code）を貼り付けてもらう
    pasted = input("\nステップ2: リダイレクト先 URL（または code）を貼り付け: ").strip()
    code = _extract_code(pasted)
    if not code:
        print("code を取得できませんでした。URL を貼り直してください。")
        return 1

    # 3) code を refresh_token に交換
    print("\nステップ3: トークンを交換中…")
    token_resp = requests.post(
        LWA_TOKEN_URLS[region],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    if token_resp.status_code != 200:
        print(f"トークン交換に失敗 ({token_resp.status_code}): {token_resp.text}")
        return 1
    tokens = token_resp.json()
    refresh_token = tokens["refresh_token"]
    access_token = tokens["access_token"]
    print("✅ refresh_token を取得しました")

    # 4) profiles を取得して profile_id 候補を表示
    print("\nステップ4: プロファイル一覧を取得中…")
    prof_resp = requests.get(
        f"{REGION_ENDPOINTS[region]}/v2/profiles",
        headers={
            "Amazon-Advertising-API-ClientId": client_id,
            "Authorization": f"Bearer {access_token}",
        },
        timeout=30,
    )
    profiles = []
    if prof_resp.status_code == 200:
        profiles = prof_resp.json()
    else:
        print(
            f"⚠️ プロファイル取得に失敗 ({prof_resp.status_code}): {prof_resp.text}\n"
            "（Ads API アクセスがまだ割り当てられていない可能性があります）"
        )

    # 5) .env に貼る内容を出力
    print("\n=== .env に設定する値 ===")
    print(f"ADS_CLIENT_ID={client_id}")
    print("ADS_CLIENT_SECRET=（あなたのシークレット）")
    print(f"ADS_REFRESH_TOKEN={refresh_token}")
    print(f"ADS_REGION={region}")
    if profiles:
        print("\n--- プロファイル候補（ADS_PROFILE_ID に使う）---")
        for p in profiles:
            cc = p.get("countryCode")
            pid = p.get("profileId")
            ptype = p.get("accountInfo", {}).get("type")
            mark = " ← 日本" if cc == "JP" else ""
            print(f"  profileId={pid}  country={cc}  type={ptype}{mark}")
        jp = [p for p in profiles if p.get("countryCode") == "JP"]
        if jp:
            print(f"\nADS_PROFILE_ID={jp[0]['profileId']}  # 日本")
    return 0


def _extract_code(pasted: str) -> str | None:
    """貼り付けられた文字列から認可コードを取り出す."""
    if "code=" in pasted:
        query = urllib.parse.urlparse(pasted).query
        values = urllib.parse.parse_qs(query)
        if "code" in values:
            return values["code"][0]
        # URL でなく 'code=xxx' 断片の場合
        return pasted.split("code=", 1)[1].split("&", 1)[0]
    # コードだけを貼った場合
    return pasted or None


if __name__ == "__main__":
    raise SystemExit(main())
