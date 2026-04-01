# QQQ EMA + VWAP Trading Bot — Hardened Repo Package

This package is a **production-hardening pass for repo safety and runtime guardrails**.

It fixes:
- hardcoded account IDs
- env-based configuration
- dry-run / paper-trading guards
- cleaner logging
- safer IBKR connection handling
- better signal alignment around **EMA(4), EMA(13), and VWAP**
- safer AI JSON parsing

## Important truth

This package is **safe to put in GitHub** and **safer to run locally**.

It is **not yet a fully production-safe live options execution engine**.

Why:
- the original project evaluates **QQQ underlying bars**
- it does **not yet contain a fully tested option-chain resolver**
- it does **not yet manage real option premium-aware bracket exits**
- it does **not yet reconcile fills / partial fills / option Greeks / slippage**

So this hardened version intentionally keeps execution in **dry-run / paper-safe mode** unless you build the option execution layer.

## Files included

- `config.py`
- `signal_engine.py`
- `ai_layer.py`
- `data_fetcher.py`
- `risk_manager.py`
- `order_executor.py`
- `bot.py`
- `.gitignore`
- `.env.example`
- `requirements.txt`
- `README.md`

## What to replace in your repo

Replace these existing files with the versions from this zip:

- `config.py`
- `signal_engine.py`
- `ai_layer.py`
- `data_fetcher.py`
- `risk_manager.py`
- `order_executor.py`
- `bot.py`
- `requirements.txt`
- `README.md`

Add:
- `.gitignore`
- `.env.example`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your paper account details.

## Safe run

```bash
python bot.py
```

Default safety:
- `DRY_RUN=true`
- `PAPER_TRADING=true`
- `ENABLE_LIVE_ORDERS=false`

## Before Git push

Remove junk:

```bash
rm -rf .venv __pycache__ __MACOSX
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete
find . -name "*.log" -delete
rm -f *.dmg
```

Then:

```bash
git init
git branch -M main
git add .
git commit -m "Harden trading bot repo"
git remote add origin https://github.com/YOUR_USERNAME/trading-bot.git
git push -u origin main
```

## Next step to make it truly live-options ready

You still need:
1. real option contract selection
2. premium-aware position sizing
3. tested take-profit / stop-loss handling on option premiums
4. fill reconciliation and order status tracking
5. reconnect + retry logic
6. trade journal persistence
7. alerting / monitoring

That is the point where it becomes **live-options production work**, not just repo cleanup.
