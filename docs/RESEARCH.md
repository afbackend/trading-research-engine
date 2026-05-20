# Research Sprints — BTC Algo Trading

Full documentation of the research process that originated this framework.
Three sprints, one invalidated strategy, and the lessons that shaped every design decision.

---

## Context

**Capital:** $200  
**Exchange:** Binance (selected after fee-tier analysis)  
**Objective:** Build a technical portfolio demonstrating rigorous quantitative research  
**Outcome:** Strategy invalidated. Framework built from the failures.

---

## Data

| Dataset | Period | Records | Timeframe |
|---|---|---|---|
| BTC/USDT price (initial) | 2026-03-04 → 2026-05-03 | 5,760 candles | 15min |
| BTC/USDT price (expanded) | 2025-11-04 → 2026-05-03 | 17,280 candles | 15min |
| BTC/USDT price (final) | 2024-05-03 → 2026-05-03 | 4,380 candles | 4h |
| Funding rate (initial) | 2026-03-04 → 2026-05-03 | 180 records | 8h |
| Funding rate (expanded) | 2025-11-04 → 2026-05-03 | 540 records | 8h |
| Funding rate (final) | 2024-05-03 → 2026-05-03 | 2,190 records | 8h |
| Daily price | 2024-05-04 → 2026-05-03 | 730 days | 1d |

All data sourced from Binance via CCXT. No authentication required (public endpoints).

---

## Exchange Selection

The initial exchange had a taker fee of 0.60% per side. Fee analysis showed this was structurally unviable.

| Metric | High-fee exchange | Selected exchange |
|---|---|---|
| Fee per side (taker) | 0.60% | 0.10% |
| Fee round trip | 1.20% | 0.20% |
| Cost per trade ($200) | $2.40 | $0.40 |
| Fee / std deviation (15min) | 5.0x | 0.85x |

At 5.0x, the high-fee exchange required a movement of 5 standard deviations just to break even on fees. Switching to a lower-fee exchange reduced this to 0.85x — the difference between structurally unviable and operatable.

---

## Timeframe Selection

15-minute candles were the initial choice. Fee barrier analysis forced a change.

| Timeframe | Std per candle | Fee/Std ratio | Implication |
|---|---|---|---|
| 15min | 0.24% | 0.85x | Fee consumes almost one full std move |
| 1h | ~0.48% | 0.42x | Fee is half an average move |
| 4h | 0.99% | 0.20x | Fee is 1/5 of an average move |

4h was selected for all subsequent research. The ratio of 0.20x provides meaningful room for edge above the fee barrier.

---

## Baseline Statistics (15min, 60 days)

Before testing any hypothesis, the market's baseline behavior was characterized.

| Metric | Value |
|---|---|
| Mean return per candle | +0.0024% |
| Standard deviation | 0.2348% |
| Positive candles | 50.5% |
| Max return | +3.52% |
| Min return | -1.77% |

**Autocorrelation:** No signal at any lag tested (1 to 16 candles). Past returns do not predict future returns at this timeframe.

**Buy and hold benchmark:** +13% over 60 days.

---

## Sprint 1 — Initial Hypotheses

**Timeframe:** 15min  
**Period:** 60 days (initial), expanded to 180 days  
**Objective:** Find statistically operatable edge in BTC/USDT

### H1 — Liquidity Grab Reversal

**Definition:** Candle pierces below 20-period support and closes above it — a stop-hunt signal followed by reversal.

**Logic:** Institutions push price below obvious support levels to trigger retail stop losses, then buy the generated liquidity. The recovery candle signals the end of the adverse move.

**Results (v1, 60 days):**

| Horizon | Occurrences | Mean return | Covers fee? |
|---|---|---|---|
| 1 candle (15min) | 253 | -0.008% | No |
| 3 candles (45min) | 253 | +0.021% | No |
| 8 candles (2h) | 253 | +0.055% | No |
| 16 candles (4h) | 253 | +0.073% | No |

**Results (v2, refined with wick > 0.3% + high volume):**

12 occurrences. Insufficient sample. Retorno negativo em todos os horizontes.

**Verdict:** Discarded. Maximum return 3x below fee in any configuration. Refinement destroyed occurrences without improving returns.

---

### H2 — Volume Confirmation

**Definition:** Price movement accompanied by volume 2x above the 20-candle average.

**Logic:** High volume indicates institutional participation. High-volume moves should have higher probability of continuation or reversal.

**Results (60 days):**

| Signal | Occurrences | Mean return (3c) | Covers fee? |
|---|---|---|---|
| Vol alto + UP | 279 | -0.018% | No |
| Vol alto + DOWN | 251 | +0.033% | No |

Thresholds from 1.5x to 4.0x were tested. No combination covered the fee.

**Observation:** Volume high + DOWN showed consistent positive return but insufficient magnitude. Noted as potential auxiliary signal.

**Verdict:** Discarded. Maximum edge 6x below fee.

---

