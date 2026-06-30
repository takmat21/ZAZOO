"""広告運用で扱うデータモデル.

Amazon Advertising API のレポートや管理オブジェクトを、ルールエンジンが
扱いやすい形に正規化したデータクラス群。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MatchType(str, Enum):
    """キーワードのマッチタイプ."""

    EXACT = "EXACT"
    PHRASE = "PHRASE"
    BROAD = "BROAD"


class EntityState(str, Enum):
    """キャンペーン / 広告グループ / キーワードの状態."""

    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


@dataclass
class KeywordMetrics:
    """キーワード単位のパフォーマンス指標.

    レポートの 1 行に対応する。金額は出稿先の通貨単位（例: JPY）。
    """

    keyword_id: str
    campaign_id: str
    ad_group_id: str
    keyword_text: str
    match_type: MatchType
    bid: float
    state: EntityState = EntityState.ENABLED
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    sales: float = 0.0
    orders: int = 0

    @property
    def acos(self) -> Optional[float]:
        """ACoS (広告費売上高比率) = cost / sales。売上 0 のときは None。"""
        if self.sales <= 0:
            return None
        return self.cost / self.sales

    @property
    def roas(self) -> Optional[float]:
        """ROAS (広告費用対効果) = sales / cost。費用 0 のときは None。"""
        if self.cost <= 0:
            return None
        return self.sales / self.cost

    @property
    def ctr(self) -> Optional[float]:
        """クリック率 = clicks / impressions。"""
        if self.impressions <= 0:
            return None
        return self.clicks / self.impressions

    @property
    def cvr(self) -> Optional[float]:
        """コンバージョン率 = orders / clicks。"""
        if self.clicks <= 0:
            return None
        return self.orders / self.clicks


@dataclass
class SearchTermMetrics:
    """検索語句 (search term) 単位のパフォーマンス指標.

    キーワード収集・除外キーワード判定の入力になる。
    """

    search_term: str
    campaign_id: str
    ad_group_id: str
    keyword_id: str
    keyword_text: str
    match_type: MatchType
    impressions: int = 0
    clicks: int = 0
    cost: float = 0.0
    sales: float = 0.0
    orders: int = 0

    @property
    def acos(self) -> Optional[float]:
        if self.sales <= 0:
            return None
        return self.cost / self.sales

    @property
    def cvr(self) -> Optional[float]:
        if self.clicks <= 0:
            return None
        return self.orders / self.clicks


@dataclass
class Campaign:
    """キャンペーン (予算ペーシング対象)."""

    campaign_id: str
    name: str
    daily_budget: float
    state: EntityState = EntityState.ENABLED
    cost: float = 0.0
    sales: float = 0.0


@dataclass
class BidChange:
    """入札変更の提案／適用結果."""

    keyword_id: str
    keyword_text: str
    old_bid: float
    new_bid: float
    reason: str

    @property
    def delta(self) -> float:
        return self.new_bid - self.old_bid


@dataclass
class NegativeKeywordSuggestion:
    """除外キーワードの提案."""

    campaign_id: str
    ad_group_id: str
    search_term: str
    match_type: MatchType
    reason: str


@dataclass
class HarvestSuggestion:
    """新規キーワード追加（収集）の提案."""

    campaign_id: str
    ad_group_id: str
    keyword_text: str
    match_type: MatchType
    suggested_bid: float
    reason: str


@dataclass
class BudgetChange:
    """日予算の変更提案／適用結果."""

    campaign_id: str
    name: str
    old_budget: float
    new_budget: float
    reason: str


@dataclass
class AutomationResult:
    """1 回の自動化実行でまとめた提案・適用結果."""

    bid_changes: list[BidChange] = field(default_factory=list)
    negatives: list[NegativeKeywordSuggestion] = field(default_factory=list)
    harvests: list[HarvestSuggestion] = field(default_factory=list)
    budget_changes: list[BudgetChange] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"入札変更 {len(self.bid_changes)} 件 / "
            f"除外キーワード {len(self.negatives)} 件 / "
            f"キーワード収集 {len(self.harvests)} 件 / "
            f"予算変更 {len(self.budget_changes)} 件"
        )
