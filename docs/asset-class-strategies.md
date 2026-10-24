# Asset-Class Strategies (v0.6)

Each class uses multi-factor confirmation adapted to its risk profile. All signals are research heuristics on synthetic data only.

## Major (BTC, ETH)
Multi-factor trend (EMA cross, RSI band, volume, BB, strength, MACD, multi-TF, stochastic, volume-delta) outside stress. Mean-reversion in range. Correlation adjusts size downward for high corr.

## Large-cap Alt
Breakout with volume, BB, strength, MACD, stochastic, and positive volume-delta. Suppressed in stress.

## Stablecoin
Depeg monitoring only (alerts at 20/50 bps). No directional orders.

## DeFi
Calm-regime trend only. High realized vol triggers defined-risk alert preference (options-style proxy).

## Meme
Strict qualified burst (volume spike vs longer avg, no chase extension, acceptable correlation). Hard 3-bar horizon.

## L2
Relative strength vs non-stress benchmark plus volume-delta confirmation.

## RWA
Slow trend; gap or stress halt. Defined-risk preference noted.

## Perpetual
Negative funding carry when drift contained and funding momentum stable. Crowded or flipping funding raises alert.

Risk caps and costs are applied downstream. Always paper-only.
