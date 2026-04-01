from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    symbol: str
    close: float
    prev_close: float
    ema_fast: float
    ema_slow: float
    vwap: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    atr: float
    volume: float
    avg_volume: float

    @property
    def bullish_alignment(self) -> bool:
        return self.close > self.ema_fast > self.ema_slow and self.close > self.vwap

    @property
    def bearish_alignment(self) -> bool:
        return self.close < self.ema_fast < self.ema_slow and self.close < self.vwap

    @property
    def rsi_oversold(self) -> bool:
        return self.rsi < 30

    @property
    def rsi_overbought(self) -> bool:
        return self.rsi > 70

    def summary(self) -> str:
        return (
            f"{self.symbol} close={self.close:.2f} "
            f"ema_fast={self.ema_fast:.2f} ema_slow={self.ema_slow:.2f} "
            f"vwap={self.vwap:.2f} rsi={self.rsi:.1f} macd_hist={self.macd_hist:+.4f}"
        )


class SignalEngine:
    def __init__(self, ema_fast: int = 4, ema_slow: int = 13):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow

    def compute(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        if df is None or df.empty or len(df) < 30:
            logger.warning("Not enough data for %s", symbol)
            return None

        try:
            work = df.copy()
            required = {"open", "high", "low", "close", "volume"}
            if not required.issubset(set(work.columns)):
                raise ValueError(f"missing columns: {required - set(work.columns)}")

            c = work["close"]
            h = work["high"]
            l = work["low"]
            v = work["volume"]

            ema_fast = ta.ema(c, length=self.ema_fast)
            ema_slow = ta.ema(c, length=self.ema_slow)
            vwap = ta.vwap(high=h, low=l, close=c, volume=v)
            rsi = ta.rsi(c, length=14)
            macd_df = ta.macd(c, fast=12, slow=26, signal=9)
            atr = ta.atr(h, l, c, length=14)
            avg_vol = v.rolling(20).mean()

            macd_col = next(col for col in macd_df.columns if col.startswith("MACD_"))
            macds_col = next(col for col in macd_df.columns if col.startswith("MACDs_"))
            macdh_col = next(col for col in macd_df.columns if col.startswith("MACDh_"))

            idx = -1
            signal = Signal(
                symbol=symbol,
                close=float(c.iloc[idx]),
                prev_close=float(c.iloc[-2]),
                ema_fast=float(ema_fast.iloc[idx]),
                ema_slow=float(ema_slow.iloc[idx]),
                vwap=float(vwap.iloc[idx]),
                rsi=float(rsi.iloc[idx]),
                macd=float(macd_df[macd_col].iloc[idx]),
                macd_signal=float(macd_df[macds_col].iloc[idx]),
                macd_hist=float(macd_df[macdh_col].iloc[idx]),
                atr=float(atr.iloc[idx]),
                volume=float(v.iloc[idx]),
                avg_volume=float(avg_vol.iloc[idx]),
            )
            logger.info("Signal %s", signal.summary())
            return signal
        except Exception as exc:
            logger.error("Signal computation failed for %s: %s", symbol, exc, exc_info=True)
            return None
