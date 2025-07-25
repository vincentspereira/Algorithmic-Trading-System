"""
Generate Sample Market Data for AI Assistant Feature Store

This script generates sample market data in Parquet format for testing
the Feast feature store integration.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path


def generate_market_data(tickers=['AAPL', 'GOOGL', 'MSFT'], days=30):
    """Generate sample market data for specified tickers and days"""
    
    # Create date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    all_data = []
    
    for ticker in tickers:
        # Set different base prices for each ticker
        base_prices = {'AAPL': 150.0, 'GOOGL': 2800.0, 'MSFT': 300.0}
        base_price = base_prices.get(ticker, 100.0)
        
        # Generate price data with some randomness
        np.random.seed(hash(ticker) % 2**32)  # Consistent seed per ticker
        
        prices = []
        current_price = base_price
        
        for i, date in enumerate(date_range):
            # Add some trend and volatility
            daily_return = np.random.normal(0.001, 0.02)  # 0.1% mean, 2% volatility
            current_price *= (1 + daily_return)
            
            # Generate OHLC data
            high_factor = 1 + abs(np.random.normal(0, 0.01))
            low_factor = 1 - abs(np.random.normal(0, 0.01))
            
            open_price = current_price * np.random.uniform(0.99, 1.01)
            high_price = current_price * high_factor
            low_price = current_price * low_factor
            close_price = current_price
            
            # Generate volume (higher volume on higher volatility days)
            base_volume = {'AAPL': 50000000, 'GOOGL': 25000000, 'MSFT': 40000000}
            volume = int(base_volume.get(ticker, 30000000) * np.random.uniform(0.5, 2.0))
            
            # Calculate additional metrics
            vwap = (high_price + low_price + close_price) / 3
            price_change_pct = ((close_price - open_price) / open_price) * 100
            
            # Generate technical indicators (simplified)
            rsi_14 = 30 + (np.random.random() * 40)  # RSI between 30-70
            macd_line = np.random.normal(0, 2)
            macd_signal = macd_line + np.random.normal(0, 0.5)
            
            # Bollinger bands (simplified)
            bb_middle = close_price
            bb_width = close_price * 0.04  # 4% width
            bollinger_upper = bb_middle + bb_width
            bollinger_lower = bb_middle - bb_width
            
            # Moving averages (simplified)
            sma_20 = close_price * np.random.uniform(0.98, 1.02)
            sma_50 = close_price * np.random.uniform(0.95, 1.05)
            ema_12 = close_price * np.random.uniform(0.99, 1.01)
            ema_26 = close_price * np.random.uniform(0.97, 1.03)
            
            # ATR (simplified)
            atr_14 = close_price * np.random.uniform(0.01, 0.03)
            
            # Market sentiment and additional metrics
            sentiment_score = np.random.uniform(-0.5, 0.5)
            news_sentiment = np.random.uniform(-1, 1)
            social_sentiment = np.random.uniform(-1, 1)
            analyst_rating = np.random.uniform(1, 5)
            
            # Momentum indicators
            price_momentum_1d = price_change_pct
            price_momentum_7d = np.random.normal(0, 5)
            volume_momentum = np.random.uniform(0.8, 1.2)
            sector_performance = np.random.uniform(-2, 2)
            
            # Market cap and PE ratio (simplified)
            shares_outstanding = {'AAPL': 16000000000, 'GOOGL': 13000000000, 'MSFT': 7500000000}
            market_cap = close_price * shares_outstanding.get(ticker, 10000000000)
            pe_ratio = np.random.uniform(15, 35)
            
            # 20-day volatility (simplified)
            volatility_20d = np.random.uniform(0.15, 0.45)
            
            # Create timestamps
            event_timestamp = pd.Timestamp(date)
            created_timestamp = pd.Timestamp(datetime.now())
            
            row_data = {
                'ticker': ticker,
                'event_timestamp': event_timestamp,
                'created_timestamp': created_timestamp,
                
                # Daily market features
                'opening_price': round(open_price, 2),
                'daily_high': round(high_price, 2),
                'daily_low': round(low_price, 2),
                'closing_price': round(close_price, 2),
                'daily_volume': volume,
                'vwap': round(vwap, 2),
                'price_change_percentage': round(price_change_pct, 2),
                'market_cap': int(market_cap),
                'pe_ratio': round(pe_ratio, 2),
                'volatility_20d': round(volatility_20d, 3),
                
                # Technical indicators
                'rsi_14': round(rsi_14, 2),
                'macd_line': round(macd_line, 3),
                'macd_signal': round(macd_signal, 3),
                'bollinger_upper': round(bollinger_upper, 2),
                'bollinger_lower': round(bollinger_lower, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'ema_12': round(ema_12, 2),
                'ema_26': round(ema_26, 2),
                'atr_14': round(atr_14, 2),
                
                # Market sentiment
                'sentiment_score': round(sentiment_score, 3),
                'news_sentiment': round(news_sentiment, 3),
                'social_sentiment': round(social_sentiment, 3),
                'analyst_rating': round(analyst_rating, 2),
                'price_momentum_1d': round(price_momentum_1d, 2),
                'price_momentum_7d': round(price_momentum_7d, 2),
                'volume_momentum': round(volume_momentum, 3),
                'sector_performance': round(sector_performance, 2),
            }
            
            all_data.append(row_data)
            prices.append(close_price)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Sort by ticker and date
    df = df.sort_values(['ticker', 'event_timestamp']).reset_index(drop=True)
    
    return df


def save_parquet_file(df, file_path):
    """Save DataFrame to Parquet file"""
    
    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to PyArrow table and save
    table = pa.Table.from_pandas(df)
    pq.write_table(table, file_path)
    
    print(f"✓ Sample market data saved to {file_path}")
    print(f"  - Records: {len(df)}")
    print(f"  - Tickers: {df['ticker'].unique().tolist()}")
    print(f"  - Date range: {df['event_timestamp'].min()} to {df['event_timestamp'].max()}")


def main():
    """Main function to generate and save sample data"""
    print("Generating sample market data for AI Assistant Feature Store...")
    print("=" * 60)
    
    # Generate data
    df = generate_market_data(tickers=['AAPL', 'GOOGL', 'MSFT'], days=30)
    
    # Save to parquet file
    file_path = "data/market_data.parquet"
    save_parquet_file(df, file_path)
    
    # Display sample data
    print(f"\nSample data preview:")
    print(df[['ticker', 'event_timestamp', 'closing_price', 'daily_volume', 'rsi_14']].head(10))
    
    print(f"\nData generation completed successfully!")


if __name__ == "__main__":
    main()