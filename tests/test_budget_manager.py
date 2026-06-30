"""予算ペーシングロジックのテスト."""

from zazoo_ads.config import BudgetRules
from zazoo_ads.models import Campaign, EntityState
from zazoo_ads.rules.budget_manager import adjust_budgets


def _c(**kwargs) -> Campaign:
    base = dict(campaign_id="c1", name="ザズー_SP", daily_budget=1000.0)
    base.update(kwargs)
    return Campaign(**base)


def test_increase_on_good_acos():
    rules = BudgetRules(increase_when_acos_below=0.20, increase_step=0.20, min_cost=500.0)
    c = _c(cost=600.0, sales=6000.0)  # ACoS 10%
    out = adjust_budgets([c], rules)
    assert len(out) == 1
    assert out[0].new_budget == 1200.0


def test_decrease_on_bad_acos():
    rules = BudgetRules(decrease_when_acos_above=0.50, decrease_step=0.20, min_cost=500.0)
    c = _c(cost=600.0, sales=1000.0)  # ACoS 60%
    out = adjust_budgets([c], rules)
    assert len(out) == 1
    assert out[0].new_budget == 800.0


def test_no_change_in_target_band():
    rules = BudgetRules(
        increase_when_acos_below=0.20,
        decrease_when_acos_above=0.50,
        min_cost=500.0,
    )
    c = _c(cost=600.0, sales=2000.0)  # ACoS 30%
    assert adjust_budgets([c], rules) == []


def test_skip_low_cost():
    rules = BudgetRules(min_cost=500.0)
    c = _c(cost=100.0, sales=2000.0)
    assert adjust_budgets([c], rules) == []


def test_disabled():
    rules = BudgetRules(enabled=False)
    c = _c(cost=600.0, sales=6000.0)
    assert adjust_budgets([c], rules) == []


def test_paused_campaign_skipped():
    rules = BudgetRules(min_cost=500.0)
    c = _c(cost=600.0, sales=6000.0, state=EntityState.PAUSED)
    assert adjust_budgets([c], rules) == []


def test_budget_clamped_to_max():
    rules = BudgetRules(
        increase_when_acos_below=0.20,
        increase_step=0.20,
        max_daily_budget=1100.0,
        min_cost=500.0,
    )
    c = _c(daily_budget=1000.0, cost=600.0, sales=6000.0)
    out = adjust_budgets([c], rules)
    assert out[0].new_budget == 1100.0
