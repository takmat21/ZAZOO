"""設定の読み込み.

API 認証情報は環境変数（.env）から、ルールの閾値は YAML から読み込む。
認証情報は決してリポジトリにコミットしないこと（.env.example を参照）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml


# Amazon Advertising API のリージョン別エンドポイント
REGION_ENDPOINTS = {
    "NA": "https://advertising-api.amazon.com",
    "EU": "https://advertising-api-eu.amazon.com",
    "FE": "https://advertising-api-fe.amazon.com",  # 日本を含む極東リージョン
}

# Login with Amazon (LWA) のトークン交換エンドポイント（リージョン別）
# 注意: アカウントの所属リージョンに合ったドメインを使わないと認証に失敗する。
LWA_TOKEN_URLS = {
    "NA": "https://api.amazon.com/auth/o2/token",
    "EU": "https://api.amazon.co.uk/auth/o2/token",
    "FE": "https://api.amazon.co.jp/auth/o2/token",  # 日本
}

# OAuth 認可（ユーザーがログイン・許可する）画面のエンドポイント（リージョン別）
LWA_AUTH_URLS = {
    "NA": "https://www.amazon.com/ap/oa",
    "EU": "https://eu.account.amazon.com/ap/oa",
    "FE": "https://apac.account.amazon.com/ap/oa",  # 日本・極東
}

# 後方互換のためのエイリアス（既定リージョン NA のトークン URL）
LWA_TOKEN_URL = LWA_TOKEN_URLS["NA"]


@dataclass
class ApiCredentials:
    """Amazon Advertising API の認証情報."""

    client_id: str
    client_secret: str
    refresh_token: str
    profile_id: str
    region: str = "FE"

    def _require_region(self) -> str:
        if self.region not in REGION_ENDPOINTS:
            raise ValueError(
                f"未知のリージョン: {self.region}. "
                f"利用可能: {', '.join(REGION_ENDPOINTS)}"
            )
        return self.region

    @property
    def endpoint(self) -> str:
        """広告 API のエンドポイント（リージョン別）."""
        return REGION_ENDPOINTS[self._require_region()]

    @property
    def lwa_token_url(self) -> str:
        """LWA トークン交換エンドポイント（リージョン別）."""
        return LWA_TOKEN_URLS[self._require_region()]

    @property
    def lwa_auth_url(self) -> str:
        """OAuth 認可画面のエンドポイント（リージョン別）."""
        return LWA_AUTH_URLS[self._require_region()]

    @classmethod
    def from_env(cls) -> "ApiCredentials":
        """環境変数から認証情報を読み込む.

        必要な環境変数:
          ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN, ADS_PROFILE_ID
        任意:
          ADS_REGION (既定: FE)
        """
        required = {
            "ADS_CLIENT_ID": "client_id",
            "ADS_CLIENT_SECRET": "client_secret",
            "ADS_REFRESH_TOKEN": "refresh_token",
            "ADS_PROFILE_ID": "profile_id",
        }
        values: dict[str, str] = {}
        missing: list[str] = []
        for env_name, attr in required.items():
            val = os.environ.get(env_name)
            if not val:
                missing.append(env_name)
            else:
                values[attr] = val
        if missing:
            raise RuntimeError(
                "認証情報の環境変数が不足しています: " + ", ".join(missing)
            )
        return cls(region=os.environ.get("ADS_REGION", "FE"), **values)


@dataclass
class BidRules:
    """入札最適化のルール."""

    target_acos: float = 0.30          # 目標 ACoS (30%)
    min_clicks: int = 10               # 判定に必要な最小クリック数
    bid_up_step: float = 0.10          # 引き上げ率 (+10%)
    bid_down_step: float = 0.15        # 引き下げ率 (-15%)
    max_bid: float = 200.0             # 入札上限
    min_bid: float = 10.0              # 入札下限 (JP の SP は 2 円〜だが安全側に)
    zero_sale_clicks: int = 15         # 売上 0 で引き下げ対象とするクリック数


@dataclass
class HarvestRules:
    """キーワード収集のルール."""

    min_orders: int = 2                # 収集対象とする最小注文数
    max_acos: float = 0.30             # 収集対象とする最大 ACoS
    default_match_type: str = "EXACT"
    bid_multiplier: float = 1.0        # 元の cost/click を基準にした入札倍率


@dataclass
class NegativeRules:
    """除外キーワードのルール."""

    min_clicks: int = 15               # 除外判定に必要な最小クリック数
    max_orders: int = 0                # この注文数以下なら除外候補
    min_cost: float = 100.0            # この費用以上を浪費していれば除外候補
    default_match_type: str = "EXACT"


@dataclass
class BudgetRules:
    """予算ペーシングのルール."""

    enabled: bool = True
    increase_when_acos_below: float = 0.20   # 好調 (ACoS が低い) 時に増額
    increase_step: float = 0.20              # 増額率 (+20%)
    decrease_when_acos_above: float = 0.50   # 不調時に減額
    decrease_step: float = 0.20              # 減額率 (-20%)
    max_daily_budget: float = 50000.0
    min_daily_budget: float = 500.0
    min_cost: float = 500.0                  # 判定に必要な最小消化額


@dataclass
class RulesConfig:
    """全ルールの束ね."""

    bid: BidRules = field(default_factory=BidRules)
    harvest: HarvestRules = field(default_factory=HarvestRules)
    negative: NegativeRules = field(default_factory=NegativeRules)
    budget: BudgetRules = field(default_factory=BudgetRules)

    @classmethod
    def from_yaml(cls, path: str) -> "RulesConfig":
        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RulesConfig":
        def build(section_cls, key):
            section = data.get(key) or {}
            valid = {f for f in section_cls.__dataclass_fields__}
            unknown = set(section) - valid
            if unknown:
                raise ValueError(
                    f"設定 '{key}' に未知のキー: {', '.join(sorted(unknown))}"
                )
            return section_cls(**section)

        return cls(
            bid=build(BidRules, "bid"),
            harvest=build(HarvestRules, "harvest"),
            negative=build(NegativeRules, "negative"),
            budget=build(BudgetRules, "budget"),
        )
