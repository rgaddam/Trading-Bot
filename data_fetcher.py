from __future__ import annotations

import logging
from typing import Dict

import pandas as pd
from ib_insync import IB, Stock, util

from config import IBKRConfig, IndicatorConfig, SafetyConfig

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, ibkr_cfg: IBKRConfig, trading_cfg: IndicatorConfig, safety_cfg: SafetyConfig):
        self.cfg = ibkr_cfg
        self.tcfg = trading_cfg
        self.safety = safety_cfg
        self.ib = IB()
        self.account = ibkr_cfg.account

    def connect(self) -> None:
        if self.cfg.host not in {"127.0.0.1", "localhost"} and not self.safety.allow_non_localhost_ib:
            raise RuntimeError("Refusing non-localhost IB connection. Set ALLOW_NON_LOCALHOST_IB=true to override.")
        self.ib.connect(host=self.cfg.host, port=self.cfg.port, clientId=self.cfg.client_id, readonly=False, timeout=10)
        if not self.ib.isConnected():
            raise RuntimeError("IBKR connection failed")
        managed = self.ib.managedAccounts()
        if not self.account:
            if len(managed) == 1:
                self.account = managed[0]
                logger.info("Auto-selected IB account %s", self.account)
            elif len(managed) > 1:
                raise RuntimeError(f"Multiple IB accounts available; set IB_ACCOUNT explicitly: {managed}")
        logger.info("Connected to IBKR host=%s port=%s clientId=%s account=%s", self.cfg.host, self.cfg.port, self.cfg.client_id, self.account)

    def disconnect(self) -> None:
        if self.ib.isConnected():
            self.ib.disconnect()

    def get_contract(self, symbol: str) -> Stock:
        contract = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        return contract

    def fetch_bars(self, symbol: str) -> pd.DataFrame:
        contract = self.get_contract(symbol)
        duration = self._bars_to_duration(self.tcfg.lookback_bars, self.tcfg.bar_size)
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=self.tcfg.bar_size,
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        df = util.df(bars)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()

    def get_account_value(self) -> float:
        values = self.ib.accountValues(self.account)
        for v in values:
            if v.tag == "NetLiquidation" and v.currency == "USD":
                return float(v.value)
        return 0.0

    def get_positions(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for pos in self.ib.positions(self.account):
            out[pos.contract.symbol] = pos.position
        return out

    @staticmethod
    def _bars_to_duration(n_bars: int, bar_size: str) -> str:
        minutes_per_bar = {
            "1 min": 1, "2 mins": 2, "3 mins": 3, "5 mins": 5,
            "10 mins": 10, "15 mins": 15, "20 mins": 20, "30 mins": 30,
            "1 hour": 60, "2 hours": 120, "1 day": 390,
        }
        total_minutes = n_bars * minutes_per_bar.get(bar_size, 10)
        total_days = max(1, total_minutes // 390 + 1)
        if total_days <= 7:
            return f"{total_days} D"
        if total_days <= 30:
            return f"{(total_days // 7) + 1} W"
        return f"{(total_days // 30) + 1} M"
