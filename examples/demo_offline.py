"""認証情報なしで動かせるオフラインデモ.

サンプルのレポートデータに対してルールエンジンを適用し、生成される
自動化プランを表示する。API は呼ばない。

実行:
  PYTHONPATH=src python examples/demo_offline.py
"""

from zazoo_ads.automation import build_plan
from zazoo_ads.cli import _print_plan
from zazoo_ads.config import RulesConfig
from zazoo_ads.models import (
    Campaign,
    KeywordMetrics,
    MatchType,
    SearchTermMetrics,
)


def main() -> None:
    config = RulesConfig.from_dict({})  # 既定ルール

    keywords = [
        KeywordMetrics(
            keyword_id="111", campaign_id="c1", ad_group_id="g1",
            keyword_text="ザズー リング", match_type=MatchType.EXACT, bid=80.0,
            impressions=5000, clicks=40, cost=2400.0, sales=3000.0, orders=6,
        ),  # ACoS 80% → 引き下げ
        KeywordMetrics(
            keyword_id="222", campaign_id="c1", ad_group_id="g1",
            keyword_text="ザズー ネックレス", match_type=MatchType.EXACT, bid=60.0,
            impressions=8000, clicks=50, cost=600.0, sales=6000.0, orders=12,
        ),  # ACoS 10% → 引き上げ
        KeywordMetrics(
            keyword_id="333", campaign_id="c1", ad_group_id="g1",
            keyword_text="ザズー ピアス", match_type=MatchType.BROAD, bid=70.0,
            impressions=3000, clicks=20, cost=1400.0, sales=0.0, orders=0,
        ),  # 売上ゼロ → 引き下げ
    ]

    search_terms = [
        SearchTermMetrics(
            search_term="ザズー シルバー リング", campaign_id="c1", ad_group_id="g1",
            keyword_id="111", keyword_text="ザズー リング", match_type=MatchType.BROAD,
            impressions=2000, clicks=15, cost=900.0, sales=9000.0, orders=5,
        ),  # 好調 → 収集
        SearchTermMetrics(
            search_term="安い アクセサリー まとめ", campaign_id="c1", ad_group_id="g1",
            keyword_id="333", keyword_text="ザズー ピアス", match_type=MatchType.BROAD,
            impressions=4000, clicks=25, cost=600.0, sales=0.0, orders=0,
        ),  # 浪費 → 除外
    ]

    campaigns = [
        Campaign(
            campaign_id="c1", name="ザズー_SP_主力", daily_budget=3000.0,
            cost=4400.0, sales=18000.0,  # ACoS 約 24%（帯内）→ 変更なし
        ),
        Campaign(
            campaign_id="c2", name="ザズー_SP_新商品", daily_budget=2000.0,
            cost=1500.0, sales=15000.0,  # ACoS 10% → 増額
        ),
    ]

    plan = build_plan(keywords, search_terms, campaigns, config)
    _print_plan(plan)


if __name__ == "__main__":
    main()
