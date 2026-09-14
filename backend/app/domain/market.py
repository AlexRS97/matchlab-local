from enum import StrEnum


class Market(StrEnum):
    OVER_0_5_GOALS = "OVER_0_5_GOALS"
    OVER_1_5_GOALS = "OVER_1_5_GOALS"
    OVER_2_5_GOALS = "OVER_2_5_GOALS"
    OVER_3_5_GOALS = "OVER_3_5_GOALS"
    OVER_4_5_GOALS = "OVER_4_5_GOALS"
    BTTS_YES = "BTTS_YES"
    BTTS_NO = "BTTS_NO"
    OVER_7_5_CORNERS = "OVER_7_5_CORNERS"
    OVER_8_5_CORNERS = "OVER_8_5_CORNERS"
    OVER_9_5_CORNERS = "OVER_9_5_CORNERS"
    OVER_10_5_CORNERS = "OVER_10_5_CORNERS"
    OVER_11_5_CORNERS = "OVER_11_5_CORNERS"

    @property
    def line(self) -> float | None:
        return float(self.value.split("_")[1]) + 0.5 if self.value.startswith("OVER") else None

    @property
    def selection(self) -> str:
        return "NO" if self == Market.BTTS_NO else "YES" if self == Market.BTTS_YES else "OVER"

    @classmethod
    def parse(cls, value: str) -> "Market":
        key = value.upper()
        if key.startswith("CORNERS_OVER_"):
            key = key.removeprefix("CORNERS_") + "_CORNERS"
        if key.startswith("OVER_") and not key.endswith(("GOALS", "CORNERS")):
            key += "_GOALS"
        return cls(key)


GOAL_MARKETS = [m for m in Market if not m.value.endswith("CORNERS")]
CORNER_MARKETS = [m for m in Market if m.value.endswith("CORNERS")]
