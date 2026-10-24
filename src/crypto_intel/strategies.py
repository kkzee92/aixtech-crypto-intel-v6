"""Asset-class strategy research rules.

Transparent heuristics for paper research. Not forecasts and not a recommendation
to trade. Each class has an entry, an invalidation, and a regime overlay.
Version 0.6 adds volume-delta proxy, correlation-adjusted sizing, options-style
defined-risk proxies for high-vol, and refined multi-factor filters.
"""

from __future__ import annotations

from statistics import fmean, pstdev

# Assume models and regime exist; in full repo they would be imported
# from crypto_intel.models import AssetClass, Candle, Side, Signal
# from crypto_intel.regime import Regime, atr_pct, classify

# Minimal stubs for standalone demonstration (in production these are separate modules)
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AssetClass(Enum):
    MAJOR = "major"
    LARGE_CAP_ALT = "large_cap_alt"
    STABLECOIN = "stablecoin"
    DEFI = "defi"
    MEME = "meme"
    L2 = "l2"
    RWA = "rwa"
    PERPETUAL = "perpetual"

class Side(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"
    ALERT = "alert"

class Regime(Enum):
    TREND = "trend"
    RANGE = "range"
    STRESS = "stress"

@dataclass
class Candle:
    symbol: str
    asset_class: AssetClass
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: float = 0.0

@dataclass
class Signal:
    symbol: str
    asset_class: AssetClass
    side: Side
    confidence: float
    reason: str
    stop_distance_pct: float
    size_fraction: float
    horizon_bars: int

def atr_pct(candles: list) -> float:
    if len(candles) < 2:
        return 0.01
    trs = []
    for i in range(1, len(candles)):
        tr = max(candles[i].high - candles[i].low, abs(candles[i].high - candles[i-1].close), abs(candles[i].low - candles[i-1].close))
        trs.append(tr / candles[i].close)
    return fmean(trs) if trs else 0.01

def classify(candles: list) -> Regime:
    if len(candles) < 8:
        return Regime.RANGE
    vol = atr_pct(candles)
    if vol > 0.05:
        return Regime.STRESS
    closes = [c.close for c in candles]
    if abs(closes[-1] / closes[-8] - 1) > 0.03:
        return Regime.TREND
    return Regime.RANGE

PLAYBOOK: dict = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with multi-factor, MACD, multi-TF, stochastic, and vol-delta confirmation, except under stress or stretched RSI. Correlation adjusts size.",
        "entry": "Fast EMA above slow EMA, RSI 45-70, volume >=0.9x, BB positive, ADX-style >1.2, MACD hist >0, stochastic %K rising, longer-window aligned, vol-delta positive, adaptive vol scale.",
        "invalidation": "Stress regime, RSI >70, thin volume, weak strength, negative MACD, stochastic overbought, multi-TF mismatch, or high correlation without diversification.",
        "horizon": "8 bars mean-reversion, 20 bars trend",
    },
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Breakouts require volume, BB, strength, MACD, stochastic, and vol-delta confirmation; stress suppressed.",
        "entry": "Close above prior five-bar high, volume >=1.2x, BB >0.5, non-stress, strength proxy, MACD hist >0, stochastic not extreme, vol-delta ok.",
        "invalidation": "Stress or missing confirmation.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "The useful signal is a peg break, not direction.",
        "entry": "Deviation of 50 bps or more raises an alert. No order.",
        "invalidation": "Not applicable. Size stays zero.",
        "horizon": "1 bar monitor",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in a calm realised-vol regime with volume support, correlation note, and options-style defined-risk preference in spikes.",
        "entry": "Close above 8-bar EMA, realised vol <=6%, non-stress, volume ok, adaptive scale. High vol prefers alert over long.",
        "invalidation": "Stress or high vol.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Most bursts are untradeable. Qualified bursts require volume spike vs longer average, hard time stop, and low correlation.",
        "entry": "15% four-bar burst, volume spike vs 10-bar avg, not extended 40%, liquidity floor, corr not extreme.",
        "invalidation": "Thin liquidity or chase extension.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "L2 tokens are relative-strength bets versus a benchmark with vol-delta confirmation.",
        "entry": "Six-bar excess >3% vs non-stress benchmark, positive vol-delta.",
        "invalidation": "Missing or stressed benchmark.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Tokenised real-world assets should be slow. Gaps are a halt. Prefer defined-risk.",
        "entry": "Close above EMA and prior close, gap <8%, non-stress.",
        "invalidation": "Gap or stress.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding with contained drift is a carry observation; sudden funding flips or momentum raise alerts.",
        "entry": "Funding <= -5 bps, |drift| <4%, funding not flipping sharply positive, funding momentum stable.",
        "invalidation": "Crowded funding, excess drift, or sharp funding flip.",
        "horizon": "8 bars",
    },
}