### H3 — Extreme Funding Rate

**Definition:** Funding rate above the 90th or 95th percentile as an overbought signal — short entry with 8-hour holding period.

**Logic:** High funding rate means longs are paying shorts to maintain positions. An overbought market is vulnerable to corrections and cascading liquidations.

**Results (180 days, P95, in-sample):**

| Horizon | Mean return | Win rate | Net edge | Covers fee? |
|---|---|---|---|---|
| 1h (4c) | -0.062% | 31.2% | +0.057% | No |
| 2h (8c) | -0.118% | 38.5% | +0.108% | No |
| 4h (16c) | -0.234% | 44.8% | +0.213% | Yes |
| 8h (32c) | -0.487% | 54.4% | +0.449% | Yes |

**P90 vs P95 comparison:**

| Metric | P90 | P95 |
|---|---|---|
| Trades/day | 9.1 | 4.4 |
| Win rate | 54.4% | 55.5% |
| Net edge/trade | +0.29% | +0.54% |
| Total return 180d | +15.3% | +11.5% |
| Max drawdown | -15.1% | -10.3% |
| Longest losing streak | 85 | 61 |

**Critical finding — regime dependency (in-sample):**

| Period | Trend | Trades | Win rate | Edge |
|---|---|---|---|---|
| Nov-Dec 2025 | DOWN -15.6% | 544 | 56.2% | +0.48% |
| Jan-Feb 2026 | DOWN -23.7% | 256 | 53.9% | +0.67% |
| Mar-Apr 2026 | UP +14.1% | 0 | — | — |

Zero trades during the uptrend. Signal works exclusively in downtrending markets with trapped longs.

**Sprint 1 conclusion:** Edge identified in H3 but conditional on market regime. Regime detection required.

---

## Sprint 2 — Regime Detection

**Objective:** Add regime filter to H3 to make it robust across all market conditions

### EMA as Regime Filter

Tested EMA50, EMA100, EMA200, EMA400 on 15-minute candles as downtrend filters (price below EMA = downtrend regime).

| Filter | Win rate (Nov-Dec) | Win rate (Jan-Feb) | Mar-Apr filtered? |
|---|---|---|---|
| EMA50 | 49.0% (weak) | 56.2% | Yes |
| EMA100 | 52.2% | 53.1% | Yes |
| EMA200 | 63.1% | 57.6% | Yes |
| EMA400 | 64.4% | 64.6% | Yes |

All EMAs correctly filtered Mar-Apr 2026 (zero trades in uptrend).

### Problem: EMA on 15min = noise

EMA400 on 15-minute candles produced 438 regime transitions in 180 days (73/month). Price oscillated around the EMA constantly, generating regime flip-flop rather than stable detection.

### Solution: Daily EMA50

Switching to daily EMA50 reduced transitions from 438 to 14. Stable, meaningful regime detection.

**H3 + Daily EMA50 results (in-sample, 180 days):**

| Metric | Value |
|---|---|
| Total trades | 768 |
| Trades/day | 4.3 |
| Win rate | 57.4% |
| Edge/trade | +0.57% |
| Total return | +11.5% |
| Max drawdown | -10.3% |
| Benchmark (buy and hold) | -24.5% |
| Longest losing streak | 51 |

**Performance by period:**

| Period | Trend | Trades | Win rate | Edge | Status |
|---|---|---|---|---|---|
| Nov-Dec 2025 | DOWN | 544 | 56.2% | +0.48% | Positive |
| Jan-Feb 2026 | DOWN | 224 | 60.3% | +0.80% | Positive |
| Mar-Apr 2026 | UP | 0 | — | — | Filtered |

**December problem:** Win rate of 45% — market was lateral below the EMA50, not actively declining. EMA does not distinguish between active downtrend and lateral consolidation.

**Sprint 2 original conclusion:** Strategy approved for paper trading.

**Sprint 2 corrected conclusion (after Sprint 3):** Premature. The improvement from Sprint 1 (+1.9pp win rate, +0.03% edge) was marginal and within statistical noise. No out-of-sample validation had been performed.

---

## Sprint 3 — Walk-Forward Validation

**Objective:** Validate H3 + EMA50 daily out-of-sample using walk-forward

### Method

Each continuous downtrend period was split 60% train / 40% test. The P95 funding rate threshold was calculated using only training data. Performance was evaluated only on test data.

### Downtrend periods identified

| Period | Duration |
|---|---|
| 2025-11-04 → 2026-01-05 | 62 days |
| 2026-01-08 → 2026-01-14 | 6 days (excluded — too short) |
| 2026-01-21 → 2026-03-16 | 54 days |
| 2026-03-19 → 2026-04-08 | 20 days |

### Out-of-sample results

| Period | Train threshold | OOS trades | OOS win rate | OOS edge | p-value | Valid? |
|---|---|---|---|---|---|---|
| Nov 25 → Jan 26 | 0.0094% | 352 | 43.5% | -0.14% | 0.022 | No |
| Jan → Mar 26 | 0.0097% | <10 | — | — | — | Insufficient |
| Mar → Apr 26 | 0.0037% | 288 | 18.1% | -1.07% | 0.000 | No |

