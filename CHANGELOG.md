# Changelog

## v1.0 (in progress)

Walk-forward validation engine with structural OOS guarantees, real baseline
comparison, automatic verdict with dispersion check. See `README.md`.

## Planned

### v1.1 — Strategy auditor

A helper (proposed location: `backtester.audit`) that, given a strategy and a
test DataFrame, calls `generate_signals(data.iloc[:k])` for several values of
`k` and verifies that the signals produced for indices `< k` are identical
across calls. Catches look-ahead bias in `generate_signals` by sampling,
without changing the framework's interface. Optional, runs outside the normal
execution path. Closes the gap left by Option B of the v1.0 look-ahead
contract (documented but not enforced in `Strategy.generate_signals`).
