**Institutional-Grade Augmentation for Candlestick Patterns**

**Objective:**

Analyse the Candlestick Pattern codebase located in the following folder:

“C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\indicators”

Based on the following resources, expand the pattern detection library and, crucially, refactor and enhance the entire pattern recognition system with institutional-grade features. The goal is to transform pattern signals from simple binary triggers into confidence-weighted, risk-aware decisions.

I would like you to go through these websites, understand it thoroughly, and incorporate these candlestick patterns as well as the Trading Rules, Backtests or any other information / ideas into the Algorithmic Trading System:

1. **75 Different Types of Candlestick Patterns (Trading Rules + Backtests)**

<https://www.quantifiedstrategies.com/types-of-candlesticks-patterns/>

1. **Candlestick Patterns: The Updated Complete Guide**

<https://www.morpher.com/blog/candlestick-patterns>

1. **45 Candlestick Patterns Every Trader Must Know**

<https://www.xs.com/en/blog/candlestick-patterns-types/>

1. **40 Powerful Candlestick Patterns: A Complete Trading Guide for Beginner Traders**

<https://www.strike.money/technical-analysis/types-of-candlesticks-patterns>

**Scope & Directives:**

1. **Comprehensive Pattern Integration:**
    - Analyze the four provided websites to extract the formal rules and definitions for all listed candlestick patterns.
    - Cross-reference this list with the existing pattern_detection.py (or equivalent) code to identify which patterns are already implemented.
    - **Develop and integrate all missing patterns** into the codebase, ensuring they follow the existing class/method architecture and output a consistent signal format.
2. **Institutional-Grade Feature Augmentation:** Refactor the core pattern detection logic to make it not just a detector, but an **analyst**. For each pattern detected, the system must calculate and return a rich metadata object including:
    - **Volume Confirmation Scoring:** A score (e.g., 0.0 to 1.0) based on how volume during the pattern formation compares to the recent average (e.g., current_volume / n_period_volume_ma). A score >1.2 should reinforce the pattern; <0.8 should weaken it.
    - **Volume-Weighted Price Analysis:** Integrate VWAP or other volume-weighted indicators into the pattern's context. Does the pattern form near a significant VWAP level?
    - **Smart Money Detection / Proxy:** Where possible, use existing order book or tick data indicators to assess aggression (e.g., large buy orders at the bid during a bullish pattern formation boosts confidence).
    - **Adaptive Confidence Scoring:** Replace a static pattern strength with a dynamic score that factors in:
        - The "crispness" of the pattern's shape (e.g., how perfectly it matches the ideal).
        - The volume confirmation score.
        - **Market Regime Context:** Adjust confidence based on volatility (e.g., low volatility patterns may be more reliable) and overall trend alignment (e.g., a bullish pattern in an uptrend is a continuation and gets a higher score than in a downtrend). Use existing ATR and trend indicators.
        - **Institutional Bias Assessment:** If data is available, analyze Open Interest changes or other derivatives data for confluence.
    - **Integrated Risk Management Factory:**
        - **Auto Stop-Loss/Target Calculation:** For each pattern, automatically calculate a logical stop-loss level (e.g., below the low of a hammer) and a primary profit target based on a configurable risk-reward ratio (e.g., 1:2, 1:3).
        - **Risk-Adjusted Signal Output:** The final output for a detected pattern must be a tuple or object containing: (pattern_name, base_signal, composite_confidence_score, suggested_stop_loss, suggested_profit_target).
3. **System Integration & Updates:**
    - **Update** detect_all_patterns **Method:** Ensure this method returns a dictionary of all detected patterns with their full suite of enhanced metadata, not just a list of pattern names.
    - **Enhance Pattern Reliability Database:** Expand the existing database schema to store the new metadata fields (volume_score, confidence_score, market_regime) alongside each pattern occurrence for future backtesting analysis and machine learning model training.
    - **Maintain Code Consistency:** Ensure all new code adheres to the existing project's style, uses the same data structures (e.g., NumPy arrays, Pandas DataFrames), and efficiently leverages existing helper functions and indicator calculations.

**Success Criteria:**  
The enhancement is complete when:

- The codebase contains a complete library of patterns from the provided sources.
- The pattern detection system provides a sophisticated, multi-factor confidence score for each pattern.
- Every pattern signal is accompanied by a logically derived risk management suggestion (stop-loss, take-profit).
- The updated detect_all_patterns function provides a unified interface for strategies to access this enhanced information.
- The system's performance can be more accurately judged based on confidence thresholds (e.g., only taking signals with a confidence score > 0.7)

**Comprehensive List of Candlestick Patterns**

Candlestick patterns are categorized into **bullish reversal**, **bearish reversal**, **continuation**, and **indecision/neutral** patterns. Below is a detailed list compiled from multiple sources.

**Bullish Reversal Patterns**

These patterns signal a potential upward price movement after a downtrend.

