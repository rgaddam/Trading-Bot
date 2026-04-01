from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Tuple


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class IBKRConfig:
    host: str = field(default_factory=lambda: _env_str("IB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("IB_PORT", 7497))
    client_id: int = field(default_factory=lambda: _env_int("IB_CLIENT_ID", 1))
    account: str = field(default_factory=lambda: _env_str("IB_ACCOUNT", ""))


@dataclass
class TimeConfig:
    windows: List[Tuple[Tuple[int, int], Tuple[int, int]]] = field(
        default_factory=lambda: [((9, 45), (11, 30)), ((13, 30), (15, 30))]
    )
    timezone: str = "America/New_York"


@dataclass
class IndicatorConfig:
    symbol: str = field(default_factory=lambda: _env_str("SYMBOL", "QQQ"))
    bar_size: str = field(default_factory=lambda: _env_str("BAR_SIZE", "10 mins"))
    lookback_bars: int = field(default_factory=lambda: _env_int("LOOKBACK_BARS", 80))
    ema_fast: int = field(default_factory=lambda: _env_int("EMA_FAST", 4))
    ema_slow: int = field(default_factory=lambda: _env_int("EMA_SLOW", 13))
    use_vwap: bool = field(default_factory=lambda: _env_bool("USE_VWAP", True))
    require_closed_candle: bool = True


@dataclass
class OptionsConfig:
    underlying: str = field(default_factory=lambda: _env_str("UNDERLYING", "QQQ"))
    option_type: str = field(default_factory=lambda: _env_str("OPTION_TYPE", "CALL"))
    moneyness: str = field(default_factory=lambda: _env_str("MONEYNESS", "ATM"))
    max_premium_usd: float = field(default_factory=lambda: _env_float("MAX_PREMIUM_USD", 1000.0))
    require_confirmation: bool = field(default_factory=lambda: _env_bool("REQUIRE_CONFIRMATION", True))


@dataclass
class RiskConfig:
    min_confidence: float = field(default_factory=lambda: _env_float("MIN_CONFIDENCE", 0.60))
    stop_loss_usd: float = field(default_factory=lambda: _env_float("STOP_LOSS_USD", 500.0))
    stop_on_ema_break: bool = field(default_factory=lambda: _env_bool("STOP_ON_EMA_BREAK", True))
    partial_profit_trigger_pct: float = field(default_factory=lambda: _env_float("PARTIAL_PROFIT_TRIGGER_PCT", 1.0))
    partial_profit_sell_pct: float = field(default_factory=lambda: _env_float("PARTIAL_PROFIT_SELL_PCT", 0.50))
    trail_remaining_on_ema: bool = field(default_factory=lambda: _env_bool("TRAIL_REMAINING_ON_EMA", True))
    max_trades_per_day: int = field(default_factory=lambda: _env_int("MAX_TRADES_PER_DAY", 2))
    max_daily_loss_usd: float = field(default_factory=lambda: _env_float("MAX_DAILY_LOSS_USD", 1400.0))
    max_concurrent_positions: int = field(default_factory=lambda: _env_int("MAX_CONCURRENT_POSITIONS", 1))
    no_averaging_down: bool = field(default_factory=lambda: _env_bool("NO_AVERAGING_DOWN", True))


@dataclass
class AIConfig:
    use_claude: bool = field(default_factory=lambda: _env_bool("USE_CLAUDE", True))
    model: str = field(default_factory=lambda: _env_str("CLAUDE_MODEL", "claude-sonnet-4-5"))
    max_tokens: int = field(default_factory=lambda: _env_int("CLAUDE_MAX_TOKENS", 512))
    instructions: str = """
You are a disciplined options trading assistant focused on QQQ ATM CALL options only.

Rules:
- Use only the supplied technical snapshot.
- BUY only when the most recent CLOSED candle is above EMA fast, EMA slow, and VWAP.
- Default to HOLD when uncertain.
- Return concise JSON only.

Output schema:
{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": <float 0.0-1.0>,
  "rationale": "<2 short sentences max>",
  "suggested_size_pct": <float 0.0-1.0>
}
""".strip()


@dataclass
class SafetyConfig:
    dry_run: bool = field(default_factory=lambda: _env_bool("DRY_RUN", True))
    paper_trading: bool = field(default_factory=lambda: _env_bool("PAPER_TRADING", True))
    enable_live_orders: bool = field(default_factory=lambda: _env_bool("ENABLE_LIVE_ORDERS", False))
    allow_non_localhost_ib: bool = field(default_factory=lambda: _env_bool("ALLOW_NON_LOCALHOST_IB", False))


@dataclass
class BotConfig:
    agent_name: str = "ema-vwap-options-agent"
    description: str = "QQQ call options bot with repo-safe production hardening"
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    time: TimeConfig = field(default_factory=TimeConfig)
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    options: OptionsConfig = field(default_factory=OptionsConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    log_file: str = field(default_factory=lambda: _env_str("LOG_FILE", "trading_bot.log"))


def get_config() -> BotConfig:
    return BotConfig()
