"""
Advanced Data Visualization and Interactive Charts
TradingView integration, real-time order book visualization, and custom indicators
"""
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class IndicatorType(Enum):
    """Technical indicator types"""
    SMA = "simple_moving_average"
    EMA = "exponential_moving_average"
    RSI = "relative_strength_index"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    VOLUME_PROFILE = "volume_profile"
    SUPPORT_RESISTANCE = "support_resistance"


@dataclass
class OHLCV:
    """OHLCV data structure"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class OrderBookLevel:
    """Order book level data"""
    price: float
    quantity: int
    side: str  # 'bid' or 'ask'


@dataclass
class TechnicalIndicator:
    """Technical indicator configuration"""
    indicator_type: IndicatorType
    parameters: Dict[str, Any]
    name: str
    color: str = "#4a90e2"
    visible: bool = True


class TechnicalAnalysis:
    """Technical analysis calculations"""
    
    @staticmethod
    def simple_moving_average(prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)
        
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                avg = sum(prices[i-period+1:i+1]) / period
                sma.append(avg)
        
        return sma
    
    @staticmethod
    def exponential_moving_average(prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if not prices:
            return []
        
        ema = [prices[0]]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema[i-1] * (1 - multiplier))
            ema.append(ema_value)
        
        return ema
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi_values = [None] * (period)
        
        for i in range(period, len(deltas)):
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
            
            # Update averages
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return [None] + rsi_values
    
    @staticmethod
    def macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalAnalysis.exponential_moving_average(prices, fast_period)
        ema_slow = TechnicalAnalysis.exponential_moving_average(prices, slow_period)
        
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        # Filter out None values for signal calculation
        macd_values = [x for x in macd_line if x is not None]
        signal_line_values = TechnicalAnalysis.exponential_moving_average(macd_values, signal_period)
        
        # Reconstruct signal line with proper positioning
        signal_line = [None] * len(macd_line)
        signal_index = 0
        for i, macd_val in enumerate(macd_line):
            if macd_val is not None and signal_index < len(signal_line_values):
                signal_line[i] = signal_line_values[signal_index]
                signal_index += 1
        
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram.append(macd_line[i] - signal_line[i])
            else:
                histogram.append(None)
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands"""
        sma = TechnicalAnalysis.simple_moving_average(prices, period)
        
        upper_band = []
        lower_band = []
        
        for i in range(len(prices)):
            if i < period - 1:
                upper_band.append(None)
                lower_band.append(None)
            else:
                price_slice = prices[i-period+1:i+1]
                std = np.std(price_slice)
                upper_band.append(sma[i] + (std * std_dev))
                lower_band.append(sma[i] - (std * std_dev))
        
        return sma, upper_band, lower_band


