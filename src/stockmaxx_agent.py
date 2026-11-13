#!/usr/bin/env python3
"""
StockMaxx Agent - an agentic stock-finance demo for Base.

Track: Base "Stocks Maxxing" Builder Quest - Agentic Stock Finance.

What it does
------------
1. Watches a universe of tokenized stocks on Base (Coinbase-issued tokenized
   stocks, read through the public Tokenized Stocks API described at
   docs.base.org/sdks/tokenized-stocks; falls back to a clearly labelled
   reference universe when the API base URL is not configured).
2. Scores each name with a radar-style signal engine (momentum + activity +
   NAV-staleness guard, following the Base docs guidance: nav_price is a
   Chainlink-based reference value, not an execution price, and must be
   staleness-checked before use).
3. Passes every candidate order through a hard risk guard (position cap,
   total-exposure cap, stop-loss, take-profit, kill switch).
4. Executes through an adapter interface. The demo adapter is a paper
   executor anchored to live Base Sepolia block height: every intent is
   written to an append-only ledger with the testnet block it was decided
   at. A mainnet router adapter (Aerodrome) is stubbed behind an explicit
   flag and is NEVER used by the demo - no real funds, ever, without a
   human turning it on.

Positions are tracked in share-equivalent units using the token
`multiplier`, mirroring the onchain `balanceOfUI` concept from the Base
docs (raw balance x current multiplier).

Stdlib only. Run:  python3 src/stockmaxx_agent.py --ticks 8
"""

import argparse
import json
import math
import os
import random
import sys
import time
import urllib.request
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")
LEDGER_PATH = os.path.join(ROOT, "data", "intent_ledger.json")


# ---------------------------------------------------------------- chain I/O
def rpc_call(urls, method, params):
    """Minimal JSON-RPC client with endpoint fallback. Returns (result, url)."""
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last_err = None
    for url in urls:
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "stockmaxx-agent/0.1"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
            if "result" in body:
                return body["result"], url
            last_err = body.get("error")
        except Exception as exc:  # noqa: BLE001 - fallback across endpoints
            last_err = exc
    raise RuntimeError(f"RPC {method} failed on all endpoints: {last_err}")


# ---------------------------------------------------------------- data layer
@dataclass
class Quote:
    ticker: str
    name: str
    nav_price: float
    multiplier: float
    nav_updated_at: float  # epoch seconds
    source: str             # "api" or "reference-demo"


