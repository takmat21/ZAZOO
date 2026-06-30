"""ロギング設定."""

from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False) -> logging.Logger:
    """ルートロガーを設定して返す."""
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("zazoo_ads")
    logger.setLevel(level)
    # 多重ハンドラ登録を防ぐ
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)
    return logger
