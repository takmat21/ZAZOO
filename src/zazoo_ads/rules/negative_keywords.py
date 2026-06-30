"""除外キーワードルール.

検索語句レポートから「費用を浪費しているのに成果が出ない語句」を見つけ、
除外完全一致 (NEGATIVE_EXACT) の追加候補を提案する。
"""

from __future__ import annotations

from ..config import NegativeRules
from ..models import MatchType, NegativeKeywordSuggestion, SearchTermMetrics


def suggest_negatives(
    search_terms: list[SearchTermMetrics], rules: NegativeRules
) -> list[NegativeKeywordSuggestion]:
    """除外キーワードの提案リストを返す."""
    suggestions: list[NegativeKeywordSuggestion] = []
    seen: set[tuple[str, str]] = set()
    match_type = MatchType(rules.default_match_type)

    for st in search_terms:
        term = st.search_term.strip()
        if not term:
            continue
        # 条件: 十分クリックされ、費用が閾値以上、注文が閾値以下
        if st.clicks < rules.min_clicks:
            continue
        if st.cost < rules.min_cost:
            continue
        if st.orders > rules.max_orders:
            continue

        key = (st.ad_group_id, term.lower())
        if key in seen:
            continue
        seen.add(key)

        suggestions.append(
            NegativeKeywordSuggestion(
                campaign_id=st.campaign_id,
                ad_group_id=st.ad_group_id,
                search_term=term,
                match_type=match_type,
                reason=(
                    f"{st.clicks} クリック / 費用 {st.cost:.0f} / "
                    f"注文 {st.orders} 件のため除外"
                ),
            )
        )
    return suggestions
