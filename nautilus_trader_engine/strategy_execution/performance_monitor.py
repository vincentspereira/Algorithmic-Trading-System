import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Monitors the performance of live trading strategies.
    """

    def __init__(self):
        self.strategy_metrics: Dict[str, Dict[str, Any]] = {}

    def initialize_strategy_metrics(self, strategy_id: str):
        """
        Initializes performance metrics for a new strategy.
        """
        self.strategy_metrics[strategy_id] = {
            "pnl": 0.0,
            "drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "status": "active"
        }
        logger.info(f"Performance metrics initialized for strategy {strategy_id}.")

    def update_metrics(self, strategy_id: str, new_trade_pnl: float):
        """
        Updates performance metrics based on new trade results.
        This is a simplified update. A real system would process trade events,
        account updates, etc., to calculate these metrics accurately.
        """
        if strategy_id not in self.strategy_metrics:
            logger.warning(f"Strategy {strategy_id} not found in performance monitor. Initializing...")
            self.initialize_strategy_metrics(strategy_id)

        metrics = self.strategy_metrics[strategy_id]
        metrics["pnl"] += new_trade_pnl
        metrics["total_trades"] += 1

        if new_trade_pnl > 0:
            metrics["winning_trades"] += 1
        else:
            metrics["losing_trades"] += 1

        if metrics["total_trades"] > 0:
            metrics["win_rate"] = metrics["winning_trades"] / metrics["total_trades"]

        # Placeholder for drawdown calculation (requires more complex logic over time)
        # For simplicity, we'll just update it if a new trade causes a larger "drawdown"
        # This is NOT a true drawdown calculation.
        if new_trade_pnl < 0 and abs(new_trade_pnl) > metrics["drawdown"]:
            metrics["drawdown"] = abs(new_trade_pnl)

        logger.info(f"Metrics updated for strategy {strategy_id}: PnL={metrics['pnl']:.2f}, WinRate={metrics['win_rate']:.2f}")

    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """
        Returns the current performance metrics for a specific strategy.
        """
        return self.strategy_metrics.get(strategy_id, {"status": "not_found", "message": "Strategy not monitored."})

    def get_all_strategies_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns performance metrics for all monitored strategies.
        """
        return self.strategy_metrics