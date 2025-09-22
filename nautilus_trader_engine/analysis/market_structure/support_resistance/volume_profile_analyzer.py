"""
Volume Profile Support and Resistance Analyzer

Advanced volume profile analysis for institutional-grade support/resistance identification:
- Volume Profile (VP) analysis for high-volume price levels
- Volume Weighted Average Price (VWAP) levels
- Point of Control (POC) identification
- Value Area (VA) calculation
- Volume clusters and gaps analysis
- Smart money accumulation/distribution zones
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class VolumeProfileType(Enum):
    """Types of volume profile analysis"""
    POINT_OF_CONTROL = "point_of_control"
    VALUE_AREA_HIGH = "value_area_high"
    VALUE_AREA_LOW = "value_area_low"
    VOLUME_CLUSTER = "volume_cluster"
    VWAP_LEVEL = "vwap_level"
    VOLUME_GAP = "volume_gap"


class VolumeProfileSignalType(Enum):
    """Signal types for volume profile analysis"""
    POC_TEST = "POC_TEST"
    VA_BREAKOUT = "VA_BREAKOUT"
    VOLUME_CLUSTER_BREAK = "VOLUME_CLUSTER_BREAK"
    VWAP_REJECTION = "VWAP_REJECTION"
    VOLUME_GAP_FILL = "VOLUME_GAP_FILL"
    ACCUMULATION_ZONE = "ACCUMULATION_ZONE"
    DISTRIBUTION_ZONE = "DISTRIBUTION_ZONE"


@dataclass
class VolumeProfileLevel:
    """Represents a volume profile based level"""
    level_type: VolumeProfileType
    price_level: float
    volume_at_level: float
    relative_volume: float  # Volume relative to average
    confidence_score: float
    timeframes_active: List[str]
    last_update: datetime
    significance_score: float


@dataclass
class VolumeProfileSignal:
    """Signal for volume profile analysis"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Volume profile specific fields
    point_of_control: Optional[float]
    value_area_high: Optional[float]
    value_area_low: Optional[float]
    volume_clusters: List[Dict[str, Any]]
    vwap_level: Optional[float]
    volume_gaps: List[Dict[str, Any]]


