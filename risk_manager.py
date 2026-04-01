from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from ai_layer import TradeDecision
from config import OptionsConfig, RiskConfig
from signal_engine import Signal

logger = logging.getLogger(__name__)


@dataclass
class OrderSpec:
    symbol: str
    action: str
    quantity: int
    stop_loss_underlying: float
    take_profit_underlying: float
    rationale: str


class RiskManager:
    def __init__(self, cfg: RiskConfig, options_cfg: OptionsConfig):
        self.cfg = cfg
        self.options_cfg = options_cfg
        self._trades_today = 0
        self._daily_loss = 0.0

    def reset_daily_counters(self) -> None:
        self._trades_today = 0
        self._daily_loss = 0.0

    def record_pnl(self, pnl_usd: float) -> None:
        if pnl_usd < 0:
            self._daily_loss += abs(pnl_usd)

    def evaluate(
        self,
        decision: TradeDecision,
        signal: Signal,
        positions: Dict[str, float],
        account_value: float,
    ) -> Optional[OrderSpec]:
        if decision.action == "HOLD":
            return None
        if decision.confidence < self.cfg.min_confidence:
            logger.info("Skipped: confidence %.2f < %.2f", decision.confidence, self.cfg.min_confidence)
            return None
        if self._trades_today >= self.cfg.max_trades_per_day:
            logger.warning("Skipped: max trades per day reached")
            return None
        if self._daily_loss >= self.cfg.max_daily_loss_usd:
            logger.warning("Skipped: daily loss limit reached")
            return None
        if decision.action == "BUY" and positions.get(signal.symbol, 0):
            logger.info("Skipped: existing position in %s", signal.symbol)
            return None
        if decision.action == "BUY" and not signal.bullish_alignment:
            logger.info("Skipped: bullish alignment no longer valid")
            return None

        quantity = max(1, int(round(decision.suggested_size_pct)))
        stop_loss_underlying = max(0.01, signal.close - max(signal.atr, 0.25))
        take_profit_underlying = signal.close + max(signal.atr * 2.0, 0.50)

        self._trades_today += 1
        return OrderSpec(
            symbol=signal.symbol,
            action=decision.action,
            quantity=quantity,
            stop_loss_underlying=stop_loss_underlying,
            take_profit_underlying=take_profit_underlying,
            rationale=decision.rationale,
        )
