"""入札最適化ロジックのテスト."""

from zazoo_ads.config import BidRules
from zazoo_ads.models import EntityState, KeywordMetrics, MatchType
from zazoo_ads.rules.bid_optimizer import optimize_bids


def _kw(**kwargs) -> KeywordMetrics:
    base = dict(
        keyword_id="k1",
        campaign_id="c1",
        ad_group_id="g1",
        keyword_text="ザズー",
        match_type=MatchType.EXACT,
        bid=100.0,
    )
    base.update(kwargs)
    return KeywordMetrics(**base)


def test_high_acos_lowers_bid():
    rules = BidRules(target_acos=0.30, min_clicks=10, bid_down_step=0.15)
    # ACoS = 50 / 100 = 50% > 30%
    kw = _kw(clicks=20, cost=50.0, sales=100.0, orders=1)
    changes = optimize_bids([kw], rules)
    assert len(changes) == 1
    assert changes[0].new_bid == 85.0  # 100 * 0.85
    assert changes[0].new_bid < changes[0].old_bid


def test_low_acos_raises_bid():
    rules = BidRules(target_acos=0.30, min_clicks=10, bid_up_step=0.10)
    # ACoS = 10 / 100 = 10% < 30%
    kw = _kw(clicks=20, cost=10.0, sales=100.0, orders=2)
    changes = optimize_bids([kw], rules)
    assert len(changes) == 1
    assert changes[0].new_bid == 110.0  # 100 * 1.10


def test_zero_sales_with_many_clicks_lowers_bid():
    rules = BidRules(zero_sale_clicks=15, bid_down_step=0.15)
    kw = _kw(clicks=20, cost=200.0, sales=0.0, orders=0)
    changes = optimize_bids([kw], rules)
    assert len(changes) == 1
    assert changes[0].new_bid == 85.0
    assert "売上ゼロ" in changes[0].reason


def test_few_clicks_no_change():
    rules = BidRules(min_clicks=10, zero_sale_clicks=15)
    # クリック少 & 売上あり → 判定対象外
    kw = _kw(clicks=5, cost=10.0, sales=100.0, orders=1)
    assert optimize_bids([kw], rules) == []


def test_zero_sales_few_clicks_no_change():
    rules = BidRules(zero_sale_clicks=15)
    kw = _kw(clicks=5, cost=20.0, sales=0.0, orders=0)
    assert optimize_bids([kw], rules) == []


def test_bid_clamped_to_min():
    rules = BidRules(target_acos=0.30, min_clicks=10, bid_down_step=0.15, min_bid=95.0)
    kw = _kw(bid=100.0, clicks=20, cost=80.0, sales=100.0, orders=1)
    changes = optimize_bids([kw], rules)
    assert changes[0].new_bid == 95.0  # 85 だが下限 95 に丸められる


def test_bid_clamped_to_max():
    rules = BidRules(target_acos=0.30, min_clicks=10, bid_up_step=0.10, max_bid=105.0)
    kw = _kw(bid=100.0, clicks=20, cost=10.0, sales=100.0, orders=2)
    changes = optimize_bids([kw], rules)
    assert changes[0].new_bid == 105.0  # 110 だが上限 105


def test_paused_keyword_skipped():
    rules = BidRules()
    kw = _kw(state=EntityState.PAUSED, clicks=20, cost=50.0, sales=100.0, orders=1)
    assert optimize_bids([kw], rules) == []


def test_acos_exactly_at_target_no_change():
    rules = BidRules(target_acos=0.30, min_clicks=10)
    # ACoS = 30 / 100 = 30% ちょうど → 変更なし
    kw = _kw(clicks=20, cost=30.0, sales=100.0, orders=1)
    assert optimize_bids([kw], rules) == []
