#!/usr/bin/env python3
import sys

from backtester.cli import _REGISTRY, main
from backtester.strategy.examples.funding_rate import FundingRateStrategy

_REGISTRY["funding_rate"] = FundingRateStrategy

if __name__ == "__main__":
    sys.exit(main())
