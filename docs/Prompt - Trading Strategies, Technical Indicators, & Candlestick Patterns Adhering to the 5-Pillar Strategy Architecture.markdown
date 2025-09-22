Below is a comprehensive, well-structured prompt you can use for your AI IDE Agent. I've crafted it based on your instructions, ensuring it covers the rework of the codebase, adherence to the specified architectures and directives, integration of indicators and patterns into strategies, and the additional points you mentioned (resolving imports, validating tests, and post-resolution enhancements).

To enhance the prompt based on my understanding of your goals (from the query and attached documents), I've added the following:

- Emphasis on ensuring modularity, scalability, and performance optimisations (e.g., for high-frequency trading, as mentioned in the Features, Phases & Integration Strategy document).
- Requirements for cross-referencing and integrating the comprehensive list of indicators (80+) and patterns (75+) from the COMPREHENSIVE_TECHNICAL_INDICATORS_DOCUMENTATION.md and README.md files.
- Instructions to maintain consistency with the overall system architecture (e.g., event-driven, microservices, NautilusTrader integration) from the Features, Phases & Integration Strategy document.
- A step-by-step workflow to guide the agent, including backups, version control, and final validation.
- Suggestions for AI/ML enhancements in strategies (e.g., using FinRL or PyOD for regime adaptation), aligning with the 5-Pillar Architecture's focus on ML clustering and adaptive learning.
- A focus on backward compatibility to avoid breaking existing integrations.

This prompt is formal, precise, and self-contained, adhering to your preferred response style.

**Prompt for AI IDE Agent: Institutional-Grade Refactoring of Indicators, Patterns, and Strategies**

**Objective:** Your task is to thoroughly analyse and refactor the entire codebase in the following folders:

- C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\indicators (containing technical indicators and candlestick patterns).
- C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\strategies (containing trading strategies).

The goal is to transform all technical indicators, candlestick patterns, and strategies into institutional-grade components by strictly adhering to:

- The **Institutional-Grade Technical Indicator Refactoring Directives** from " C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\Other Files\\Prompt - Institutional-Grade Technical Indicator Refactoring for NautilusTrader.docx". Refactor indicators to inherit from AugmentedIndicator (inheriting from Indicator), deprecating simple value properties in favour of value_meta returning IndicatorSignal objects with raw values, signal types, composite confidence scores, confidence components, suggested Trade Entries, Stop Loss / Take Profit, Trailing Stop Loss, Support and Resistance Levels using various techniques, and integration of the 5 pillars (volume confirmation, regime adaptation, multi-timeframe convergence, smart money proxies, risk management).
- The **Institutional-Grade Candlestick Pattern Augmentation Directives** from " C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\Other Files\\Prompt - Institutional-Grade Augmentation for Candlestick Patterns.docx". Expand the pattern library to include all 75+ patterns from the provided websites and attached COMPREHENSIVE_TECHNICAL_INDICATORS_DOCUMENTATION.md; refactor detection logic into an "analyst" system outputting metadata objects with volume confirmation scoring, VWAP analysis, smart money detection, adaptive confidence scoring (factoring crispness, volume, regime, trend alignment, institutional bias), and integrated risk management (auto SL/TP based on risk-reward ratios like 1:2 or 1:3). Update detect_all_patterns to return a dictionary of patterns with enhanced metadata.
- The **5-Pillar Strategy Architecture** outlined in " C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\Other Files\\Prompt - Trading Strategies Adhering to the 5-Pillar Strategy Architecture.docx". Every strategy must be a complete, self-contained Python class inheriting from BaseRetailStrategy or equivalent, implementing:
  - **Pillar 1: Signal Generation & Augmentation** – Use volume-weighted, adaptive, multi-timeframe indicators and patterns; output rich IndicatorSignal objects with raw values, signal types (e.g., BULLISH/BEARISH), and dynamic composite confidence scores.
  - **Pillar 2: Dynamic Risk & Money Management** – Include position sizing based on normalised ATR, volatility, and correlations; initial/trailing stop-losses; take-profits; and portfolio-wide drawdown checks.
  - **Pillar 3: Market Regime Adaptation** – Use indicators like Choppy Market Index, ADX, and VWMA; optionally integrate ML clustering (e.g., PyOD) to disable/reduce positions in unfavourable regimes.
  - **Pillar 4: Decoupled Execution Logic & Order Management** – Output "Execution Intent" objects (e.g., {'action': 'ENTER_LONG', 'algorithm': 'VWAP', 'urgency': 'MEDIUM', 'time_in_force': 'GTC'}) for the Order Management System.
  - **Pillar 5: Performance Tracking & Configurability** – Log metrics (e.g., Sharpe, Sortino, Calmar ratios) to an analytics database; externalise parameters in config.json for Optuna optimisation.