class AdvancedChartGenerator:
    """Advanced chart generation with technical indicators"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.technical_analysis = TechnicalAnalysis()
    
    def create_candlestick_chart(self, ohlcv_data: List[OHLCV], 
                               indicators: List[TechnicalIndicator] = None,
                               title: str = "Price Chart") -> str:
        """Create interactive candlestick chart with indicators"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Candlestick chart requires Plotly")
        
        try:
            # Prepare data
            timestamps = [data.timestamp for data in ohlcv_data]
            opens = [data.open for data in ohlcv_data]
            highs = [data.high for data in ohlcv_data]
            lows = [data.low for data in ohlcv_data]
            closes = [data.close for data in ohlcv_data]
            volumes = [data.volume for data in ohlcv_data]
            
            # Create subplots
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=('Price', 'Volume', 'Indicators'),
                row_width=[0.2, 0.1, 0.1]
            )
            
            # Add candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=timestamps,
                    open=opens,
                    high=highs,
                    low=lows,
                    close=closes,
                    name="Price"
                ),
                row=1, col=1
            )
            
            # Add volume bars
            colors = ['red' if closes[i] < opens[i] else 'green' for i in range(len(closes))]
            fig.add_trace(
                go.Bar(
                    x=timestamps,
                    y=volumes,
                    name="Volume",
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            # Add technical indicators
            if indicators:
                for indicator in indicators:
                    if not indicator.visible:
                        continue
                    
                    self._add_indicator_to_chart(fig, indicator, closes, timestamps)
            
            # Update layout
            fig.update_layout(
                title=title,
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                height=800,
                showlegend=True
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"Error creating candlestick chart: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def _add_indicator_to_chart(self, fig, indicator: TechnicalIndicator, 
                              prices: List[float], timestamps: List[datetime]):
        """Add technical indicator to chart"""
        try:
            if indicator.indicator_type == IndicatorType.SMA:
                period = indicator.parameters.get('period', 20)
                sma_values = self.technical_analysis.simple_moving_average(prices, period)
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=sma_values,
                        name=f"SMA({period})",
                        line=dict(color=indicator.color)
                    ),
                    row=1, col=1
                )
            
            elif indicator.indicator_type == IndicatorType.EMA:
                period = indicator.parameters.get('period', 20)
                ema_values = self.technical_analysis.exponential_moving_average(prices, period)
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=ema_values,
                        name=f"EMA({period})",
                        line=dict(color=indicator.color)
                    ),
                    row=1, col=1
                )
            
            elif indicator.indicator_type == IndicatorType.RSI:
                period = indicator.parameters.get('period', 14)
                rsi_values = self.technical_analysis.rsi(prices, period)
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=rsi_values,
                        name=f"RSI({period})",
                        line=dict(color=indicator.color)
                    ),
                    row=3, col=1
                )
                
                # Add RSI reference lines
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
            
            elif indicator.indicator_type == IndicatorType.BOLLINGER_BANDS:
                period = indicator.parameters.get('period', 20)
                std_dev = indicator.parameters.get('std_dev', 2)
                sma, upper, lower = self.technical_analysis.bollinger_bands(prices, period, std_dev)
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=upper,
                        name="BB Upper",
                        line=dict(color="rgba(255,0,0,0.5)"),
                        fill=None
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=lower,
                        name="BB Lower",
                        line=dict(color="rgba(255,0,0,0.5)"),
                        fill='tonexty',
                        fillcolor="rgba(255,0,0,0.1)"
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=sma,
                        name="BB Middle",
                        line=dict(color="blue")
                    ),
                    row=1, col=1
                )
            
            elif indicator.indicator_type == IndicatorType.MACD:
                fast = indicator.parameters.get('fast_period', 12)
                slow = indicator.parameters.get('slow_period', 26)
                signal = indicator.parameters.get('signal_period', 9)
                
                macd_line, signal_line, histogram = self.technical_analysis.macd(prices, fast, slow, signal)
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=macd_line,
                        name="MACD",
                        line=dict(color="blue")
                    ),
                    row=3, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=signal_line,
                        name="Signal",
                        line=dict(color="red")
                    ),
                    row=3, col=1
                )
                
                colors = ['red' if h < 0 else 'green' for h in histogram if h is not None]
                fig.add_trace(
                    go.Bar(
                        x=timestamps,
                        y=histogram,
                        name="Histogram",
                        marker_color=colors,
                        opacity=0.7
                    ),
                    row=3, col=1
                )
        
        except Exception as e:
            self.logger.error(f"Error adding indicator {indicator.name}: {e}")
    
    def create_order_book_visualization(self, bids: List[OrderBookLevel], 
                                      asks: List[OrderBookLevel],
                                      title: str = "Order Book") -> str:
        """Create order book depth visualization"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Order book visualization requires Plotly")
        
        try:
            # Sort order book data
            bids_sorted = sorted(bids, key=lambda x: x.price, reverse=True)
            asks_sorted = sorted(asks, key=lambda x: x.price)
            
            # Calculate cumulative quantities
            bid_prices = [level.price for level in bids_sorted]
            bid_quantities = [level.quantity for level in bids_sorted]
            bid_cumulative = np.cumsum(bid_quantities)
            
            ask_prices = [level.price for level in asks_sorted]
            ask_quantities = [level.quantity for level in asks_sorted]
            ask_cumulative = np.cumsum(ask_quantities)
            
            fig = go.Figure()
            
            # Add bid side
            fig.add_trace(
                go.Scatter(
                    x=bid_prices,
                    y=bid_cumulative,
                    mode='lines',
                    name='Bids',
                    line=dict(color='green', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(0,255,0,0.1)'
                )
            )
            
            # Add ask side
            fig.add_trace(
                go.Scatter(
                    x=ask_prices,
                    y=ask_cumulative,
                    mode='lines',
                    name='Asks',
                    line=dict(color='red', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(255,0,0,0.1)'
                )
            )
            
            # Add individual levels as bars
            fig.add_trace(
                go.Bar(
                    x=bid_prices,
                    y=bid_quantities,
                    name='Bid Levels',
                    marker_color='green',
                    opacity=0.3,
                    yaxis='y2'
                )
            )
            
            fig.add_trace(
                go.Bar(
                    x=ask_prices,
                    y=ask_quantities,
                    name='Ask Levels',
                    marker_color='red',
                    opacity=0.3,
                    yaxis='y2'
                )
            )
            
            # Update layout
            fig.update_layout(
                title=title,
                xaxis_title="Price",
                yaxis_title="Cumulative Quantity",
                yaxis2=dict(
                    title="Level Quantity",
                    overlaying='y',
                    side='right'
                ),
                height=600,
                showlegend=True
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"Error creating order book visualization: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def create_volume_profile(self, ohlcv_data: List[OHLCV], 
                            bins: int = 50,
                            title: str = "Volume Profile") -> str:
        """Create volume profile chart"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Volume profile requires Plotly")
        
        try:
            # Extract price and volume data
            prices = []
            volumes = []
            
            for data in ohlcv_data:
                # Use typical price (HLC/3)
                typical_price = (data.high + data.low + data.close) / 3
                prices.append(typical_price)
                volumes.append(data.volume)
            
            # Create price bins
            min_price = min(prices)
            max_price = max(prices)
            price_bins = np.linspace(min_price, max_price, bins)
            
            # Calculate volume for each price bin
            volume_profile = np.zeros(bins - 1)
            
            for i, price in enumerate(prices):
                bin_index = np.digitize(price, price_bins) - 1
                if 0 <= bin_index < len(volume_profile):
                    volume_profile[bin_index] += volumes[i]
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            bin_centers = (price_bins[:-1] + price_bins[1:]) / 2
            
            fig.add_trace(
                go.Bar(
                    x=volume_profile,
                    y=bin_centers,
                    orientation='h',
                    name='Volume Profile',
                    marker_color='blue',
                    opacity=0.7
                )
            )
            
            # Highlight POC (Point of Control - highest volume)
            poc_index = np.argmax(volume_profile)
            poc_price = bin_centers[poc_index]
            
            fig.add_hline(
                y=poc_price,
                line_dash="dash",
                line_color="red",
                annotation_text=f"POC: ${poc_price:.2f}"
            )
            
            fig.update_layout(
                title=title,
                xaxis_title="Volume",
                yaxis_title="Price",
                height=600,
                showlegend=True
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"Error creating volume profile: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def create_heatmap(self, data: Dict[str, Dict[str, float]], 
                      title: str = "Correlation Heatmap") -> str:
        """Create correlation heatmap"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Heatmap requires Plotly")
        
        try:
            # Convert data to matrix format
            symbols = list(data.keys())
            matrix = []
            
            for symbol1 in symbols:
                row = []
                for symbol2 in symbols:
                    correlation = data[symbol1].get(symbol2, 0)
                    row.append(correlation)
                matrix.append(row)
            
            fig = go.Figure(
                data=go.Heatmap(
                    z=matrix,
                    x=symbols,
                    y=symbols,
                    colorscale='RdBu',
                    zmid=0,
                    text=matrix,
                    texttemplate="%{text:.2f}",
                    textfont={"size": 10}
                )
            )
            
            fig.update_layout(
                title=title,
                width=600,
                height=600
            )
            
            return fig.to_html(include_plotlyjs='cdn')
            
        except Exception as e:
            self.logger.error(f"Error creating heatmap: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def _create_text_chart(self, message: str) -> str:
        """Create text-based chart when visualization libraries not available"""
        return f"""
        <div class="text-chart">
            <h3>Chart Unavailable</h3>
            <p>{message}</p>
            <p>Install plotly for interactive charts</p>
        </div>
        """


# Sample data generators for testing
class SampleDataGenerator:
    """Generate sample data for testing charts"""
    
    @staticmethod
    def generate_ohlcv_data(days: int = 30, symbol: str = "AAPL") -> List[OHLCV]:
        """Generate sample OHLCV data"""
        data = []
        base_price = 150.0
        current_price = base_price
        
        for i in range(days * 24):  # Hourly data
            timestamp = datetime.now() - timedelta(hours=days * 24 - i)
            
            # Random walk
            change = np.random.normal(0, 0.5)
            current_price += change
            
            # Generate OHLC
            open_price = current_price
            high_price = open_price + abs(np.random.normal(0, 1))
            low_price = open_price - abs(np.random.normal(0, 1))
            close_price = low_price + (high_price - low_price) * np.random.random()
            volume = int(np.random.normal(10000, 3000))
            
            data.append(OHLCV(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=max(volume, 1000)
            ))
            
            current_price = close_price
        
        return data
    
    @staticmethod
    def generate_order_book_data() -> Tuple[List[OrderBookLevel], List[OrderBookLevel]]:
        """Generate sample order book data"""
        mid_price = 150.0
        
        bids = []
        asks = []
        
        # Generate bid levels
        for i in range(20):
            price = mid_price - (i + 1) * 0.01
            quantity = int(np.random.exponential(1000))
            bids.append(OrderBookLevel(price=price, quantity=quantity, side='bid'))
        
        # Generate ask levels
        for i in range(20):
            price = mid_price + (i + 1) * 0.01
            quantity = int(np.random.exponential(1000))
            asks.append(OrderBookLevel(price=price, quantity=quantity, side='ask'))
        
        return bids, asks


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create chart generator
    chart_gen = AdvancedChartGenerator()
    
    # Generate sample data
    ohlcv_data = SampleDataGenerator.generate_ohlcv_data(30)
    bids, asks = SampleDataGenerator.generate_order_book_data()
    
    # Create indicators
    indicators = [
        TechnicalIndicator(
            indicator_type=IndicatorType.SMA,
            parameters={'period': 20},
            name="SMA 20",
            color="blue"
        ),
        TechnicalIndicator(
            indicator_type=IndicatorType.RSI,
            parameters={'period': 14},
            name="RSI 14",
            color="purple"
        ),
        TechnicalIndicator(
            indicator_type=IndicatorType.BOLLINGER_BANDS,
            parameters={'period': 20, 'std_dev': 2},
            name="Bollinger Bands",
            color="red"
        )
    ]
    
    # Generate charts
    candlestick_chart = chart_gen.create_candlestick_chart(ohlcv_data, indicators)
    order_book_chart = chart_gen.create_order_book_visualization(bids, asks)
    volume_profile_chart = chart_gen.create_volume_profile(ohlcv_data)
    
    print("Advanced charts generated successfully")
    print(f"Candlestick chart length: {len(candlestick_chart)}")
    print(f"Order book chart length: {len(order_book_chart)}")
    print(f"Volume profile chart length: {len(volume_profile_chart)}")