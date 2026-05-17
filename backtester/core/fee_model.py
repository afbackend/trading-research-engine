from dataclasses import dataclass


@dataclass
class FeeModel:
    """Fee is ALWAYS subtracted from gross return. No trade exists without fee."""

    taker_fee: float = 0.001
    slippage_estimate: float = 0.0

    @property
    def round_trip(self) -> float:
        return (self.taker_fee + self.slippage_estimate) * 2

    def apply(self, gross_return: float) -> float:
        return gross_return - self.round_trip
