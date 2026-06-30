"""予算ペーシングルール.

キャンペーンの ACoS を基準に日予算を増減する。
  - ACoS が十分低い（好調）→ 機会損失を防ぐため増額。
  - ACoS が高すぎる（不調）→ 損失抑制のため減額。
消化額が小さいキャンペーンはノイズが大きいので対象外。
"""

from __future__ import annotations

from ..config import BudgetRules
from ..models import BudgetChange, Campaign, EntityState


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def adjust_budgets(
    campaigns: list[Campaign], rules: BudgetRules
) -> list[BudgetChange]:
    """日予算の変更案リストを返す."""
    if not rules.enabled:
        return []

    changes: list[BudgetChange] = []
    for c in campaigns:
        if c.state != EntityState.ENABLED:
            continue
        if c.cost < rules.min_cost:
            continue
        if c.sales <= 0:
            continue  # ACoS が定義できない

        acos = c.cost / c.sales
        new_budget: float | None = None
        reason = ""

        if acos <= rules.increase_when_acos_below:
            new_budget = c.daily_budget * (1 + rules.increase_step)
            reason = (
                f"ACoS {acos:.0%} ≤ {rules.increase_when_acos_below:.0%} の好調のため "
                f"+{int(rules.increase_step * 100)}%"
            )
        elif acos >= rules.decrease_when_acos_above:
            new_budget = c.daily_budget * (1 - rules.decrease_step)
            reason = (
                f"ACoS {acos:.0%} ≥ {rules.decrease_when_acos_above:.0%} の不調のため "
                f"-{int(rules.decrease_step * 100)}%"
            )

        if new_budget is None:
            continue

        new_budget = round(
            _clamp(new_budget, rules.min_daily_budget, rules.max_daily_budget), 2
        )
        if abs(new_budget - c.daily_budget) < 1e-9:
            continue

        changes.append(
            BudgetChange(
                campaign_id=c.campaign_id,
                name=c.name,
                old_budget=c.daily_budget,
                new_budget=new_budget,
                reason=reason,
            )
        )
    return changes
