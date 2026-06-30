"""オーケストレーション (build_plan) の統合テスト."""

import os

from zazoo_ads.automation import build_plan
from zazoo_ads.config import RulesConfig
from zazoo_ads.models import (
    Campaign,
    KeywordMetrics,
    MatchType,
    SearchTermMetrics,
)

EXAMPLE_RULES = os.path.join(
    os.path.dirname(__file__), "..", "config", "rules.example.yaml"
)


def test_example_yaml_loads():
    cfg = RulesConfig.from_yaml(EXAMPLE_RULES)
    assert cfg.bid.target_acos == 0.30
    assert cfg.harvest.default_match_type == "EXACT"


def test_build_plan_combines_all_rules():
    cfg = RulesConfig.from_dict({})

    keywords = [
        KeywordMetrics(
            keyword_id="k1", campaign_id="c1", ad_group_id="g1",
            keyword_text="ザズー", match_type=MatchType.EXACT, bid=100.0,
            clicks=20, cost=80.0, sales=100.0, orders=1,  # ACoS 80% → 引き下げ
        ),
    ]
    search_terms = [
        # 好調 → 収集対象
        SearchTermMetrics(
            search_term="ザズー 財布", campaign_id="c1", ad_group_id="g1",
            keyword_id="k1", keyword_text="ザズー", match_type=MatchType.BROAD,
            clicks=10, cost=100.0, sales=1000.0, orders=3,
        ),
        # 浪費 → 除外対象
        SearchTermMetrics(
            search_term="無関係", campaign_id="c1", ad_group_id="g1",
            keyword_id="k1", keyword_text="ザズー", match_type=MatchType.BROAD,
            clicks=20, cost=300.0, sales=0.0, orders=0,
        ),
    ]
    campaigns = [
        Campaign(
            campaign_id="c1", name="ザズー_SP", daily_budget=1000.0,
            cost=600.0, sales=6000.0,  # ACoS 10% → 増額
        ),
    ]

    plan = build_plan(keywords, search_terms, campaigns, cfg)
    assert len(plan.bid_changes) == 1
    assert len(plan.harvests) == 1
    assert len(plan.negatives) == 1
    assert len(plan.budget_changes) == 1
    assert "件" in plan.summary()