class TokenizedStocksClient:
    """Reads tokenized-stock reference data.

    Live mode uses the public Tokenized Stocks API (read-only, no key).
    The base URL is deployment-specific, so it is taken from the
    TOKENIZED_STOCKS_API_BASE env var / config; without it we use the
    reference universe and label quotes as demo data.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.base_url = os.environ.get("TOKENIZED_STOCKS_API_BASE", "").rstrip("/")

    def list_quotes(self):
        if self.base_url:
            try:
                with urllib.request.urlopen(f"{self.base_url}/?page_size=100", timeout=15) as resp:
                    data = json.loads(resp.read())
                quotes = []
                for tok in data.get("tokens", []):
                    if not tok.get("nav_price"):
                        continue  # docs: never treat missing NAV as a price
                    quotes.append(Quote(
                        ticker=tok["symbol"], name=tok.get("name", tok["symbol"]),
                        nav_price=float(tok["nav_price"]),
                        multiplier=float(tok.get("multiplier", 1.0)),
                        nav_updated_at=float(tok.get("nav_price_updated_at", time.time())),
                        source="api",
                    ))
                if quotes:
                    return quotes
            except Exception as exc:  # noqa: BLE001
                print(f"[data] Tokenized Stocks API unreachable ({exc}); using reference universe")
        now = time.time()
        return [Quote(t["ticker"], t["name"], float(t["nav_price"]), float(t["multiplier"]), now, "reference-demo")
                for t in self.cfg["reference_universe"]]


class DemoFeed:
    """Deterministic per-ticker price walk for the demo (seeded, reproducible)."""

    def __init__(self, universe_cfg, seed=42):
        self.rng = {t["ticker"]: random.Random(seed + hash(t["ticker"]) % 1000) for t in universe_cfg}
        self.vol = {t["ticker"]: t["volatility"] for t in universe_cfg}
        self.drift = {t["ticker"]: self.rng[t["ticker"]].uniform(-0.001, 0.004) for t in universe_cfg}

    def step(self, quote: Quote) -> Quote:
        r = self.rng[quote.ticker]
        shock = r.gauss(self.drift[quote.ticker], self.vol[quote.ticker])
        quote.nav_price = round(quote.nav_price * (1 + shock), 4)
        quote.nav_updated_at = time.time()
        return quote


# ---------------------------------------------------------------- signals
@dataclass
class Signal:
    ticker: str
    score: float        # 0..1 composite
    momentum: float     # fractional change over the lookback window
    reason: str


class SignalEngine:
    """Radar-style scoring, the same pattern we use for on-chain hunting:
    momentum + sustained direction, never a single green candle."""

    def __init__(self, lookback=5):
        self.history = {}
        self.lookback = lookback

    def observe(self, quote: Quote):
        self.history.setdefault(quote.ticker, []).append(quote.nav_price)

    def score(self, quote: Quote, now: float, max_staleness: float):
        hist = self.history.get(quote.ticker, [])
        if len(hist) < 3:
            return Signal(quote.ticker, 0.0, 0.0, "warming up (need >=3 observations)")
        window = hist[-self.lookback:] if len(hist) >= self.lookback else hist
        momentum = (window[-1] - window[0]) / window[0]
        consistency = sum(1 for a, b in zip(window, window[1:]) if b >= a) / max(1, len(window) - 1)
        score = max(0.0, min(1.0, 0.5 + momentum * 18)) * (0.6 + 0.4 * consistency)
        stale_for = now - quote.nav_updated_at
        if stale_for > max_staleness:
            return Signal(quote.ticker, 0.0, momentum, f"BLOCKED: NAV stale {stale_for:.0f}s > {max_staleness:.0f}s")
        return Signal(quote.ticker, round(score, 3), momentum,
                      f"momentum {momentum*100:+.2f}% over {len(window)} ticks, consistency {consistency:.2f}")


# ---------------------------------------------------------------- risk
@dataclass
class Position:
    ticker: str
    shares: float = 0.0          # share-equivalent units (multiplier applied)
    avg_price: float = 0.0


@dataclass
class Portfolio:
    cash: float
    positions: dict = field(default_factory=dict)

    def value(self, quotes):
        total = self.cash
        for tick, pos in self.positions.items():
            if pos.shares and tick in quotes:
                total += pos.shares * quotes[tick].nav_price
        return total

    def exposure_pct(self, quotes):
        v = self.value(quotes)
        if v <= 0:
            return 0.0
        invested = sum(p.shares * quotes[t].nav_price for t, p in self.positions.items() if p.shares and t in quotes)
        return 100.0 * invested / v


class RiskGuard:
    def __init__(self, cfg):
        self.cfg = cfg

    def check_buy(self, pf: Portfolio, quotes, ticker, usd_amount):
        if self.cfg["kill_switch"]:
            return False, "kill switch ON"
        if usd_amount <= 0:
            return False, "non-positive amount"
        price = quotes[ticker].nav_price
        qmap = {t: q for t, q in quotes.items()}
        total_after = pf.value(qmap)
        pos_after = (pf.positions.get(ticker, Position(ticker)).shares * price) + usd_amount
        if 100.0 * pos_after / total_after > self.cfg["max_position_pct"]:
            return False, f"position cap {self.cfg['max_position_pct']}% would be breached"
        invested_after = sum(p.shares * qmap[t].nav_price for t, p in pf.positions.items() if p.shares) + usd_amount
        if 100.0 * invested_after / total_after > self.cfg["max_total_exposure_pct"]:
            return False, f"total exposure cap {self.cfg['max_total_exposure_pct']}% would be breached"
        return True, "ok"

    def exit_reason(self, pos: Position, price: float):
        if pos.shares <= 0 or pos.avg_price <= 0:
            return None
        pnl = (price - pos.avg_price) / pos.avg_price * 100.0
        if pnl <= self.cfg["stop_loss_pct"]:
            return f"stop-loss hit ({pnl:+.2f}% <= {self.cfg['stop_loss_pct']}%)"
        if pnl >= self.cfg["take_profit_pct"]:
            return f"take-profit hit ({pnl:+.2f}% >= {self.cfg['take_profit_pct']}%)"
        return None


# ---------------------------------------------------------------- execution
@dataclass
class Intent:
    side: str
    ticker: str
    usd_amount: float
    price: float
    shares: float
    reason: str
    block: int
    status: str = "RECORDED"


class PaperExecutor:
    """Demo executor: records intents to an append-only ledger anchored to
    the live Base Sepolia block height. No keys, no funds, no broadcasts."""

    def __init__(self, ledger_path=LEDGER_PATH):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
        self.entries = []
        if os.path.exists(ledger_path):
            with open(ledger_path) as fh:
                self.entries = json.load(fh)

    def execute(self, intent: Intent):
        self.entries.append(vars(intent))
        with open(self.ledger_path, "w") as fh:
            json.dump(self.entries, fh, indent=2)
        return intent


class MainnetRouterExecutor:
    """Placeholder for the real thing (Aerodrome router on Base mainnet).

    Deliberately unusable in the demo: constructing it is fine, executing
    raises. Turning this on is a human decision - it needs a funded wallet,
    slippage bounds, and the operator's explicit go-ahead.
    """

    def execute(self, intent: Intent):
        raise RuntimeError("Mainnet execution is disabled in this build (demo/testnet only).")


# ---------------------------------------------------------------- agent
class StockMaxxAgent:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = TokenizedStocksClient(cfg)
        self.engine = SignalEngine()
        self.guard = RiskGuard(cfg["risk"])
        self.executor = PaperExecutor()
        self.pf = Portfolio(cash=cfg["paper_portfolio"]["starting_cash_usd"])
        self.feed = DemoFeed(cfg["reference_universe"])

    def chain_block(self):
        result, url = rpc_call(self.cfg["network"]["rpc_urls"], "eth_blockNumber", [])
        return int(result, 16), url

    def run(self, ticks=8, sleep_s=0.6):
        quotes_list = self.client.list_quotes()
        quotes = {q.ticker: q for q in quotes_list}
        src = quotes_list[0].source if quotes_list else "n/a"
        print("=" * 74)
        print("StockMaxx Agent - Agentic Stock Finance on Base (TESTNET DEMO)")
        print(f"Universe source: {src} | names: {', '.join(sorted(quotes))}")
        try:
            block, url = self.chain_block()
            print(f"Base Sepolia live block: {block} (via {url})")
        except RuntimeError as exc:
            block = -1
            print(f"Base Sepolia RPC unreachable, continuing offline: {exc}")
        print(f"Paper portfolio: ${self.pf.cash:,.2f} | risk caps: "
              f"{self.cfg['risk']['max_position_pct']}%/position, "
              f"{self.cfg['risk']['max_total_exposure_pct']}% total, "
              f"SL {self.cfg['risk']['stop_loss_pct']}%, TP {self.cfg['risk']['take_profit_pct']}%")
        print("=" * 74)

        for tick in range(1, ticks + 1):
            for q in quotes.values():
                self.feed.step(q)
                self.engine.observe(q)
            try:
                block, _ = self.chain_block()
            except RuntimeError:
                pass
            print(f"\n-- tick {tick} | Base Sepolia block {block if block >= 0 else 'n/a'} --")

            # exits first (risk before opportunity)
            for ticker, pos in list(self.pf.positions.items()):
                if pos.shares <= 0:
                    continue
                reason = self.guard.exit_reason(pos, quotes[ticker].nav_price)
                if reason:
                    usd = pos.shares * quotes[ticker].nav_price
                    intent = Intent("SELL", ticker, round(usd, 2), quotes[ticker].nav_price,
                                    round(pos.shares, 6), reason, block)
                    self.executor.execute(intent)
                    self.pf.cash += usd
                    print(f"  EXIT  {ticker:<5} ${usd:>9,.2f} @ {intent.price:>8.2f}  {reason}")
                    pos.shares = 0.0
                    pos.avg_price = 0.0

            # entries by strongest signal
            signals = [self.engine.score(q, time.time(), self.cfg["risk"]["max_nav_staleness_seconds"])
                       for q in quotes.values()]
            signals.sort(key=lambda s: s.score, reverse=True)
            for sig in signals:
                mark = ""
                if sig.score >= self.cfg["risk"]["min_momentum_score"]:
                    # size under the per-position cap so the guard is a real
                    # check, not a guaranteed block: 90% of the cap, in cash terms
                    cap_usd = self.pf.value(quotes) * self.cfg["risk"]["max_position_pct"] / 100.0 * 0.9
                    budget = min(self.pf.cash * 0.25, cap_usd)
                    pos = self.pf.positions.get(sig.ticker)
                    if pos is None or pos.shares <= 0:
                        ok, why = self.guard.check_buy(self.pf, quotes, sig.ticker, budget)
                        if ok and budget > 50:
                            price = quotes[sig.ticker].nav_price
                            shares = budget / price * quotes[sig.ticker].multiplier
                            intent = Intent("BUY", sig.ticker, round(budget, 2), price,
                                            round(shares, 6), f"signal {sig.score}: {sig.reason}", block)
                            self.executor.execute(intent)
                            self.pf.cash -= budget
                            self.pf.positions[sig.ticker] = Position(sig.ticker, shares, price)
                            mark = f"  -> BUY ${budget:,.2f} ({shares:.4f} share-equiv)"
                        else:
                            mark = f"  -> blocked by risk guard: {why}"
                print(f"  {sig.ticker:<5} score {sig.score:.3f}  {sig.reason}{mark}")
            time.sleep(sleep_s)

        total = self.pf.value(quotes)
        print("\n" + "=" * 74)
        print("PORTFOLIO SUMMARY (paper, testnet)")
        print(f"  cash:        ${self.pf.cash:>10,.2f}")
        for ticker, pos in sorted(self.pf.positions.items()):
            if pos.shares:
                print(f"  {ticker:<5} {pos.shares:>10.4f} share-equiv @ avg {pos.avg_price:>8.2f} "
                      f"(now {quotes[ticker].nav_price:>8.2f})")
        print(f"  total value: ${total:>10,.2f}  (start $10,000.00, "
              f"{(total/10000-1)*100:+.2f}%)")
        print(f"  exposure:    {self.pf.exposure_pct(quotes):.1f}% | intents recorded: {len(self.executor.entries)}")
        print(f"  ledger:      {self.executor.ledger_path}")
        print("  NOTE: demo only - no real orders, no real funds, no financial advice.")
        print("=" * 74)
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="StockMaxx Agent demo")
    ap.add_argument("--ticks", type=int, default=8)
    ap.add_argument("--sleep", type=float, default=0.6)
    args = ap.parse_args(argv)
    with open(CONFIG_PATH) as fh:
        cfg = json.load(fh)
    agent = StockMaxxAgent(cfg)
    return agent.run(ticks=args.ticks, sleep_s=args.sleep)


if __name__ == "__main__":
    sys.exit(main())
