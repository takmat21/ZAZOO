"""保存済み refresh_token を使って profiles を取得し、JP の profile_id を .env に書き込む.

オンボーディング直後は profiles が空のことがある（反映待ち）。その場合は
時間をおいて再実行すればよい。ブラウザ認可のやり直しは不要。

実行:
  cd /home/user/ZAZOO && python3 examples/fetch_profiles.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

TOKEN_URLS = {
    "NA": "https://api.amazon.com/auth/o2/token",
    "EU": "https://api.amazon.co.uk/auth/o2/token",
    "FE": "https://api.amazon.co.jp/auth/o2/token",
}
API_ENDPOINTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",
}


def load_env() -> dict:
    env = {}
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def curl_json(args: list) -> dict:
    """curl を使って（プロキシ対応）JSON を取得する."""
    out = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"curl failed: {out.stderr}")
    return json.loads(out.stdout)


def main() -> int:
    env = load_env()
    cid = env.get("ADS_CLIENT_ID", "")
    csec = env.get("ADS_CLIENT_SECRET", "")
    rt = env.get("ADS_REFRESH_TOKEN", "")
    region = env.get("ADS_REGION", "FE")
    if not (cid and csec and rt) or rt.startswith("ここに"):
        print("ERROR: .env の client_id / client_secret / refresh_token が未設定です")
        return 1

    # 1) refresh_token -> access_token
    tok = curl_json([
        "curl", "-sS", "-X", "POST", TOKEN_URLS[region],
        "-d", "grant_type=refresh_token",
        "-d", f"refresh_token={rt}",
        "-d", f"client_id={cid}",
        "-d", f"client_secret={csec}",
    ])
    if "access_token" not in tok:
        print("ERROR: アクセストークン取得失敗:", tok)
        return 1
    at = tok["access_token"]
    print("access_token: OK")

    # 2) profiles
    profs = curl_json([
        "curl", "-sS", f"{API_ENDPOINTS[region]}/v2/profiles",
        "-H", f"Amazon-Advertising-API-ClientId: {cid}",
        "-H", f"Authorization: Bearer {at}",
    ])
    if not isinstance(profs, list):
        print("profiles 応答:", profs)
        return 1

    print(f"profiles 件数: {len(profs)}")
    for p in profs:
        ai = p.get("accountInfo", {})
        print(f"  profileId={p.get('profileId')} country={p.get('countryCode')} "
              f"type={ai.get('type')} name={ai.get('name')}")

    if not profs:
        print("\n⚠️ まだ profiles が空です（オンボーディング反映待ちの可能性）。"
              "\n   時間をおいて再実行してください: python3 examples/fetch_profiles.py")
        return 0

    jp = [p for p in profs if p.get("countryCode") == "JP"]
    pid = str((jp[0] if jp else profs[0])["profileId"])

    # 3) .env の ADS_PROFILE_ID を更新
    lines = open(ENV_PATH, encoding="utf-8").read().splitlines()
    done = False
    for i, ln in enumerate(lines):
        if re.match(r"^ADS_PROFILE_ID=", ln):
            lines[i] = f"ADS_PROFILE_ID={pid}"
            done = True
    if not done:
        lines.append(f"ADS_PROFILE_ID={pid}")
    open(ENV_PATH, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\n✅ ADS_PROFILE_ID={pid} を .env に保存しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
