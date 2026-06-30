"""自動化オーケストレーション.

レポートデータとルール設定から提案 (AutomationResult) を生成し、
dry-run でなければ API クライアントを通じて適用する。
"""

from __future__ import annotations

import logging

from .api.client import AdsApiClient
from .config import RulesConfig
from .models import (
    AutomationResult,
    Campaign,
    KeywordMetrics,
    SearchTermMetrics,
)
from .rules import (
    adjust_budgets,
    harvest_keywords,
    optimize_bids,
    suggest_negatives,
)

logger = logging.getLogger("zazoo_ads")


def build_plan(
    keywords: list[KeywordMetrics],
    search_terms: list[SearchTermMetrics],
    campaigns: list[Campaign],
    config: RulesConfig,
) -> AutomationResult:
    """各ルールを実行し、提案をまとめて返す（副作用なし）."""
    return AutomationResult(
        bid_changes=optimize_bids(keywords, config.bid),
        negatives=suggest_negatives(search_terms, config.negative),
        harvests=harvest_keywords(search_terms, keywords, config.harvest),
        budget_changes=adjust_budgets(campaigns, config.budget),
    )


def apply_plan(client: AdsApiClient, plan: AutomationResult) -> None:
    """提案を API に適用する（dry-run でないときのみ呼ぶ）."""
    if plan.bid_changes:
        updates = [
            {"keywordId": c.keyword_id, "bid": c.new_bid}
            for c in plan.bid_changes
        ]
        logger.info("入札を %d 件更新します", len(updates))
        client.update_keyword_bids(updates)

    if plan.negatives:
        negatives = [
            {
                "campaignId": n.campaign_id,
                "adGroupId": n.ad_group_id,
                "keywordText": n.search_term,
                "matchType": f"NEGATIVE_{n.match_type.value}",
                "state": "ENABLED",
            }
            for n in plan.negatives
        ]
        logger.info("除外キーワードを %d 件追加します", len(negatives))
        client.create_negative_keywords(negatives)

    if plan.harvests:
        keywords = [
            {
                "campaignId": h.campaign_id,
                "adGroupId": h.ad_group_id,
                "keywordText": h.keyword_text,
                "matchType": h.match_type.value,
                "bid": h.suggested_bid,
                "state": "ENABLED",
            }
            for h in plan.harvests
        ]
        logger.info("キーワードを %d 件追加します", len(keywords))
        client.create_keywords(keywords)

    if plan.budget_changes:
        updates = [
            {
                "campaignId": b.campaign_id,
                "budget": {"budget": b.new_budget, "budgetType": "DAILY"},
            }
            for b in plan.budget_changes
        ]
        logger.info("予算を %d 件更新します", len(updates))
        client.update_campaign_budgets(updates)
