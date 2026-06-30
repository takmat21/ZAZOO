"""Amazon Advertising API クライアント.

認証ヘッダの付与、リトライ、Sponsored Products の管理オブジェクト
(キーワード入札・除外キーワード・予算) の更新を担う。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from ..config import ApiCredentials
from .auth import LwaTokenProvider

logger = logging.getLogger("zazoo_ads")

# Sponsored Products v3 のコンテンツタイプ
SP_KEYWORD_CONTENT_TYPE = "application/vnd.spKeyword.v3+json"
SP_NEGATIVE_KEYWORD_CONTENT_TYPE = "application/vnd.spNegativeKeyword.v3+json"
SP_CAMPAIGN_CONTENT_TYPE = "application/vnd.spCampaign.v3+json"


class AdsApiClient:
    """Sponsored Products v3 の更新系操作をまとめたクライアント."""

    def __init__(
        self,
        credentials: ApiCredentials,
        token_provider: Optional[LwaTokenProvider] = None,
        session: Optional[requests.Session] = None,
        max_retries: int = 3,
    ) -> None:
        self._credentials = credentials
        self._session = session or requests.Session()
        self._token = token_provider or LwaTokenProvider(credentials, self._session)
        self._max_retries = max_retries

    def _headers(self, content_type: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Amazon-Advertising-API-ClientId": self._credentials.client_id,
            "Amazon-Advertising-API-Scope": self._credentials.profile_id,
            "Authorization": f"Bearer {self._token.get_token()}",
        }
        if content_type:
            headers["Content-Type"] = content_type
            headers["Accept"] = content_type
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        content_type: Optional[str] = None,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        """認証付きリクエストを送る（指数バックオフでリトライ）."""
        url = f"{self._credentials.endpoint}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=self._headers(content_type),
                    json=json,
                    params=params,
                    timeout=60,
                )
            except requests.RequestException as exc:  # ネットワーク系
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("通信エラー (%s)。%ds 後に再試行", exc, wait)
                time.sleep(wait)
                continue

            # 401: トークン失効 → 強制更新して 1 度だけ即リトライ
            if resp.status_code == 401 and attempt == 0:
                logger.info("401 を受信。トークンを強制更新します")
                self._token.get_token(force_refresh=True)
                continue
            # 429 / 5xx: バックオフして再試行
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(
                    "%s を受信。%ds 後に再試行 (%d/%d)",
                    resp.status_code, wait, attempt + 1, self._max_retries,
                )
                time.sleep(wait)
                continue
            return resp

        if last_exc:
            raise RuntimeError(f"リクエスト失敗: {last_exc}") from last_exc
        raise RuntimeError("リクエストがリトライ上限に達しました")

    # --- 入札更新 ---------------------------------------------------------

    def update_keyword_bids(self, updates: list[dict[str, Any]]) -> dict[str, Any]:
        """キーワードの入札を一括更新する.

        updates 例: [{"keywordId": "123", "bid": 45.0}, ...]
        """
        resp = self.request(
            "PUT",
            "/sp/keywords",
            content_type=SP_KEYWORD_CONTENT_TYPE,
            json={"keywords": updates},
        )
        resp.raise_for_status()
        return resp.json()

    # --- 除外キーワード追加 ----------------------------------------------

    def create_negative_keywords(
        self, negatives: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """除外キーワードを一括作成する.

        negatives 例: [{"campaignId": "..", "adGroupId": "..",
                        "keywordText": "..", "matchType": "NEGATIVE_EXACT",
                        "state": "ENABLED"}, ...]
        """
        resp = self.request(
            "POST",
            "/sp/negativeKeywords",
            content_type=SP_NEGATIVE_KEYWORD_CONTENT_TYPE,
            json={"negativeKeywords": negatives},
        )
        resp.raise_for_status()
        return resp.json()

    # --- キーワード追加（収集） ------------------------------------------

    def create_keywords(self, keywords: list[dict[str, Any]]) -> dict[str, Any]:
        """新規キーワードを一括作成する."""
        resp = self.request(
            "POST",
            "/sp/keywords",
            content_type=SP_KEYWORD_CONTENT_TYPE,
            json={"keywords": keywords},
        )
        resp.raise_for_status()
        return resp.json()

    # --- 予算更新 ---------------------------------------------------------

    def update_campaign_budgets(
        self, updates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """キャンペーンの日予算を一括更新する.

        updates 例: [{"campaignId": "..", "budget": {"budget": 3000,
                      "budgetType": "DAILY"}}, ...]
        """
        resp = self.request(
            "PUT",
            "/sp/campaigns",
            content_type=SP_CAMPAIGN_CONTENT_TYPE,
            json={"campaigns": updates},
        )
        resp.raise_for_status()
        return resp.json()
