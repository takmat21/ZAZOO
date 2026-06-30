"""除外キーワードロジックのテスト."""

from zazoo_ads.config import NegativeRules
from zazoo_ads.models import MatchType, SearchTermMetrics
from zazoo_ads.rules.negative_keywords import suggest_negatives


def _st(**kwargs) -> SearchTermMetrics:
    base = dict(
        search_term="無関係 ワード",
        campaign_id="c1",
        ad_group_id="g1",
        keyword_id="k1",
        keyword_text="ザズー",
        match_type=MatchType.BROAD,
    )
    base.update(kwargs)
    return SearchTermMetrics(**base)


def test_suggest_wasteful_term():
    rules = NegativeRules(min_clicks=15, max_orders=0, min_cost=100.0)
    st = _st(clicks=20, cost=300.0, sales=0.0, orders=0)
    out = suggest_negatives([st], rules)
    assert len(out) == 1
    assert out[0].search_term == "無関係 ワード"
    assert out[0].match_type == MatchType.EXACT


def test_skip_when_has_orders():
    rules = NegativeRules(min_clicks=15, max_orders=0, min_cost=100.0)
    st = _st(clicks=20, cost=300.0, sales=500.0, orders=1)
    assert suggest_negatives([st], rules) == []


def test_skip_low_clicks():
    rules = NegativeRules(min_clicks=15, max_orders=0, min_cost=100.0)
    st = _st(clicks=5, cost=300.0, sales=0.0, orders=0)
    assert suggest_negatives([st], rules) == []


def test_skip_low_cost():
    rules = NegativeRules(min_clicks=15, max_orders=0, min_cost=100.0)
    st = _st(clicks=20, cost=50.0, sales=0.0, orders=0)
    assert suggest_negatives([st], rules) == []


def test_dedup():
    rules = NegativeRules(min_clicks=15, max_orders=0, min_cost=100.0)
    st1 = _st(clicks=20, cost=300.0, orders=0)
    st2 = _st(clicks=18, cost=200.0, orders=0)
    assert len(suggest_negatives([st1, st2], rules)) == 1