def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]

def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value

def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0
    rs = fmean(gains) / average_loss
    return 100.0 - (100.0 / (1.0 + rs))

def _stoch_k(closes: list[float], period: int = 14) -> float:
    if len(closes) < period:
        return 50.0
    window = closes[-period:]
    lowest = min(window)
    highest = max(window)
    if highest == lowest:
        return 50.0
    return 100.0 * (closes[-1] - lowest) / (highest - lowest)

def _rel_volume(candles: list) -> float:
    if len(candles) < 6:
        return 1.0
    recent = fmean(c.volume for c in candles[-5:-1])
    return candles[-1].volume / recent if recent else 1.0

def _bb_position(closes: list[float]) -> float:
    if len(closes) < 8:
        return 0.0
    window = closes[-8:]
    mean = fmean(window)
    std = pstdev(window) or 0.001
    return (closes[-1] - mean) / std

def _adx_proxy(candles: list) -> float:
    if len(candles) < 8:
        return 1.0
    ups = []
    downs = []
    for i in range(1, len(candles)):
        high_diff = candles[i].high - candles[i-1].high
        low_diff = candles[i-1].low - candles[i].low
        ups.append(max(high_diff, 0.0))
        downs.append(max(low_diff, 0.0))
    up_avg = fmean(ups[-7:]) if ups else 0.0
    down_avg = fmean(downs[-7:]) if downs else 0.0
    if up_avg + down_avg == 0:
        return 1.0
    return max(up_avg, down_avg) / (up_avg + down_avg + 1e-9) * 2

def _macd_hist(closes: list[float]) -> float:
    if len(closes) < 26:
        return 0.0
    fast = _ema(closes, 12)
    slow = _ema(closes, 26)
    return fast - slow

def _multi_tf_aligned(closes: list[float]) -> bool:
    if len(closes) < 20:
        return True
    short = closes[-1] / closes[-8] - 1.0
    long = closes[-1] / closes[-20] - 1.0
    return (short > 0 and long > 0) or (short < 0 and long < 0)

def _volume_delta(candles: list) -> float:
    """Simple volume-delta proxy: recent volume change direction vs prior."""
    if len(candles) < 6:
        return 0.0
    recent = fmean(c.volume for c in candles[-3:])
    prior = fmean(c.volume for c in candles[-6:-3])
    return (recent - prior) / prior if prior else 0.0

def _adaptive_factor(candles: list) -> float:
    if len(candles) < 16:
        return 1.0
    current = atr_pct(candles[-8:])
    baseline = atr_pct(candles[-16:-8]) or current
    if baseline == 0:
        return 1.0
    ratio = current / baseline
    return max(0.5, min(1.05, 1.15 - ratio * 0.35))

def _correlation(candles: list, benchmark: Optional[list]) -> float:
    if not benchmark or len(benchmark) < 8 or len(candles) < 8:
        return 0.0
    own_ret = _returns([c.close for c in candles[-8:]])
    bench_ret = _returns([c.close for c in benchmark[-8:]])
    if len(own_ret) != len(bench_ret) or not own_ret:
        return 0.0
    mean_o = fmean(own_ret)
    mean_b = fmean(bench_ret)
    cov = fmean((o - mean_o) * (b - mean_b) for o, b in zip(own_ret, bench_ret))
    var_o = pstdev(own_ret) ** 2 or 1e-9
    var_b = pstdev(bench_ret) ** 2 or 1e-9
    return cov / (var_o ** 0.5 * var_b ** 0.5)

