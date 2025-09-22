import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
from nautilus_trader.indicators.base.indicator import Indicator

class SeasonalDecomposition(Indicator):
    """
    Applies seasonal decomposition to a time series.

    Decomposes a time series into trend, seasonal, and residual components.
    """
    def __init__(self, period: int, model: str = 'additive', input_bar_type: str = 'close'):
        """
        Initializes the SeasonalDecomposition indicator.

        :param period: The period of the seasonality.
        :param model: The type of model ('additive' or 'multiplicative').
        :param input_bar_type: The bar attribute to use for the decomposition ('close', 'high', etc.).
        """
        super().__init__()
        self.period = period
        self.model = model
        self.input_bar_type = input_bar_type
        self.trend = None
        self.seasonal = None
        self.resid = None

    def handle_bar(self, bar):
        """
        Receives a new bar and updates the indicator.
        """
        # This indicator is not designed to be updated bar-by-bar in a streaming fashion.
        # It is intended to be used on a historical series of data.
        # The calculation logic will be handled by a method that processes a full series.
        pass

    def calculate(self, series: pd.Series):
        """
        Performs the seasonal decomposition on the given series.

        :param series: A pandas Series containing the time series data.
        """
        if len(series) < 2 * self.period:
            # Not enough data to perform decomposition
            return

        result = seasonal_decompose(series, model=self.model, period=self.period)
        self.trend = result.trend
        self.seasonal = result.seasonal
        self.resid = result.resid

        # You can access the components like this:
        # trend_series = self.trend
        # seasonal_series = self.seasonal
        # residual_series = self.resid