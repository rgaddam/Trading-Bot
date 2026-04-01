from __future__ import annotations

import logging
from dataclasses import asdict

from ib_insync import IB

from config import OptionsConfig, SafetyConfig
from risk_manager import OrderSpec

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    Safety-first executor.

    This hardened version is intentionally DRY-RUN by default.
    It logs a normalized execution plan and refuses live order placement
    unless ENABLE_LIVE_ORDERS=true and PAPER_TRADING=false.

    Why this guard exists:
    the current project still evaluates the underlying QQQ bars but does not yet
    contain a fully tested option-chain resolver + premium-aware bracket manager.
    """

    def __init__(self, ib: IB, options_cfg: OptionsConfig, safety_cfg: SafetyConfig):
        self.ib = ib
        self.options_cfg = options_cfg
        self.safety = safety_cfg

    def execute(self, spec: OrderSpec) -> bool:
        logger.info("Execution plan: %s", asdict(spec))
        if self.safety.dry_run or self.safety.paper_trading or not self.safety.enable_live_orders:
            logger.warning(
                "DRY-RUN ONLY: no live order placed. "
                "Set DRY_RUN=false, PAPER_TRADING=false, and ENABLE_LIVE_ORDERS=true only after adding tested option execution."
            )
            return True

        logger.error("Live order placement is intentionally blocked in this hardened package until option execution is fully implemented.")
        return False
