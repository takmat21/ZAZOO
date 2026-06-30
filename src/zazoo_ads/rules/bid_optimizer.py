"""入札最適化ルール.

目標 ACoS を基準に、キーワードごとの入札を引き上げ／引き下げする。
判定の前提:
  - クリック数が少ないキーワードは統計的に不安定なので対象外。
  - 売上が出ていて ACoS が目標より低い → 取りこぼしを防ぐため引き上げ。
  - ACoS が目標より高い → 採算改善のため引き下げ。
  - 十分クリックされているのに売上ゼロ → 強めに引き下げ。
"""

from __future__ import annotations

from ..config import BidRules
from ..models import BidChange, EntityState, KeywordMetrics


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round_bid(value: float) -> float:
    """入札は小数第 2 位まで（通貨最小単位を想定）に丸める."""
    return round(value, 2)


def optimize_bids(
    keywords: list[KeywordMetrics], rules: BidRules
) -> list[BidChange]:
    """入札変更案のリストを返す（変更不要なものは含めない）."""
    changes: list[BidChange] = []
    for kw in keywords:
        if kw.state != EntityState.ENABLED:
            continue
        change = _evaluate(kw, rules)
        if change is not None:
            changes.append(change)
    return changes


def _evaluate(kw: KeywordMetrics, rules: BidRules) -> BidChange | None:
    # 売上ゼロかつ十分クリックされている → 強めに引き下げ
    if kw.orders == 0 and kw.clicks >= rules.zero_sale_clicks:
        new_bid = _round_bid(
            _clamp(kw.bid * (1 - rules.bid_down_step), rules.min_bid, rules.max_bid)
        )
        if new_bid < kw.bid:
            return BidChange(
                keyword_id=kw.keyword_id,
                keyword_text=kw.keyword_text,
                old_bid=kw.bid,
                new_bid=new_bid,
                reason=(
                    f"{kw.clicks} クリックで売上ゼロのため "
                    f"-{int(rules.bid_down_step * 100)}%"
                ),
            )
        return None

    # クリック数が少なすぎる場合は判定しない（ノイズ回避）
    if kw.clicks < rules.min_clicks:
        return None

    acos = kw.acos
    if acos is None:
        return None  # 売上ゼロは上で処理済み

    # ACoS が目標より高い → 引き下げ
    if acos > rules.target_acos:
        new_bid = _round_bid(
            _clamp(kw.bid * (1 - rules.bid_down_step), rules.min_bid, rules.max_bid)
        )
        if new_bid < kw.bid:
            return BidChange(
                keyword_id=kw.keyword_id,
                keyword_text=kw.keyword_text,
                old_bid=kw.bid,
                new_bid=new_bid,
                reason=(
                    f"ACoS {acos:.0%} > 目標 {rules.target_acos:.0%} のため "
                    f"-{int(rules.bid_down_step * 100)}%"
                ),
            )
        return None

    # ACoS が目標より低い → 引き上げ（取りこぼし防止）
    if acos < rules.target_acos:
        new_bid = _round_bid(
            _clamp(kw.bid * (1 + rules.bid_up_step), rules.min_bid, rules.max_bid)
        )
        if new_bid > kw.bid:
            return BidChange(
                keyword_id=kw.keyword_id,
                keyword_text=kw.keyword_text,
                old_bid=kw.bid,
                new_bid=new_bid,
                reason=(
                    f"ACoS {acos:.0%} < 目標 {rules.target_acos:.0%} のため "
                    f"+{int(rules.bid_up_step * 100)}%"
                ),
            )
        return None

    return None
