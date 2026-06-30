"""キーワード収集ロジックのテスト."""

from zazoo_ads.config import HarvestRules
from zazoo_ads.models import KeywordMetrics, MatchType, SearchTermMetrics
from zazoo_ads.rules.keyword_harvester import harvest_keywords


def _st(**kwargs) -> SearchTermMetrics:
    base = dict(
        search_term="ザズー バッグ",
        campaign_id="c1",
        ad_group_id="g1",
        keyword_id="k1",
        keyword_text="ザズー",
        match_type=MatchType.BROAD,
    )
    base.update(kwargs)
    return SearchTermMetrics(**base)


def _kw(**kwargs) -> KeywordMetrics:
    base = dict(
        keyword_id="k1",
        campaign_id="c1",
        ad_group_id="g1",
        keyword_text="ザズー",
        match_type=MatchType.EXACT,
        bid=50.0,
    )
    base.update(kwargs)
    return KeywordMetrics(**base)


def test_harvest_good_term():
    rules = HarvestRules(min_orders=2, max_acos=0.30, bid_multiplier=1.0)
    st = _st(clicks=10, cost=100.0, sales=1000.0, orders=3)  # ACoS 10%
    out = harvest_keywords([st], [], rules)
    assert len(out) == 1
    assert out[0].keyword_text == "ザズー バッグ"
    assert out[0].match_type == MatchType.EXACT
    assert out[0].suggested_bid == 10.0  # cpc = 100/10 = 10


def test_skip_low_orders():
    rules = HarvestRules(min_orders=2, max_acos=0.30)
    st = _st(clicks=10, cost=100.0, sales=1000.0, orders=1)
    assert harvest_keywords([st], [], rules) == []


def test_skip_high_acos():
    rules = HarvestRules(min_orders=2, max_acos=0.30)
    st = _st(clicks=10, cost=500.0, sales=1000.0, orders=3)  # ACoS 50%
    assert harvest_keywords([st], [], rules) == []


def test_skip_already_existing_exact_keyword():
    rules = HarvestRules(min_orders=2, max_acos=0.30)
    st = _st(search_term="ザズー バッグ", clicks=10, cost=100.0, sales=1000.0, orders=3)
    existing = _kw(keyword_text="ザズー バッグ", match_type=MatchType.EXACT)
    assert harvest_keywords([st], [existing], rules) == []


def test_dedup_within_run():
    rules = HarvestRules(min_orders=2, max_acos=0.30)
    st1 = _st(clicks=10, cost=100.0, sales=1000.0, orders=3)
    st2 = _st(clicks=5, cost=50.0, sales=500.0, orders=2)  # 同一語句
    out = harvest_keywords([st1, st2], [], rules)
    assert len(out) == 1
