# StockMaxx Agent

An AI agent for **tokenized-stock finance on Base**, built for the
**Base "Stocks Maxxing" Builder Quest — Agentic Stock Finance track**.

The agent watches tokenized stocks on Base, scores them with a radar-style
signal engine, and manages a portfolio under hard, non-negotiable risk caps.
This build runs end-to-end on **Base Sepolia (testnet)** with a paper
portfolio: no real funds, no real orders, nothing to lose — and the rules of
the Quest explicitly say testnet submissions are not judged less favorably.

## What it does

1. **Data** — reads tokenized-stock reference data the way Base documents it:
   the public, read-only Tokenized Stocks API (`docs.base.org/sdks/tokenized-stocks`)
   for token contracts, supply, `multiplier`, and Chainlink-based
   `nav_price`. If no API base URL is configured, it falls back to a clearly
   labelled reference universe (demo data).
2. **Signals** — a momentum + consistency score per name, with a
   **NAV-staleness guard**: Base docs warn that `nav_price` is a reference
   value (not an execution price) that can go stale outside market hours, so
   any name whose NAV is older than the configured bound is blocked, not
   traded.
3. **Risk guard** — every order must pass: max 20% per position, max 60%
   total exposure, −8% stop-loss, +15% take-profit, and a kill switch.
   The guard can veto the signal engine, and in the demo it visibly does.
4. **Execution (adapter)** — the demo adapter is a paper executor that writes
   every intent to an append-only ledger anchored to the **live Base Sepolia
   block height** at decision time. Positions are tracked in share-equivalent
   units via the token `multiplier` (the `balanceOfUI` concept from the Base
   docs). A mainnet router adapter (Aerodrome) exists only as a disabled
   stub: turning it on is a human decision requiring a funded wallet and
   explicit approval.
5. **Report** — end-of-run portfolio summary: cash, positions, exposure,
   intent count, ledger path.

## Run it

```bash
python3 src/stockmaxx_agent.py --ticks 10
python3 tests/test_agent.py   # 5 risk/signal smoke tests
```

Stdlib only — no dependencies, no API keys, no wallet keys.

## Layout

- `src/stockmaxx_agent.py` — the whole agent (data, signals, risk, execution)
- `config.json` — network, reference universe, risk caps
- `tests/test_agent.py` — guard + signal smoke tests
- `data/intent_ledger.json` — generated intent ledger (testnet paper trades)
- `output/demo_transcript.txt` — a real recorded demo run
- `video/demo.mp4` — 1-minute demo video used in the X post

## Quest notes

- Track: **Agentic Stock Finance** (one submission per track).
- Entry = public X post with this demo video tagging **@buildonbase** +
  the official submission form, before the deadline (see
  `submission-answers.md` for prepared answers).
- Scoring (per the Quest page as reported at launch): **50% traction**
  (real onchain usage), **25% product quality**, **25% building in public**.
- No token launch is required or planned. Launching a token is optional in
  this Quest, and this project does not launch one.
- The agent is a single-operator portfolio agent for its owner's wallet. It
  is not a public trading service and does not offer trading to anyone else.

## Disclaimer

Demo software. Paper trading on a testnet. Not financial advice, not an
offer of any security or tokenized asset, and no relationship with or
endorsement by Base, Coinbase, or any issuer is claimed.
