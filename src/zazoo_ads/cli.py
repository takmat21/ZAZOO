"""コマンドラインインターフェース.

使い方の例:
  # 直近 30 日のデータで提案を表示（適用しない）
  python -m zazoo_ads run --rules config/rules.example.yaml --dry-run

  # 実際に適用する
  python -m zazoo_ads run --rules config/rules.yaml --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from .api.client import AdsApiClient
from .api.reports import ReportClient
from .automation import apply_plan, build_plan
from .config import ApiCredentials, RulesConfig
from .models import AutomationResult
from .utils.logging import setup_logging


def _default_dates(days: int) -> tuple[str, str]:
    """直近 N 日の (開始日, 終了日) を返す。終了日は前日。"""
    today = dt.date.today()
    end = today - dt.timedelta(days=1)
    start = end - dt.timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _print_plan(plan: AutomationResult) -> None:
    print("\n=== 自動化プラン ===")
    print(plan.summary())

    if plan.bid_changes:
        print("\n--- 入札変更 ---")
        for c in plan.bid_changes:
            print(
                f"  [{c.keyword_text}] {c.old_bid:.2f} → {c.new_bid:.2f} "
                f"({c.reason})"
            )
    if plan.harvests:
        print("\n--- キーワード収集 ---")
        for h in plan.harvests:
            print(
                f"  + [{h.keyword_text}] {h.match_type.value} "
                f"@ {h.suggested_bid:.2f} ({h.reason})"
            )
    if plan.negatives:
        print("\n--- 除外キーワード ---")
        for n in plan.negatives:
            print(f"  - [{n.search_term}] {n.match_type.value} ({n.reason})")
    if plan.budget_changes:
        print("\n--- 予算変更 ---")
        for b in plan.budget_changes:
            print(
                f"  [{b.name}] {b.old_budget:.0f} → {b.new_budget:.0f} "
                f"({b.reason})"
            )
    print()


def _cmd_run(args: argparse.Namespace) -> int:
    logger = setup_logging(args.verbose)
    config = RulesConfig.from_yaml(args.rules)

    if args.start and args.end:
        start, end = args.start, args.end
    else:
        start, end = _default_dates(args.days)
    logger.info("対象期間: %s 〜 %s", start, end)

    credentials = ApiCredentials.from_env()
    client = AdsApiClient(credentials)
    reports = ReportClient(client)

    logger.info("レポートを取得します…")
    keywords = reports.fetch_keyword_metrics(start, end)
    search_terms = reports.fetch_search_term_metrics(start, end)
    logger.info(
        "取得: キーワード %d 行 / 検索語句 %d 行",
        len(keywords), len(search_terms),
    )

    # 予算調整は別途キャンペーン一覧が必要。本 CLI では未取得のため空。
    campaigns: list = []

    plan = build_plan(keywords, search_terms, campaigns, config)
    _print_plan(plan)

    if args.apply:
        logger.info("プランを適用します")
        apply_plan(client, plan)
        logger.info("適用完了")
    else:
        logger.info("dry-run のため適用しません（--apply で実行）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zazoo_ads",
        description="ZAZOO Amazon 広告運用自動化ツール",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="レポートを取得して自動化を実行")
    run.add_argument(
        "--rules", required=True, help="ルール設定 YAML のパス"
    )
    run.add_argument(
        "--days", type=int, default=30, help="対象期間の日数 (既定: 30)"
    )
    run.add_argument("--start", help="開始日 YYYY-MM-DD (--days より優先)")
    run.add_argument("--end", help="終了日 YYYY-MM-DD")
    group = run.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run", action="store_true", default=True,
        help="提案のみ表示し適用しない（既定）",
    )
    group.add_argument(
        "--apply", action="store_true", help="提案を実際に適用する"
    )
    run.add_argument("-v", "--verbose", action="store_true", help="詳細ログ")
    run.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
