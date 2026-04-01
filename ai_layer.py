from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Literal

import anthropic

from signal_engine import Signal

logger = logging.getLogger(__name__)

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass
class TradeDecision:
    action: Action
    confidence: float
    rationale: str
    suggested_size_pct: float


def _safe_json_parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    return json.loads(text)


def _build_user_prompt(signal: Signal, positions: dict, account_value: float) -> str:
    pos = positions.get(signal.symbol, 0)
    return f"""Evaluate this QQQ setup.

Technical snapshot:
- Symbol: {signal.symbol}
- Close: {signal.close:.2f}
- Previous close: {signal.prev_close:.2f}
- EMA fast: {signal.ema_fast:.2f}
- EMA slow: {signal.ema_slow:.2f}
- VWAP: {signal.vwap:.2f}
- RSI: {signal.rsi:.1f}
- MACD hist: {signal.macd_hist:+.4f}
- ATR: {signal.atr:.3f}
- Volume: {signal.volume:,.0f}
- Avg volume: {signal.avg_volume:,.0f}
- Bullish alignment: {signal.bullish_alignment}

Account context:
- Net liquidation: ${account_value:,.2f}
- Current position proxy in {signal.symbol}: {pos}

Respond with JSON only.
""".strip()


class AILayer:
    def __init__(self, model: str, max_tokens: int, system_prompt: str):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def decide(self, signal: Signal, positions: dict, account_value: float) -> TradeDecision:
        raw = ""
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": _build_user_prompt(signal, positions, account_value)}],
            )
            raw = resp.content[0].text
            data = _safe_json_parse(raw)
            action = str(data.get("action", "HOLD")).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            return TradeDecision(
                action=action,
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
                rationale=str(data.get("rationale", ""))[:300],
                suggested_size_pct=max(0.0, min(1.0, float(data.get("suggested_size_pct", 0.0)))),
            )
        except Exception as exc:
            logger.error("AI decision failed: %s | raw=%r", exc, raw, exc_info=True)
            return TradeDecision("HOLD", 0.0, "AI layer failed; default HOLD.", 0.0)


class RuleBasedLayer:
    def decide(self, signal: Signal, positions: dict, account_value: float) -> TradeDecision:
        if signal.bullish_alignment and signal.macd_hist > 0 and not signal.rsi_overbought:
            if positions.get(signal.symbol, 0) == 0:
                return TradeDecision("BUY", 0.72, "Bullish EMA/VWAP alignment with positive momentum.", 1.0)
        return TradeDecision("HOLD", 0.40, "No strong setup.", 0.0)