| **Pattern Name** | **Description** | **Trading Rules** | **Backtest Insights** |
| --- | --- | --- | --- |
| **Hammer** | Small body with a long lower wick (≥2x body) and little to no upper wick. Appears after a downtrend. | **Entry**: After confirmation (e.g., next candle closing above Hammer's close). **Stop-Loss**: Below the low of the Hammer. **Target**: Based on resistance or 1:2 risk-reward. | Success rate ~60–70% with confirmation . |
| **Inverted Hammer** | Similar to Hammer but with a long upper wick and small lower wick. | **Entry**: After confirmation (e.g., next candle closing higher). **Stop-Loss**: Below the low of the pattern. | Success rate ~67% . |
| **Bullish Engulfing** | Two-candle pattern. A small bearish candle is followed by a larger bullish candle that completely engulfs the prior candle. | **Entry**: At the close of the engulfing candle. **Stop-Loss**: Below the low of the pattern. | Success rate ~62% . Reliable in downtrends . |
| **Piercing Pattern** | Two-candle pattern. A bearish candle is followed by a bullish candle that opens below the prior low but closes above its midpoint. | **Entry**: At the close of the bullish candle. **Stop-Loss**: Below the low of the pattern. | Success rate ~64% . |
| **Morning Star** | Three-candle pattern: long bearish candle, small-bodied candle (e.g., Doji), and a long bullish candle closing above the first candle’s midpoint. | **Entry**: After the third candle closes. **Stop-Loss**: Below the low of the small-bodied candle. | Success rate ~78% . Highly reliable at support levels . |
| **Three White Soldiers** | Three consecutive long bullish candles with small wicks. | **Entry**: On breakout above the pattern. **Stop-Loss**: Below the low of the first candle. | Success rate ~84% . Indicates strong buying pressure . |
| **Bullish Harami** | Two-candle pattern. A large bearish candle is followed by a small bullish candle contained within its range. | **Entry**: After confirmation (e.g., next candle breaking above Harami high). **Stop-Loss**: Below the low of the pattern. | Success rate ~53% . Less reliable; requires context . |
| **Tweezer Bottom** | Two or more candles with identical lows, forming a support level. | **Entry**: After the second candle confirms support. **Stop-Loss**: Below the support level. | Success rate ~56% . |
| **Bullish Abandoned Baby** | Three-candle pattern: large bearish candle, Doji gapping down, and a large bullish candle gapping up. | **Entry**: After the third candle closes. **Stop-Loss**: Below the Doji's low. | Rare but high reliability; requires gap confirmation . |
| **Three Inside Up** | Three-candle pattern: bearish candle, bullish candle closing above the first candle’s midpoint, and another bullish candle closing above the first candle’s open. | **Entry**: After the third candle closes. **Stop-Loss**: Below the low of the pattern. | Success rate ~65% . |
| **Bullish Hikkake** | False downward breakout of an inside bar followed by a breakout above the inside bar’s high. | **Entry**: On breakout above the inside bar’s high. **Stop-Loss**: Below the pattern low. | Requires breakout confirmation; moderate reliability . |

**Bearish Reversal Patterns**

These patterns indicate a potential downward price movement after an uptrend.

| **Pattern Name** | **Description** | **Trading Rules** | **Backtest Insights** |
| --- | --- | --- | --- |
| **Shooting Star** | Small body with a long upper wick and little to no lower wick. Appears after an uptrend. | **Entry**: At the close of the Shooting Star or next candle confirmation. **Stop-Loss**: Above the high of the pattern. | Success rate ~50–60% with confirmation . |
| **Hanging Man** | Similar to Hammer but appears after an uptrend. Small body with a long lower wick. | **Entry**: After confirmation (e.g., next candle closing lower). **Stop-Loss**: Above the high of the pattern. | Requires trend context; moderate reliability . |
| **Bearish Engulfing** | Two-candle pattern. A small bullish candle is followed by a larger bearish candle that engulfs the prior candle. | **Entry**: At the close of the engulfing candle. **Stop-Loss**: Above the high of the pattern. | Similar reliability to Bullish Engulfing . |
| **Evening Star** | Three-candle pattern: long bullish candle, small-bodied candle, and a long bearish candle closing below the first candle’s midpoint. | **Entry**: After the third candle closes. **Stop-Loss**: Above the high of the pattern. | High reliability at resistance levels . |
| **Three Black Crows** | Three consecutive long bearish candles with small wicks. | **Entry**: On breakout below the pattern. **Stop-Loss**: Above the high of the first candle. | Indicates strong selling pressure . |
| **Dark Cloud Cover** | Two-candle pattern. A bullish candle is followed by a bearish candle that opens above the prior high but closes below its midpoint. | **Entry**: At the close of the bearish candle. **Stop-Loss**: Above the high of the pattern. | Often used with volume analysis . |
| **Bearish Harami** | Two-candle pattern. A large bullish candle is followed by a small bearish candle contained within its range. | **Entry**: After confirmation (e.g., next candle breaking below Harami low). **Stop-Loss**: Above the high of the pattern. | Low reliability; requires context . |
| **Tweezer Top** | Two or more candles with identical highs, forming a resistance level. | **Entry**: After the second candle confirms resistance. **Stop-Loss**: Above the resistance level. | Moderate reliability . |
| **Bearish Abandoned Baby** | Three-candle pattern: large bullish candle, Doji gapping up, and a large bearish candle gapping down. | **Entry**: After the third candle closes. **Stop-Loss**: Above the Doji's high. | Rare but high reliability; requires gap confirmation . |
| **Three Inside Down** | Three-candle pattern: bullish candle, bearish candle closing below the first candle’s midpoint, and another bearish candle closing below the first candle’s open. | **Entry**: After the third candle closes. **Stop-Loss**: Above the high of the pattern. | Moderate reliability . |

**Continuation Patterns**

These patterns suggest the existing trend will resume after a pause.

| **Pattern Name** | **Description** | **Trading Rules** | **Backtest Insights** |
| --- | --- | --- | --- |
| **Rising Three Methods** | Bullish trend continuation. A long bullish candle is followed by three small bearish candles within its range, and then another bullish candle. | **Entry**: On breakout above the consolidation. **Stop-Loss**: Below the low of the pattern. | Reliable in uptrends . |
| **Falling Three Methods** | Bearish trend continuation. A long bearish candle is followed by three small bullish candles within its range, and then another bearish candle. | **Entry**: On breakout below the consolidation. **Stop-Loss**: Above the high of the pattern. | Effective in downtrends . |
| **Bullish/Bearish Flag** | Sharp price movement (flagpole) followed by a consolidation (flag) in the opposite direction. | **Entry**: On breakout in the direction of the trend. **Stop-Loss**: Outside the flag pattern. | Works well with volume confirmation . |
| **Upside Tasuki Gap** | Bullish continuation. A bullish candle is followed by a gap up and a bearish candle that does not fill the gap. | **Entry**: On breakout above the gap. **Stop-Loss**: Below the gap level. | Requires trend alignment . |
| **Downside Tasuki Gap** | Bearish continuation. A bearish candle is followed by a gap down and a bullish candle that does not fill the gap. | **Entry**: On breakout below the gap. **Stop-Loss**: Above the gap level. | Requires trend alignment . |
| **Mat Hold** | Bullish continuation. Similar to Rising Three Methods but with variations in the consolidation phase. | **Entry**: On breakout above the consolidation. **Stop-Loss**: Below the pattern low. | Moderate reliability . |
| **Rising Window** | Bullish continuation. A gap between two bullish candles, indicating strong buying pressure. | **Entry**: On pullback to the gap support. **Stop-Loss**: Below the gap. | Gaps often act as support/resistance . |
| **Falling Window** | Bearish continuation. A gap between two bearish candles, indicating strong selling pressure. | **Entry**: On pullback to the gap resistance. **Stop-Loss**: Above the gap. | Gaps often act as support/resistance . |

**Indecision/Neutral Patterns**

These patterns reflect market uncertainty and potential trend changes.

| **Pattern Name** | **Description** | **Trading Rules** | **Backtest Insights** |
| --- | --- | --- | --- |
| **Doji** | Open and close prices are nearly equal, resulting in a small body with long wicks. | **Entry**: Wait for confirmation (e.g., next candle breaking out). **Stop-Loss**: Above/below the Doji’s extremes. | Signals reversal at trend extremes . |
| **Spinning Top** | Small body with long upper and lower wicks. | **Entry**: Requires confirmation from next candle. **Stop-Loss**: Beyond the pattern’s range. | Often leads to reversals or pauses . |
| **High Wave** | Similar to Doji but with a larger body and very long wicks. | **Entry**: Wait for confirmation. **Stop-Loss**: Beyond the pattern’s range. | Indicates high volatility and indecision . |

**Backtesting Insights and Trading Tips**

- **General Findings**: Candlestick patterns are more reliable when:
  - Confirmed by subsequent price action or volume.
  - Aligned with key support/resistance levels.
  - Used with other indicators (e.g., RSI, moving averages) .
- **Performance Variance**: Success rates range from ~50% to 84%, with patterns like Three White Soldiers and Morning Star showing higher reliability .
- **Limitations**: Patterns may fail in volatile markets or without context. Backtesting on historical data (e.g., S&P 500) is recommended for strategy validation .
- **Risk Management**: Always use stop-loss orders and aim for a risk-reward ratio of at least 1:2 .

**Key Takeaways**

1. **Context Matters**: Trade patterns in alignment with the overall trend and key levels.
2. **Confirmation is Crucial**: Wait for additional signals (e.g., volume surge, indicator alignment) before entering.
3. **Practice and Backtest**: Use demo accounts and historical data to test strategies before live trading .