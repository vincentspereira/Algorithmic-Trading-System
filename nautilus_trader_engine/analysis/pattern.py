"""
Pattern enums for technical indicators
"""

from enum import Enum


class PatternType(Enum):
    """Types of candlestick patterns"""

    # Single candle patterns
    HAMMER = "hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    INVERTED_HAMMER = "inverted_hammer"
    DOJI = "doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    SPINNING_TOP = "spinning_top"
    HIGH_WAVE = "high_wave"
    MARUBOZU_BULLISH = "marubozu_bullish"
    MARUBOZU_BEARISH = "marubozu_bearish"

    # Two candle patterns
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    PIERCING_PATTERN = "piercing_pattern"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"
    TWEEZER_TOP = "tweezer_top"
    TWEEZER_BOTTOM = "tweezer_bottom"

    # Three candle patterns
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    THREE_INSIDE_UP = "three_inside_up"
    THREE_INSIDE_DOWN = "three_inside_down"
    BULLISH_ABANDONED_BABY = "bullish_abandoned_baby"
    BEARISH_ABANDONED_BABY = "bearish_abandoned_baby"

    # Continuation patterns
    RISING_THREE_METHODS = "rising_three_methods"
    FALLING_THREE_METHODS = "falling_three_methods"
    BULLISH_FLAG = "bullish_flag"
    BEARISH_FLAG = "bearish_flag"
    UPSIDE_TASUKI_GAP = "upside_tasuki_gap"
    DOWNSIDE_TASUKI_GAP = "downside_tasuki_gap"
    MAT_HOLD = "mat_hold"
    RISING_WINDOW = "rising_window"
    FALLING_WINDOW = "falling_window"

    # Complex patterns
    BULLISH_HIKKAKE = "bullish_hikkake"
    BEARISH_HIKKAKE = "bearish_hikkake"

    # Institutional patterns
    INSTITUTIONAL_ACCUMULATION = "institutional_accumulation"
    INSTITUTIONAL_DISTRIBUTION = "institutional_distribution"
    VOLUME_CLIMAX = "volume_climax"

    # Meeting lines
    BULLISH_MEETING_LINES = "bullish_meeting_lines"
    BEARISH_MEETING_LINES = "bearish_meeting_lines"

    # Other patterns
    STICK_SANDWICH = "stick_sandwich"
    KANGAROO_TAIL = "kangaroo_tail"
    MARUBOZU_WHITE = "marubozu_white"
    MARUBOZU_BLACK = "marubozu_black"
    MARUBOZU_OPENING_WHITE = "marubozu_opening_white"
    MARUBOZU_OPENING_BLACK = "marubozu_opening_black"
    MARUBOZU_CLOSING_WHITE = "marubozu_closing_white"
    MARUBOZU_CLOSING_BLACK = "marubozu_closing_black"


class PatternSignal(Enum):
    """Pattern signal types"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternReliability(Enum):
    """Pattern reliability levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"