def _corr_size_adjust(corr: float) -> float:
    """Reduce size for high absolute correlation to encourage diversification."""
    abs_corr = abs(corr)
    if abs_corr > 0.8:
        return 0.6
    if abs_corr > 0.6:
        return 0.8
    return 1.0

def _base(candles: list, side: Side, confidence: float, reason: str, size: float, bars: int, benchmark: Optional[list] = None) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    vol = atr_pct(candles)
    adapt = _adaptive_factor(candles)
    closes = [c.close for c in candles]
    macd = _macd_hist(closes)
    mtf = _multi_tf_aligned(closes)
    stoch = _stoch_k(closes)
    vdelta = _volume_delta(candles)
    corr = _correlation(candles, benchmark)
    corr_adj = _corr_size_adjust(corr)
    adj_conf = round(max(0.0, min(confidence * adapt, 1.0)), 4)
    adj_size = round(size * adapt * corr_adj, 4)
    options_note = "defined-risk preferred" if vol > 0.04 else ""
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=adj_conf,
        reason=f"{reason}; regime={regime.value}; atr={vol:.3f}; bb={_bb_position(closes):.2f}; macd={macd:.4f}; mtf={mtf}; stoch={stoch:.1f}; vdelta={vdelta:.2f}; corr≈{corr:.2f}; corr_adj={corr_adj:.2f}; adapt={adapt:.2f}; {options_note}",
        stop_distance_pct=round(max(vol * 1.5, 0.01), 4),
        size_fraction=adj_size,
        horizon_bars=bars,
    )

def signal_for(candles: list, benchmark: Optional[list] = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime, benchmark)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.04, bars=12, regime=regime, benchmark=benchmark)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime, benchmark)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes, benchmark)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime)
    return _perpetual(candles, closes)

def _major(candles: list, closes: list[float], regime: Regime, benchmark: Optional[list]) -> Signal:
    fast, slow = _ema(closes, 5), _ema(closes, 13)
    rsi = _rsi(closes)
    rel_vol = _rel_volume(candles)
    bb = _bb_position(closes)
    strength = _adx_proxy(candles)
    macd = _macd_hist(closes)
    mtf = _multi_tf_aligned(closes)
    stoch = _stoch_k(closes)
    vdelta = _volume_delta(candles)
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.45, "major stress: stand aside", 0.0, 1, benchmark)
    if fast > slow and 45 <= rsi <= 70 and rel_vol >= 0.9 and bb > 0.0 and strength > 1.15 and macd > 0 and mtf and 20 < stoch < 80 and vdelta > -0.1:
        conf = 0.76 + min(0.05, rel_vol * 0.02)
        return _base(candles, Side.LONG, conf, "major multi-factor trend with MACD, multi-TF, stochastic, and vol-delta", 0.06, 20, benchmark)
    if regime is Regime.RANGE and rsi < 30 and closes[-1] > closes[-3] and bb < -1.0 and stoch < 30:
        return _base(candles, Side.LONG, 0.65, "major mean-reversion: washed-out RSI + below BB + stoch in range", 0.03, 8, benchmark)
    return _base(candles, Side.FLAT, 0.4, "major: no multi-factor edge", 0.0, 1, benchmark)

def _breakout(candles: list, closes: list[float], size: float, bars: int, regime: Regime, benchmark: Optional[list]) -> Signal:
    if regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.4, "breakout suppressed in stress", 0.0, 1, benchmark)
    window = closes[-6:-1]
    volume_now = candles[-1].volume
    volume_base = fmean(c.volume for c in candles[-6:-1])
    bb = _bb_position(closes)
    strength = _adx_proxy(candles)
    macd = _macd_hist(closes)
    stoch = _stoch_k(closes)
    vdelta = _volume_delta(candles)
    if closes[-1] > max(window) and volume_now > volume_base * 1.2 and bb > 0.5 and strength > 1.1 and macd > 0 and stoch < 85 and vdelta > 0.0:
        return _base(candles, Side.LONG, 0.74, "breakout with volume, BB, strength, MACD, stoch, and vol-delta", size, bars, benchmark)
    return _base(candles, Side.FLAT, 0.35, "no multi-factor breakout", 0.0, 1, benchmark)

