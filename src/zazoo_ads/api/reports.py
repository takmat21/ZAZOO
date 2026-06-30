"""Sponsored Products v3 レポートの取得.

レポートは「作成 → 生成完了までポーリング → ダウンロード (gzip JSON)」
の 3 ステップ。取得した行を models のデータクラスへ正規化する。
"""

from __future__ import annotations

import gzip
import io
import json
import logging
import time
from typing import Any, Optional

from ..models import (
    EntityState,
    KeywordMetrics,
    MatchType,
    SearchTermMetrics,
)
from .client import AdsApiClient

logger = logging.getLogger("zazoo_ads")

REPORT_CONTENT_TYPE = "application/vnd.createasyncreportrequest.v3+json"


def _to_match_type(value: Optional[str]) -> MatchType:
    """API の matchType 文字列を MatchType へ。未知値は BROAD 扱い。"""
    if not value:
        return MatchType.BROAD
    try:
        return MatchType(value.upper())
    except ValueError:
        return MatchType.BROAD


def _to_state(value: Optional[str]) -> EntityState:
    if not value:
        return EntityState.ENABLED
    try:
        return EntityState(value.upper())
    except ValueError:
        return EntityState.ENABLED


class ReportClient:
    """非同期レポートの作成・取得を行う."""

    def __init__(
        self,
        client: AdsApiClient,
        poll_interval: float = 15.0,
        max_wait: float = 600.0,
    ) -> None:
        self._client = client
        self._poll_interval = poll_interval
        self._max_wait = max_wait

    def _create_report(self, body: dict[str, Any]) -> str:
        resp = self._client.request(
            "POST",
            "/reporting/reports",
            content_type=REPORT_CONTENT_TYPE,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()["reportId"]

    def _wait_for_report(self, report_id: str) -> str:
        """生成完了を待ち、ダウンロード URL を返す."""
        deadline = time.time() + self._max_wait
        while time.time() < deadline:
            resp = self._client.request("GET", f"/reporting/reports/{report_id}")
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "COMPLETED":
                return data["url"]
            if status == "FAILED":
                raise RuntimeError(
                    f"レポート生成失敗: {data.get('failureReason', '不明')}"
                )
            logger.debug("レポート %s は %s。待機します", report_id, status)
            time.sleep(self._poll_interval)
        raise TimeoutError(f"レポート {report_id} の生成がタイムアウトしました")

    def _download(self, url: str) -> list[dict[str, Any]]:
        """gzip 圧縮された JSON レポートを取得して行リストを返す."""
        import requests

        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        raw = resp.content
        # gzip ヘッダ (0x1f 0x8b) があれば解凍
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return json.loads(raw.decode("utf-8"))

    def _fetch(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        report_id = self._create_report(body)
        logger.info("レポート作成: %s", report_id)
        url = self._wait_for_report(report_id)
        return self._download(url)

    # --- キーワードレポート ----------------------------------------------

    def fetch_keyword_metrics(
        self, start_date: str, end_date: str
    ) -> list[KeywordMetrics]:
        """期間内のキーワード単位指標を取得する (YYYY-MM-DD)."""
        body = {
            "name": f"sp-keywords-{start_date}-{end_date}",
            "startDate": start_date,
            "endDate": end_date,
            "configuration": {
                "adProduct": "SPONSORED_PRODUCTS",
                "groupBy": ["targeting"],
                "columns": [
                    "keywordId", "campaignId", "adGroupId", "keyword",
                    "matchType", "keywordBid", "impressions", "clicks",
                    "cost", "sales30d", "purchases30d",
                ],
                "reportTypeId": "spTargeting",
                "timeUnit": "SUMMARY",
                "format": "GZIP_JSON",
            },
        }
        rows = self._fetch(body)
        return [self._row_to_keyword(r) for r in rows]

    @staticmethod
    def _row_to_keyword(row: dict[str, Any]) -> KeywordMetrics:
        return KeywordMetrics(
            keyword_id=str(row.get("keywordId", "")),
            campaign_id=str(row.get("campaignId", "")),
            ad_group_id=str(row.get("adGroupId", "")),
            keyword_text=row.get("keyword", ""),
            match_type=_to_match_type(row.get("matchType")),
            bid=float(row.get("keywordBid", 0.0) or 0.0),
            state=_to_state(row.get("state")),
            impressions=int(row.get("impressions", 0) or 0),
            clicks=int(row.get("clicks", 0) or 0),
            cost=float(row.get("cost", 0.0) or 0.0),
            sales=float(row.get("sales30d", 0.0) or 0.0),
            orders=int(row.get("purchases30d", 0) or 0),
        )

    # --- 検索語句レポート ------------------------------------------------

    def fetch_search_term_metrics(
        self, start_date: str, end_date: str
    ) -> list[SearchTermMetrics]:
        """期間内の検索語句単位指標を取得する."""
        body = {
            "name": f"sp-searchterms-{start_date}-{end_date}",
            "startDate": start_date,
            "endDate": end_date,
            "configuration": {
                "adProduct": "SPONSORED_PRODUCTS",
                "groupBy": ["searchTerm"],
                "columns": [
                    "searchTerm", "campaignId", "adGroupId", "keywordId",
                    "keyword", "matchType", "impressions", "clicks",
                    "cost", "sales30d", "purchases30d",
                ],
                "reportTypeId": "spSearchTerm",
                "timeUnit": "SUMMARY",
                "format": "GZIP_JSON",
            },
        }
        rows = self._fetch(body)
        return [self._row_to_search_term(r) for r in rows]

    @staticmethod
    def _row_to_search_term(row: dict[str, Any]) -> SearchTermMetrics:
        return SearchTermMetrics(
            search_term=row.get("searchTerm", ""),
            campaign_id=str(row.get("campaignId", "")),
            ad_group_id=str(row.get("adGroupId", "")),
            keyword_id=str(row.get("keywordId", "")),
            keyword_text=row.get("keyword", ""),
            match_type=_to_match_type(row.get("matchType")),
            impressions=int(row.get("impressions", 0) or 0),
            clicks=int(row.get("clicks", 0) or 0),
            cost=float(row.get("cost", 0.0) or 0.0),
            sales=float(row.get("sales30d", 0.0) or 0.0),
            orders=int(row.get("purchases30d", 0) or 0),
        )
