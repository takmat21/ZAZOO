"""Login with Amazon (LWA) のアクセストークン管理.

リフレッシュトークンからアクセストークンを取得し、期限が切れるまで
キャッシュする。アクセストークンは通常 1 時間で失効する。
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from ..config import ApiCredentials

logger = logging.getLogger("zazoo_ads")


class LwaTokenProvider:
    """アクセストークンを取得・キャッシュする."""

    # 失効直前の更新を避けるためのマージン（秒）
    _EXPIRY_MARGIN = 60

    def __init__(
        self,
        credentials: ApiCredentials,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._credentials = credentials
        self._session = session or requests.Session()
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self, *, force_refresh: bool = False) -> str:
        """有効なアクセストークンを返す（必要なら更新）."""
        now = time.time()
        if (
            not force_refresh
            and self._access_token is not None
            and now < self._expires_at - self._EXPIRY_MARGIN
        ):
            return self._access_token
        return self._refresh()

    def _refresh(self) -> str:
        logger.debug("LWA アクセストークンを更新します")
        resp = self._session.post(
            self._credentials.lwa_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._credentials.refresh_token,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"LWA トークン取得に失敗 ({resp.status_code}): {resp.text}"
            )
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._access_token
