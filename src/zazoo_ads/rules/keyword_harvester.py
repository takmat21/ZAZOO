"""キーワード収集ルール.

検索語句レポートから「成果が出ているのにキーワード化されていない語句」を
見つけ、完全一致での追加候補を提案する。

すでにキーワードとして登録済みの語句（同一広告グループ内で完全一致）は
重複登録を避けるため除外する。
"""

from __future__ import annotations

from ..config import HarvestRules
from ..models import (
    HarvestSuggestion,
    KeywordMetrics,
    MatchType,
    SearchTermMetrics,
)


def _existing_exact_terms(
    keywords: list[KeywordMetrics],
) -> set[tuple[str, str]]:
    """(広告グループID, 正規化語句) の集合。完全一致で既存判定する."""
    existing: set[tuple[str, str]] = set()
    for kw in keywords:
        if kw.match_type == MatchType.EXACT:
            existing.add((kw.ad_group_id, kw.keyword_text.strip().lower()))
    return existing


def harvest_keywords(
    search_terms: list[SearchTermMetrics],
    keywords: list[KeywordMetrics],
    rules: HarvestRules,
) -> list[HarvestSuggestion]:
    """新規キーワード追加の提案リストを返す."""
    existing = _existing_exact_terms(keywords)
    match_type = MatchType(rules.default_match_type)
    suggestions: list[HarvestSuggestion] = []
    seen: set[tuple[str, str]] = set()

    for st in search_terms:
        term = st.search_term.strip()
        if not term:
            continue
        acos = st.acos
        # 条件: 注文数が閾値以上 かつ ACoS が上限以下
        if st.orders < rules.min_orders:
            continue
        if acos is None or acos > rules.max_acos:
            continue

        key = (st.ad_group_id, term.lower())
        if key in existing or key in seen:
            continue
        seen.add(key)

        # 推奨入札: クリック単価 (cost/clicks) を基準に倍率をかける
        cpc = st.cost / st.clicks if st.clicks > 0 else 0.0
        suggested_bid = round(cpc * rules.bid_multiplier, 2)

        suggestions.append(
            HarvestSuggestion(
                campaign_id=st.campaign_id,
                ad_group_id=st.ad_group_id,
                keyword_text=term,
                match_type=match_type,
                suggested_bid=suggested_bid,
                reason=(
                    f"注文 {st.orders} 件 / ACoS {acos:.0%} の好調語句を"
                    f"{match_type.value} で追加"
                ),
            )
        )
    return suggestions
