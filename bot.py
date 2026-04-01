from __future__ import annotations

import logging
import os
import signal as os_signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from ai_layer import AILayer, RuleBasedLayer
from config import get_config
from data_fetcher import DataFetcher
from order_executor import OrderExecutor
from risk_manager import RiskManager
from signal_engine import SignalEngine


def setup_logging(log_file: str) -> None:
    fmt = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_file, mode="a")],
    )


logger = logging.getLogger("bot")


class TradingBot:
    LOOP_INTERVAL_SECONDS = 300

    def __init__(self):
        self.cfg = get_config()
        self._running = False
        self.fetcher = DataFetcher(self.cfg.ibkr, self.cfg.indicators, self.cfg.safety)
        self.signals = SignalEngine(self.cfg.indicators.ema_fast, self.cfg.indicators.ema_slow)
        self.risk = RiskManager(self.cfg.risk, self.cfg.options)
        self.ai = self._build_ai_layer()
        self.executor: OrderExecutor | None = None

    def _build_ai_layer(self):
        if self.cfg.ai.use_claude and os.getenv("ANTHROPIC_API_KEY"):
            logger.info("Using Claude model %s", self.cfg.ai.model)
            return AILayer(self.cfg.ai.model, self.cfg.ai.max_tokens, self.cfg.ai.instructions)
        logger.info("Using rule-based fallback layer")
        return RuleBasedLayer()

    def start(self) -> None:
        setup_logging(self.cfg.log_file)
        self._register_signals()
        self.fetcher.connect()
        self.executor = OrderExecutor(self.fetcher.ib, self.cfg.options, self.cfg.safety)
        logger.info("Bot starting dry_run=%s paper_trading=%s live_orders=%s", self.cfg.safety.dry_run, self.cfg.safety.paper_trading, self.cfg.safety.enable_live_orders)
        self._running = True
        while self._running:
            try:
                self.run_cycle()
            except Exception as exc:
                logger.error("Cycle failed: %s", exc, exc_info=True)
            time.sleep(self.LOOP_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False
        self.fetcher.disconnect()
        logger.info("Bot stopped.")

    def _within_trading_window(self) -> bool:
        now = datetime.now(ZoneInfo(self.cfg.time.timezone))
        hm = (now.hour, now.minute)
        for start, end in self.cfg.time.windows:
            if start <= hm <= end:
                return True
        return False

    def run_cycle(self) -> None:
        logger.info("Cycle start")
        if not self._within_trading_window():
            logger.info("Outside allowed trading window; skipping cycle")
            return

        account_value = self.fetcher.get_account_value()
        positions = self.fetcher.get_positions()
        symbol = self.cfg.indicators.symbol

        df = self.fetcher.fetch_bars(symbol)
        if df.empty:
            logger.warning("No bars returned for %s", symbol)
            return

        signal = self.signals.compute(symbol, df)
        if signal is None:
            return

        decision = self.ai.decide(signal, positions, account_value)
        logger.info("Decision action=%s confidence=%.2f rationale=%s", decision.action, decision.confidence, decision.rationale)

        spec = self.risk.evaluate(decision, signal, positions, account_value)
        if spec is None:
            logger.info("No order generated this cycle")
            return

        if self.executor is None:
            raise RuntimeError("Executor not initialized")
        self.executor.execute(spec)

    def _register_signals(self) -> None:
        os_signal.signal(os_signal.SIGINT, self._handle_signal)
        os_signal.signal(os_signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        logger.info("Received signal %s", signum)
        self.stop()
        sys.exit(0)


if __name__ == "__main__":
    TradingBot().start()