### Global OOS result

| Metric | In-sample | Out-of-sample |
|---|---|---|
| Win rate | 57.4% | 32.0% |
| Edge | +0.57% | **-0.56%** |
| t-statistic | +8.00 | -9.69 |
| p-value | 0.0000 | 0.0000 |
| Significant? | Yes (positive) | Yes (negative) |

The edge is **negative and statistically significant** out-of-sample. The system consistently loses money when operated with parameters trained on past data.

---

## Root Cause Analysis

### 1. P95 threshold instability

The funding rate P95 changed drastically between periods:
- First training period: 0.0094%
- Third training period: 0.0037%

The funding rate distribution is non-stationary. The P95 from one period does not apply to the next.

### 2. Regime-specific overfit

The 180-day dataset contained only one market cycle: decline from $103k to $65k followed by partial recovery. Optimized parameters captured the specific characteristics of this cycle, not a generalizable pattern.

### 3. Daily EMA50 as false regime filter

The daily EMA50 shifts directional exposure but does not detect regime. During transitions and lateral consolidation below the EMA, the system operated in the wrong regime.

---

## Validated Findings

These findings survived scrutiny and informed the framework design:

1. **Fee is a structural barrier at short timeframes.** At 15min, fee/std ratio of 0.85x eliminates most signals. At 4h, the ratio drops to 0.20x — viable.

2. **No autocorrelation exists at 15min.** Past returns do not predict future returns. Simple momentum or mean-reversion patterns fail.

3. **Funding rate captures regime, not timing.** Extreme funding indicates market state (overbought/oversold) but is not a reliable entry signal that survives out-of-sample.

4. **Walk-forward validation is non-negotiable.** In-sample backtesting produced misleading results in both Sprint 1 and Sprint 2. Without OOS validation, it is impossible to distinguish real edge from overfit.

5. **180 days with one cycle is insufficient.** Any pattern identified in a single cycle may be period-specific. Multiple cycles required for generalization.

6. **Marginal improvement does not equal validation.** Sprint 2 improved win rate by 1.9pp over Sprint 1. This was within statistical noise and did not survive OOS testing.

---

## Invalidated Hypotheses

| Hypothesis | Result | Root cause |
|---|---|---|
| H1 — Liquidity grab reversal | Return 3x below fee | Signal too weak at 15min timeframe |
| H2 — Volume confirmation | Return 6x below fee | Signal too weak at 15min timeframe |
| H3 — Funding rate extreme + EMA | OOS edge negative (-0.56%) | Non-stationary threshold + regime overfit |

---

## From Failure to Framework

Every framework design decision maps to a specific failure:

| Failure | Framework response |
|---|---|
| P95 threshold calculated on full dataset | `fit()` receives only training data |
| In-sample result reported as main output | Walk-forward is the only entry point |
| Fee applied inconsistently | `FeeModel.apply()` on every trade, no exceptions |
| Entry at same-close (impossible in practice) | Entry at next candle's open |
| No benchmark comparison | Mandatory buy-and-hold + random entry baselines |
| Marginal improvement mistaken for validation | Per-window significance check (≥60% windows significant) |
| Results looked good without statistical test | One-tailed t-test with p-value threshold |

---

## Market Context During Research

| Period | BTC Price | Trend | Funding rate |
|---|---|---|---|
| Nov 2025 | $103k → $87k | Strong decline | Predominantly positive (longs trapped) |
| Dec 2025 | $87k → $88k | Lateral | Mixed |
| Jan 2026 | $88k → $67k | Strong decline | Declining |
| Feb 2026 | $67k → $66k | Bottom / consolidation | Mostly negative |
| Mar 2026 | $66k → $73k | Recovery | Negative (shorts paying) |
| Apr 2026 | $73k → $76k | Continued recovery | Mixed |

The research period was dominated by a single macro cycle: decline from all-time highs near $103k to a low around $65k, followed by partial recovery. This limits generalizability of any finding.

---

## What Would Be Different Next Time

1. **Start with 2+ years of data.** 180 days with one cycle was insufficient. The expanded 2-year dataset (May 2024 → May 2026) at 4h timeframe is ready for Sprint 4.

2. **Walk-forward from day one.** Sprints 1 and 2 wasted time on in-sample analysis that was later invalidated. Walk-forward should be the first test, not the last.

3. **Test at 4h, not 15min.** The fee barrier at 15min made most signals unviable before any analysis was done.


## Status

**Strategy:** None validated. H3 + EMA50 daily invalidated by walk-forward.  
**Framework:** v1.0 complete. 179 tests, 99% coverage. Ready for Sprint 4.  
**Data:** 2 years of BTC/USDT at 4h + 1h + daily + funding rate collected and validated.  
