"""自動化ルール（純粋ロジック層）.

API に依存しない純関数として実装し、レポートデータを入力に提案を返す。
テスト容易性のため副作用は持たない。
"""

from .bid_optimizer import optimize_bids
from .keyword_harvester import harvest_keywords
from .negative_keywords import suggest_negatives
from .budget_manager import adjust_budgets

__all__ = [
    "optimize_bids",
    "harvest_keywords",
    "suggest_negatives",
    "adjust_budgets",
]
