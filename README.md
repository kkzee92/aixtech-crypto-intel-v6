# AIxTech crypto intel: paper-only trading information system (v0.6)

Research harness for automated cryptocurrency **information** and paper strategy
evaluation. It does not place live orders, does not store exchange secrets, and
is not financial advice.

Builds on [kkzee92/aixtech-crypto-intel-v5](https://github.com/kkzee92/aixtech-crypto-intel-v5) and the [zeekiankok92](https://github.com/zeekiankok92) AI-agent harness practices.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![version](https://img.shields.io/badge/version-0.6.0-blue)
![mode](https://img.shields.io/badge/execution-paper%20only-orange)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## What it does

- Classifies markets into eight asset classes and applies a different research rule to each, now with options-style defined-risk proxies and advanced correlation sizing.
- Labels each series trend, range, or stress, and stands aside in stress.
- Scores a signal with multi-factor confirmation plus adaptive volatility scaling, trend-strength proxy, MACD-style histogram, multi-TF consistency, stochastic oscillator proxy, volume-delta proxy, and correlation-adjusted sizing (v0.6), then a risk gate that can shrink or refuse it.
- Applies a declared round-trip cost by asset class in the paper backtest.
- Writes a hash-chained audit log with UTC timestamps, lineage stamp (optional sealed digest), consecutive-action counter, rate-based anomaly detection, zero-trust policy checks, attests fixture sources, and redacts secret-like strings (expanded further).
- Backtests on **synthetic** candles only. Network access is injectable and unused by default.

| Asset class | Research rule | Risk cap | Cost |
|---|---|---|---|
| Major (BTC, ETH) | Multi-factor EMA + strength + MACD + multi-TF + stochastic + vol-delta outside stress; range-only RSI + BB + stoch reversion; adaptive vol scale + corr adjust | 8% | 8 bps |
| Large-cap alt | Breakout with volume, BB, strength, MACD, stochastic, and vol-delta, suppressed in stress | 4% | 14 bps |
| Stablecoin | 20 bp watch, 50 bp depeg alert. No order | 0% | n/a |
| DeFi | Trend only in a calm, non-stress regime with volume + corr note + options proxy for vol spikes | 2% | 22 bps |
| Meme | Qualified burst with volume spike vs longer avg, chase filter, 3-bar horizon, strict corr | 0.5% | 45 bps |
| L2 | Relative strength versus a non-stress benchmark + vol-delta | 3% | 16 bps |
| RWA | Slow trend; halt on an 8% gap or stress; defined-risk preference | 2% | 12 bps |
| Perpetual | Negative-funding carry if drift contained; crowded or flipping funding is an alert; funding momentum | 2% | 10 bps |

Full notes: see inline PLAYBOOK and security controls.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt  # if present
# PYTHONPATH=src python -m crypto_intel scan fixtures/candles_synthetic.json
```

The fixture is labelled `SYNTHETIC` and is not a market history.

## Controls

1. Paper-only execution. `HALTED` and any live mode raise `PermissionError`.
2. Trade and withdrawal credential names are refused. No role can place an order.
3. Class size caps, confidence floors, kill switch, drawdown halt, RWA gap halt, stress overlay, multi-factor, MACD, multi-TF, stochastic, volume-delta, correlation-adjusted sizing, and adaptive filters.
4. Hash-chained audit log with timestamps, lineage (optional sealed), consecutive counter, rate anomaly, zero-trust policy, source attestation, feed jump and staleness checks.
5. PDPA-style tripwire over fixtures and docs.
6. Ruff lint (including bandit-style `S` rules), format, pytest coverage floor, gitleaks in CI.

## Honesty

- No live exchange connector is included. Do not add trade keys to this tree.
- Strategy scores describe the synthetic fixture, not future returns.
- This is not legal, compliance, or investment advice.

## Enhancements in v0.6

- Strategies: added volume-delta proxy, correlation-based size adjustment (higher corr reduces size for diversification), options-style defined-risk notes for high-vol regimes, refined funding momentum for perps.
- Security: expanded secret patterns (Telegram, Discord, more token formats), zero-trust action policy engine, improved anomaly detection with sequence awareness, stronger sealed lineage.
