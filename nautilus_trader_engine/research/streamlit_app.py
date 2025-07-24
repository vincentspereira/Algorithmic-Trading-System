import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import grpc
from nautilus_trader_engine.api.generated import market_data_pb2, market_data_pb2_grpc
from .streamlit_components import (
    candlestick_chart,
    indicator_plot,
    performance_metrics_card,
    feature_correlation_heatmap
)

# --- Configuration ---
API_URL = "http://localhost:8001/api/v1"
GRPC_SERVER_ADDRESS = "localhost:50051"

# --- Helper Functions ---

def get_features_from_api(symbol, start_date, end_date, feature_types, aggregation):
    """Fetches features from the FastAPI endpoint."""
    try:
        response = requests.get(
            f"{API_URL}/features/{symbol}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "feature_types": feature_types,
                "aggregation": aggregation,
            },
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None

def get_grpc_stream():
    """Establishes a connection to the gRPC server."""
    try:
        channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
        stub = market_data_pb2_grpc.MarketDataStub(channel)
        return stub
    except Exception as e:
        st.error(f"Error connecting to gRPC server: {e}")
        return None

# --- Main Application ---

st.set_page_config(layout="wide", page_title="Nautilus Trading Research Dashboard")
st.title("Nautilus Trading Research Dashboard")

# --- Authentication ---
st.sidebar.title("Authentication")
username = st.sidebar.text_input("Username", "demo")
password = st.sidebar.text_input("Password", "demo123", type="password")

if st.sidebar.button("Login"):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        st.session_state.access_token = response.json()["access_token"]
        st.sidebar.success("Login successful!")
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Login failed: {e}")


# --- Sidebar Controls ---
st.sidebar.title("Controls")
symbol = st.sidebar.text_input("Symbol", "AAPL")
start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("End Date", datetime.now())
aggregation = st.sidebar.selectbox("Aggregation", ["1m", "5m", "1h", "1d"], index=3)
feature_types = st.sidebar.multiselect(
    "Feature Types",
    ["market_data", "indicators", "volume_analysis"],
    default=["market_data", "indicators"]
)

if st.sidebar.button("Fetch Data"):
    if 'access_token' not in st.session_state:
        st.warning("Please log in to fetch data.")
    else:
        st.session_state.features_data = get_features_from_api(
            symbol, start_date, end_date, feature_types, aggregation
        )

# --- Dashboard Display ---
if 'features_data' in st.session_state and st.session_state.features_data:
    data = st.session_state.features_data
    st.header(f"Analysis for {data['symbol']}")

    # Create a DataFrame from the feature data
    # This is a simplified example; a real implementation would need more robust parsing
    df_data = {}
    for feature_set in data.get('features', []):
        df_data.update(feature_set['data'])
    
    # Ensure all lists have the same length by padding with None
    max_len = max(len(v) for v in df_data.values() if isinstance(v, list))
    for k, v in df_data.items():
        if isinstance(v, list):
            df_data[k] = v + [None] * (max_len - len(v))

    df = pd.DataFrame(df_data)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Display components
    if "market_data" in feature_types and not df.empty and all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close']):
        candlestick_chart(df, data['symbol'])

    if "indicators" in feature_types:
        for col in df.columns:
            if col.upper() in ["SMA_50", "RSI_14"] and col in df.columns: # Example indicators
                indicator_plot(df, col)

    # placeholder for backtesting results
    st.subheader("Backtesting Results")
    st.text("Backtesting results will be displayed here.")
    
    # placeholder for performance metrics
    dummy_metrics = {"Sharpe Ratio": 1.5, "Total Return": 25.0, "Max Drawdown": -10.0}
    performance_metrics_card(dummy_metrics)

    # placeholder for feature correlation
    if not df.empty:
        # Select only numeric columns for correlation
        numeric_df = df.select_dtypes(include=np.number)
        if not numeric_df.empty:
            feature_correlation_heatmap(numeric_df)

# --- Real-time Data Streaming ---
st.sidebar.title("Real-time Data")
if st.sidebar.button("Start Real-time Stream"):
    stub = get_grpc_stream()
    if stub:
        st.subheader("Real-time Market Data Stream")
        placeholder = st.empty()
        try:
            request = market_data_pb2.SubscriptionRequest(symbols=[symbol])
            for tick in stub.StreamMarketData(request):
                with placeholder.container():
                     st.write(f"**{tick.symbol}**: Price - ${tick.price:.2f}, Volume - {tick.volume}, Timestamp - {tick.timestamp}")
        except grpc.RpcError as e:
            st.error(f"gRPC stream error: {e.details()}")
        except Exception as e:
            st.error(f"An unexpected error occurred during streaming: {e}")