def _stable(candles: list) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    if deviation >= 0.005:
        return _base(candles, Side.ALERT, 0.92, f"stablecoin depeg monitor: deviation {deviation:.4f}", 0.0, 1)
    if deviation >= 0.002:
        return _base(candles, Side.ALERT, 0.7, f"stablecoin watch band: deviation {deviation:.4f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.8, "stablecoin inside peg band", 0.0, 1)

def _defi(candles: list, closes: list[float], regime: Regime, benchmark: Optional[list]) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    if regime is Regime.STRESS or realised > 0.06:
        return _base(candles, Side.ALERT if realised > 0.08 else Side.FLAT, 0.48, "defi volatility regime: stand aside or defined-risk alert", 0.0, 1, benchmark)
    if closes[-1] > _ema(closes, 8) and _rel_volume(candles) >= 0.8:
        return _base(candles, Side.LONG, 0.70, "defi trend in calm regime with volume", 0.02, 10, benchmark)
    return _base(candles, Side.FLAT, 0.4, "defi: no calm multi-factor trend", 0.0, 1, benchmark)

def _meme(candles: list, closes: list[float], benchmark: Optional[list]) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    longer_vol = fmean(c.volume for c in candles[-10:]) if len(candles) >= 10 else liquidity
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    corr = _correlation(candles, benchmark)
    if liquidity < 1000:
        return _base(candles, Side.FLAT, 0.2, "meme liquidity proxy too thin", 0.0, 1)
    if extension > 0.40:
        return _base(candles, Side.FLAT, 0.35, "meme chase filter: 8-bar extension too large", 0.0, 1)
    if burst > 0.15 and candles[-1].volume > candles[-2].volume and candles[-1].volume > longer_vol * 1.5 and abs(corr) < 0.7:
        return _base(candles, Side.LONG, 0.78, "meme momentum burst with volume spike and acceptable corr; hard time stop applies", 0.005, 3, benchmark)
    return _base(candles, Side.FLAT, 0.3, "meme: no qualified burst", 0.0, 1)

def _l2(candles: list, closes: list[float], benchmark: Optional[list]) -> Signal:
    if not benchmark or len(benchmark) < 8:
        return _base(candles, Side.FLAT, 0.3, "l2 requires a benchmark series", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.42, "l2 benchmark in stress", 0.0, 1)
    own = closes[-1] / closes[-6] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench = bench_closes[-1] / bench_closes[-6] - 1.0
    vdelta = _volume_delta(candles)
    if own - bench > 0.03 and vdelta > 0.0:
        return _base(candles, Side.LONG, 0.7, "l2 relative strength versus benchmark with vol-delta", 0.03, 12, benchmark)
    return _base(candles, Side.FLAT, 0.4, "l2 not leading benchmark", 0.0, 1, benchmark)

def _rwa(candles: list, closes: list[float], regime: Regime) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    if abs(gap) > 0.08 or regime is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.5, "rwa gap or stress halt", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5]:
        return _base(candles, Side.LONG, 0.67, "rwa slow trend; defined-risk preferred", 0.02, 24)
    return _base(candles, Side.FLAT, 0.4, "rwa: no slow trend", 0.0, 1)

def _perpetual(candles: list, closes: list[float]) -> Signal:
    funding = candles[-1].funding_rate
    prior_funding = candles[-2].funding_rate if len(candles) > 1 else funding
    drift = closes[-1] / closes[-6] - 1.0
    funding_mom = funding - prior_funding
    if funding >= 0.001 or (funding_mom > 0.0003 and funding > 0):
        return _base(candles, Side.ALERT, 0.7, "perp funding crowded or flipping with momentum: monitor, no carry", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < 0.04 and abs(funding_mom) < 0.0002:
        return _base(candles, Side.LONG, 0.75, "perp funding carry: negative funding, basis contained, stable momentum", 0.02, 8)
    if funding <= -0.0005:
        return _base(candles, Side.FLAT, 0.5, "perp funding attractive but drift or momentum not contained", 0.0, 1)
    return _base(candles, Side.FLAT, 0.4, "perp: no carry edge", 0.0, 1)
