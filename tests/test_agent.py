#!/usr/bin/env python3
"""Smoke tests for the StockMaxx Agent risk guard and signal engine.

Run: python3 tests/test_agent.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from stockmaxx_agent import Portfolio, Position, Quote, RiskGuard, SignalEngine  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "config.json")) as fh:
    CFG = json.load(fh)


def q(ticker, price):
    return Quote(ticker, ticker, price, 1.0, 9999999999.0, "test")


def test_position_cap_blocks_oversized_buy():
    guard = RiskGuard(CFG["risk"])
    pf = Portfolio(cash=1000.0)
    quotes = {"NVDA": q("NVDA", 100.0)}
    ok, why = guard.check_buy(pf, quotes, "NVDA", 500.0)  # 50% > 20% cap
    assert not ok and "position cap" in why, why


def test_small_buy_passes():
    guard = RiskGuard(CFG["risk"])
    pf = Portfolio(cash=1000.0)
    quotes = {"NVDA": q("NVDA", 100.0)}
    ok, why = guard.check_buy(pf, quotes, "NVDA", 150.0)  # 15% <= 20%
    assert ok, why


def test_kill_switch_blocks_everything():
    cfg = dict(CFG["risk"], kill_switch=True)
    guard = RiskGuard(cfg)
    pf = Portfolio(cash=1000.0)
    quotes = {"NVDA": q("NVDA", 100.0)}
    ok, why = guard.check_buy(pf, quotes, "NVDA", 10.0)
    assert not ok and "kill switch" in why


def test_stop_loss_triggers():
    guard = RiskGuard(CFG["risk"])
    pos = Position("NVDA", shares=2.0, avg_price=100.0)
    reason = guard.exit_reason(pos, 91.0)  # -9% <= -8%
    assert reason and "stop-loss" in reason


def test_stale_nav_blocks_signal():
    eng = SignalEngine()
    quote = q("NVDA", 100.0)
    quote.nav_updated_at = 0.0  # ancient
    for price in (100.0, 101.0, 102.0, 103.0):
        quote.nav_price = price
        eng.observe(quote)
    sig = eng.score(quote, now=10000.0, max_staleness=3600)
    assert sig.score == 0.0 and "stale" in sig.reason


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"{len(fns)} tests passed")