Ensure all components are institutional-grade: high-performance (microsecond latency for HFT), scalable, modular, and integrated with NautilusTrader's event-driven architecture (e.g., using Apache Kafka for events, as per " C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\Other Files\\Features, Phases & Integration Strategy - Algorithmic Trading System.docx"). Cross-reference the comprehensive lists in C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\indicators\\COMPREHENSIVE_TECHNICAL_INDICATORS_DOCUMENTATION.md (80+ indicators, 75+ patterns) and C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\indicators\\README.md and C:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\nautilus_trader_engine\\strategies\\README.md files to identify and implement any missing items, while enhancing existing ones for better accuracy and reliability.

**Key Enhancements and Integrations:**

- Strategies must leverage a diverse set of technical indicators (e.g., VWMA, RSI, MACD, ATR, Bollinger Bands) and candlestick patterns (e.g., Hammer, Engulfing, Morning Star) for signal generation, ensuring optimal results through combinations like:
  - Momentum strategies using VW MACD crossovers confirmed by bullish patterns and volume.
  - Mean-reversion strategies using RSI oversold signals with reversal patterns and regime checks.
  - Trend-following strategies aligning ADX trends with continuation patterns and multi-timeframe convergence.
  - Pairs trading using customised spread/ratio-based indicators and patterns (e.g., Spread_Open = Open1 - Open2).
- Incorporate AI/ML elements where applicable (e.g., FinRL for reinforcement learning in adaptive strategies, PyOD for anomaly detection in regimes).
- Maintain backward compatibility with existing code; ensure consistency with the system's microservices design, cloud-native principles, and multi-asset support (stocks, futures, options, forex, crypto).
- Optimise for performance: Use vectorised operations (NumPy/Pandas), parallel processing, and caching; target <1ms calculations for real-time use.

**Step-by-Step Workflow:**

1. **Backup and Version Control:** Before any changes, create a full backup of the folders. Commit the current state to Git with a message like "Pre-refactor backup for institutional-grade enhancements".
2. **Resolve Import-Related Issues in Strategies Module:**
    - Scan all files in the strategies folder for broken import paths.
    - Update all references from 'strategies.indicators' to 'indicators' (e.g., change from strategies.indicators import ... to from indicators import ...).
    - Ensure all module dependencies are resolved, including relative/absolute imports and any circular dependencies.
    - Test imports in isolation to confirm no errors.
3. **Validate the Entire Test Suite:**
    - Run all unit, integration, and performance tests in both folders.
    - Verify all test cases execute successfully and confirm functionality remains operational after import changes.
    - If any tests fail, debug and fix them before proceeding. Log any issues and resolutions.
4. **Only After Confirming Full Resolution of Import Issues and Test Validation:**
    - Proceed with refactoring indicators, patterns, and strategies per the directives above.
    - Implement shared utility functions for common operations (e.g., in strategies/utils/ or indicators/utils/): volume confirmation scoring, confidence aggregation, SL/TP calculation, regime detection, and Execution Intent generation. This enhances maintainability and reduces code duplication.
    - Document all code changes thoroughly: Add docstrings to classes/methods, inline comments for complex logic, and update any API references.
5. **Enhance and Integrate Components:**
    - Refactor indicators and patterns first, ensuring they output rich metadata/signals.
    - Then refactor strategies to use these enhanced indicators/patterns, adhering to the 5-Pillar Architecture. Cover all categories (momentum, volatility breakout, mean reversion, pairs trading, arbitrage, advanced technical) from the directives.
    - Add any missing indicators/patterns from the attached documentation (e.g., Vortex Indicator, Internal Bar Strength, Bullish Abandoned Baby).
6. **Update Documentation Files:**
    - Update indicators/README.md and strategies/README.md with:
        - New features (e.g., 5-Pillar integration, smart money detection, multi-timeframe convergence).
        - Improvements (e.g., volume-weighted enhancements, adaptive scoring, risk management factory).
        - Bug fixes (e.g., resolved import issues, test failures).
        - Changes affecting usage/configuration (e.g., new config.json parameters, updated class inheritance, deprecated properties like simple value).
    - Ensure updates align with the structure in the attached README.md files (e.g., add sections for new pillars, usage examples).
7. **Final Validation and Commit:**
    - Re-run the full test suite to confirm no regressions.
    - Perform a smoke test: Instantiate sample indicators, patterns, and strategies; simulate data inputs and verify outputs.
    - Commit changes to Git with detailed messages (e.g., "Implemented 5-Pillar Architecture for strategies; resolved imports").
    - Output a summary report: List refactored files, key changes, resolved issues, and any recommendations for further improvements (e.g., additional ML integrations).

**Success Criteria:**

- All components are institutional-grade, modular, and performant.
- Strategies effectively integrate indicators and patterns for superior signal quality.
- No import errors; 100% test pass rate.
- Updated README.md files are comprehensive and accurate.
- The codebase aligns with the overall system phases.

Acknowledge this prompt and confirm readiness before starting.

This prompt is ready to copy-paste into your AI IDE Agent interface. It prioritises safety (backups, step-by-step), clarity, and completeness while aligning with your system's broader goals. If you need adjustments, let me know.