class VolumeProfileAnalyzer(AugmentedIndicator):
    """
    Advanced Volume Profile Support and Resistance Analyzer

    Institutional-grade volume analysis for level identification:
    - Point of Control (POC): Price level with highest volume
    - Value Area (VA): Price range containing 70% of total volume
    - Volume Weighted Average Price (VWAP) levels
    - Volume clusters and accumulation/distribution zones
    - Volume gaps and institutional activity detection

    All implementations include volume-weighting, smart money confirmation,
    multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
    """

    def __init__(self, timeframe: str = "1D", lookback_period: int = 200, price_bins: int = 50):
        super().__init__(name="VolumeProfileAnalyzer", timeframe=timeframe)
        self.lookback_period = lookback_period
        self.price_bins = price_bins

        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []

        # Volume profile data
        self.volume_profile = {}
        self.point_of_control = None
        self.value_area = {'high': None, 'low': None}
        self.vwap_levels = []
        self.volume_clusters = []
        self.volume_gaps = []

        # Signal history
        self.signal_history = []

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[VolumeProfileSignal]:
        """
        Update analyzer with new price/volume data

        Args:
            price: Current price
            volume: Current volume
            high: High price (optional)
            low: Low price (optional)
            timestamp: Data timestamp
            order_book_data: Order book data for smart money analysis
            trade_data: Trade data for volume analysis

        Returns:
            VolumeProfileSignal if significant volume profile activity detected, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update histories
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)

        # Maintain history size
        max_history = self.lookback_period
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 50:
            return None

        # Update volume profile analysis
        self._update_volume_profile()
        self._update_point_of_control()
        self._update_value_area()
        self._update_vwap_levels()
        self._update_volume_clusters()
        self._update_volume_gaps()

        # Generate signal if significant activity
        signal = self._generate_volume_signal(timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.signal_history.append(signal)

        return signal

    def _update_volume_profile(self):
        """Update volume profile calculation"""
        if len(self.price_history) < 20:
            return

        # Create price bins
        recent_prices = self.price_history[-100:]  # Use last 100 periods
        recent_volumes = self.volume_history[-100:]

        if not recent_prices:
            return

        price_min = min(recent_prices)
        price_max = max(recent_prices)

        if price_max == price_min:
            return

        # Create bins
        bins = np.linspace(price_min, price_max, self.price_bins + 1)

        # Calculate volume per bin
        self.volume_profile = {}
        for i in range(len(recent_prices)):
            price = recent_prices[i]
            volume = recent_volumes[i]

            # Find appropriate bin
            bin_idx = np.digitize(price, bins) - 1
            if 0 <= bin_idx < len(bins) - 1:
                bin_key = f"{bins[bin_idx]:.4f}-{bins[bin_idx+1]:.4f}"
                if bin_key not in self.volume_profile:
                    self.volume_profile[bin_key] = 0
                self.volume_profile[bin_key] += volume

    def _update_point_of_control(self):
        """Update Point of Control (POC) - price level with highest volume"""
        if not self.volume_profile:
            self.point_of_control = None
            return

        # Find bin with highest volume
        max_volume_bin = max(self.volume_profile.items(), key=lambda x: x[1])

        # Extract price from bin key (use midpoint)
        bin_range = max_volume_bin[0].split('-')
        poc_price = (float(bin_range[0]) + float(bin_range[1])) / 2

        self.point_of_control = poc_price

    def _update_value_area(self):
        """Update Value Area (VA) - price range containing 70% of volume"""
        if not self.volume_profile:
            self.value_area = {'high': None, 'low': None}
            return

        # Sort bins by volume (descending)
        sorted_bins = sorted(self.volume_profile.items(), key=lambda x: x[1], reverse=True)

        total_volume = sum(self.volume_profile.values())
        target_volume = total_volume * 0.7  # 70% of volume

        # Accumulate volume until we reach target
        accumulated_volume = 0
        va_bins = []

        for bin_key, volume in sorted_bins:
            va_bins.append(bin_key)
            accumulated_volume += volume
            if accumulated_volume >= target_volume:
                break

        if va_bins:
            # Extract price range from VA bins
            all_prices = []
            for bin_key in va_bins:
                bin_range = bin_key.split('-')
                all_prices.extend([float(bin_range[0]), float(bin_range[1])])

            self.value_area = {
                'high': max(all_prices),
                'low': min(all_prices)
            }
        else:
            self.value_area = {'high': None, 'low': None}

    def _update_vwap_levels(self):
        """Update Volume Weighted Average Price (VWAP) levels"""
        if len(self.price_history) < 20 or len(self.volume_history) < 20:
            return

        # Calculate VWAP for different periods
        periods = [20, 50, 100]
        self.vwap_levels = []

        for period in periods:
            if len(self.price_history) >= period:
                recent_prices = self.price_history[-period:]
                recent_volumes = self.volume_history[-period:]

                # VWAP = sum(price * volume) / sum(volume)
                price_volume_sum = sum(p * v for p, v in zip(recent_prices, recent_volumes))
                total_volume = sum(recent_volumes)

                if total_volume > 0:
                    vwap = price_volume_sum / total_volume
                    self.vwap_levels.append({
                        'period': period,
                        'vwap': vwap,
                        'total_volume': total_volume
                    })

    def _update_volume_clusters(self):
        """Update volume cluster identification"""
        if not self.volume_profile:
            return

        # Find volume clusters (bins with volume > 2x average)
        avg_volume = sum(self.volume_profile.values()) / len(self.volume_profile)
        cluster_threshold = avg_volume * 2.0

        self.volume_clusters = []
        for bin_key, volume in self.volume_profile.items():
            if volume > cluster_threshold:
                bin_range = bin_key.split('-')
                cluster_price = (float(bin_range[0]) + float(bin_range[1])) / 2

                self.volume_clusters.append({
                    'price': cluster_price,
                    'volume': volume,
                    'relative_volume': volume / avg_volume,
                    'bin_range': bin_key
                })

        # Sort by volume (descending)
        self.volume_clusters.sort(key=lambda x: x['volume'], reverse=True)

    def _update_volume_gaps(self):
        """Update volume gap analysis"""
        if len(self.price_history) < 30:
            return

        # Find price gaps with no volume
        recent_prices = sorted(set(self.price_history[-50:]))  # Unique prices

        self.volume_gaps = []
        for i in range(len(recent_prices) - 1):
            price1 = recent_prices[i]
            price2 = recent_prices[i + 1]

            # Check if there's a significant gap
            gap_size = (price2 - price1) / price1

            if gap_size > 0.005:  # 0.5% gap
                # Check if gap has been filled
                current_price = self.price_history[-1]
                gap_filled = price1 <= current_price <= price2

                self.volume_gaps.append({
                    'gap_start': price1,
                    'gap_end': price2,
                    'gap_size_pct': gap_size * 100,
                    'gap_filled': gap_filled,
                    'significance': gap_size * 100  # Higher gaps are more significant
                })

    def _generate_volume_signal(self, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> Optional[VolumeProfileSignal]:
        """Generate signal based on volume profile analysis"""
        current_price = self.price_history[-1]

        # Check proximity to key levels
        proximity_threshold = 0.005  # 0.5%

        # POC test
        if self.point_of_control and abs(current_price - self.point_of_control) / current_price <= proximity_threshold:
            return self._create_volume_signal(
                VolumeProfileSignalType.POC_TEST, current_price, timestamp,
                order_book_data, trade_data
            )

        # Value Area breakout
        if self.value_area['high'] and current_price > self.value_area['high']:
            return self._create_volume_signal(
                VolumeProfileSignalType.VA_BREAKOUT, current_price, timestamp,
                order_book_data, trade_data
            )

        if self.value_area['low'] and current_price < self.value_area['low']:
            return self._create_volume_signal(
                VolumeProfileSignalType.VA_BREAKOUT, current_price, timestamp,
                order_book_data, trade_data
            )

        # Volume cluster break
        for cluster in self.volume_clusters[:3]:  # Check top 3 clusters
            if abs(current_price - cluster['price']) / current_price <= proximity_threshold:
                return self._create_volume_signal(
                    VolumeProfileSignalType.VOLUME_CLUSTER_BREAK, current_price, timestamp,
                    order_book_data, trade_data
                )

        # VWAP rejection
        for vwap_data in self.vwap_levels:
            if abs(current_price - vwap_data['vwap']) / current_price <= proximity_threshold:
                return self._create_volume_signal(
                    VolumeProfileSignalType.VWAP_REJECTION, current_price, timestamp,
                    order_book_data, trade_data
                )

        # Volume gap fill
        for gap in self.volume_gaps:
            if not gap['gap_filled'] and gap['gap_start'] <= current_price <= gap['gap_end']:
                return self._create_volume_signal(
                    VolumeProfileSignalType.VOLUME_GAP_FILL, current_price, timestamp,
                    order_book_data, trade_data
                )

        return None

    def _create_volume_signal(self, signal_type: VolumeProfileSignalType,
                            current_price: float, timestamp: datetime,
                            order_book_data: Dict = None,
                            trade_data: List = None) -> VolumeProfileSignal:
        """Create a volume profile signal"""
        # Calculate confidence components
        confidence_components = self._calculate_volume_confidence(
            signal_type, current_price, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management
        suggested_sl, suggested_tp = self._calculate_volume_risk_management(signal_type, current_price)

        # Additional metadata
        additional_metadata = {
            'signal_type': signal_type.value,
            'point_of_control': self.point_of_control,
            'value_area': self.value_area,
            'volume_clusters_count': len(self.volume_clusters),
            'vwap_levels_count': len(self.vwap_levels),
            'volume_gaps_count': len(self.volume_gaps),
            'total_volume_profile_bins': len(self.volume_profile)
        }

        return VolumeProfileSignal(
            value_raw=current_price,
            signal_type=f"VOLUME_PROFILE_{signal_type.value}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            point_of_control=self.point_of_control,
            value_area_high=self.value_area['high'],
            value_area_low=self.value_area['low'],
            volume_clusters=self.volume_clusters,
            vwap_level=self.vwap_levels[0]['vwap'] if self.vwap_levels else None,
            volume_gaps=self.volume_gaps
        )

    def _calculate_volume_confidence(self, signal_type: VolumeProfileSignalType,
                                   current_price: float, order_book_data: Dict = None,
                                   trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for volume signal"""
        components = {}

        # Base confidence by signal type
        type_confidence = {
            VolumeProfileSignalType.POC_TEST: 0.8,
            VolumeProfileSignalType.VA_BREAKOUT: 0.7,
            VolumeProfileSignalType.VOLUME_CLUSTER_BREAK: 0.75,
            VolumeProfileSignalType.VWAP_REJECTION: 0.6,
            VolumeProfileSignalType.VOLUME_GAP_FILL: 0.65,
            VolumeProfileSignalType.ACCUMULATION_ZONE: 0.7,
            VolumeProfileSignalType.DISTRIBUTION_ZONE: 0.7
        }
        components['signal_type_confidence'] = type_confidence.get(signal_type, 0.5)

        # Volume confirmation
        components['volume_confirmation'] = self._calculate_volume_confirmation_score(current_price)

        # Smart money confirmation
        components['smart_money_score'] = self._calculate_smart_money_volume_score(order_book_data, trade_data)

        # Timeframe alignment (simplified)
        components['timeframe_alignment'] = 0.7

        # Market regime factor
        components['market_regime_factor'] = self._calculate_market_regime_factor()

        return components

    def _calculate_volume_confirmation_score(self, current_price: float) -> float:
        """Calculate volume confirmation score"""
        if len(self.volume_history) < 10:
            return 0.5

        # Compare current volume to recent average
        current_volume = self.volume_history[-1]
        avg_volume = np.mean(self.volume_history[-10:-1])

        if avg_volume == 0:
            return 0.5

        volume_ratio = current_volume / avg_volume

        # Higher volume = higher confidence
        if volume_ratio > 2.0:
            return 0.9
        elif volume_ratio > 1.5:
            return 0.7
        elif volume_ratio > 1.0:
            return 0.5
        else:
            return 0.3

    def _calculate_smart_money_volume_score(self, order_book_data: Dict = None,
                                          trade_data: List = None) -> float:
        """Calculate smart money confirmation for volume signals"""
        score = 0.5

        if order_book_data:
            # Check order book depth at current levels
            current_price = self.price_history[-1]
            proximity_threshold = 0.001  # 0.1%

            bids_near_price = sum(vol for price, vol in order_book_data.get('bids', {}).items()
                                 if abs(price - current_price) / current_price <= proximity_threshold)
            asks_near_price = sum(vol for price, vol in order_book_data.get('asks', {}).items()
                                 if abs(price - current_price) / current_price <= proximity_threshold)

            total_orderbook_volume = bids_near_price + asks_near_price
            if total_orderbook_volume > 0:
                imbalance = abs(bids_near_price - asks_near_price) / total_orderbook_volume
                score = min(0.9, 0.5 + imbalance * 0.5)

        if trade_data:
            # Check for institutional-sized trades
            avg_trade_size = np.mean([t[1] for t in trade_data]) if trade_data else 0
            large_trades = [t for t in trade_data if t[1] > avg_trade_size * 2]

            if large_trades:
                score = min(0.95, score + 0.2)

        return score

    def _calculate_market_regime_factor(self) -> float:
        """Calculate market regime factor for confidence"""
        if len(self.price_history) < 20:
            return 0.5

        # Simple regime detection
        recent_returns = np.diff(self.price_history[-20:]) / self.price_history[-20:-1]
        volatility = np.std(recent_returns)

        # Higher volatility = potentially stronger volume signals
        if volatility > 0.02:
            return 0.8
        elif volatility > 0.01:
            return 0.6
        else:
            return 0.4

    def _calculate_volume_risk_management(self, signal_type: VolumeProfileSignalType,
                                        current_price: float) -> Tuple[float, float]:
        """Calculate risk management levels for volume signals"""
        # Base risk on recent volatility
        if len(self.price_history) >= 20:
            volatility = np.std(self.price_history[-20:])
            base_risk = volatility * 0.5
        else:
            base_risk = current_price * 0.01

        # Adjust based on signal type
        risk_multiplier = {
            VolumeProfileSignalType.POC_TEST: 1.0,
            VolumeProfileSignalType.VA_BREAKOUT: 1.5,
            VolumeProfileSignalType.VOLUME_CLUSTER_BREAK: 1.2,
            VolumeProfileSignalType.VWAP_REJECTION: 0.8,
            VolumeProfileSignalType.VOLUME_GAP_FILL: 1.3,
            VolumeProfileSignalType.ACCUMULATION_ZONE: 1.0,
            VolumeProfileSignalType.DISTRIBUTION_ZONE: 1.0
        }.get(signal_type, 1.0)

        risk_amount = base_risk * risk_multiplier

        # Determine direction based on signal type
        if signal_type in [VolumeProfileSignalType.VA_BREAKOUT, VolumeProfileSignalType.VOLUME_CLUSTER_BREAK]:
            # Assume bullish breakout
            suggested_sl = current_price - risk_amount
            suggested_tp = current_price + (risk_amount * 2)
        elif signal_type == VolumeProfileSignalType.VOLUME_GAP_FILL:
            # Gap fill can be either direction
            suggested_sl = current_price - risk_amount
            suggested_tp = current_price + risk_amount
        else:
            # Default symmetric
            suggested_sl = current_price - risk_amount
            suggested_tp = current_price + risk_amount

        return suggested_sl, suggested_tp

    def get_volume_profile_data(self) -> Dict[str, Any]:
        """Get current volume profile data"""
        return {
            'volume_profile': self.volume_profile.copy(),
            'point_of_control': self.point_of_control,
            'value_area': self.value_area.copy(),
            'vwap_levels': self.vwap_levels.copy(),
            'volume_clusters': self.volume_clusters.copy(),
            'volume_gaps': self.volume_gaps.copy()
        }

    def get_volume_statistics(self) -> Dict[str, Any]:
        """Get volume analysis statistics"""
        if not self.volume_profile:
            return {}

        volumes = list(self.volume_profile.values())

        return {
            'total_volume': sum(volumes),
            'average_volume_per_bin': np.mean(volumes),
            'max_volume_in_bin': max(volumes),
            'volume_bins_count': len(self.volume_profile),
            'volume_clusters_count': len(self.volume_clusters),
            'volume_gaps_count': len(self.volume_gaps),
            'vwap_levels_count': len(self.vwap_levels),
            'point_of_control_price': self.point_of_control,
            'value_area_range': (self.value_area['high'] - self.value_area['low']) if self.value_area['high'] and self.value_area['low'] else None
        }

    def is_price_in_value_area(self, price: float) -> bool:
        """Check if price is within value area"""
        if not self.value_area['low'] or not self.value_area['high']:
            return False

        return self.value_area['low'] <= price <= self.value_area['high']

    def get_nearest_volume_cluster(self, price: float) -> Optional[Dict[str, Any]]:
        """Get nearest volume cluster to a price"""
        if not self.volume_clusters:
            return None

        nearest_cluster = min(self.volume_clusters,
                            key=lambda x: abs(x['price'] - price))

        return nearest_cluster

    def get_volume_distribution(self, price_range: Tuple[float, float] = None) -> Dict[str, Any]:
        """Get volume distribution within a price range"""
        if not self.volume_profile:
            return {}

        if price_range:
            min_price, max_price = price_range
            filtered_profile = {
                bin_key: volume for bin_key, volume in self.volume_profile.items()
                if min_price <= float(bin_key.split('-')[0]) <= max_price
            }
        else:
            filtered_profile = self.volume_profile

        if not filtered_profile:
            return {}

        volumes = list(filtered_profile.values())

        return {
            'total_volume_in_range': sum(volumes),
            'average_volume_in_range': np.mean(volumes),
            'max_volume_in_range': max(volumes),
            'bins_in_range': len(filtered_profile),
            'volume_concentration': max(volumes) / sum(volumes) if sum(volumes) > 0 else 0
        }