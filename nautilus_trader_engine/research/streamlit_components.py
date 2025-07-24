import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def candlestick_chart(df: pd.DataFrame, symbol: str):
    """
    Displays a candlestick chart for the given symbol.
    """
    st.subheader(f"Candlestick Chart: {symbol}")
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'])])
    fig.update_layout(
        title=f"{symbol} Candlestick Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig)

def indicator_plot(df: pd.DataFrame, indicator: str):
    """
    Displays a plot for a given technical indicator.
    """
    st.subheader(f"Indicator: {indicator}")
    st.line_chart(df[indicator])

def performance_metrics_card(metrics: dict):
    """
    Displays a card with key performance metrics.
    """
    st.subheader("Performance Metrics")
    for key, value in metrics.items():
        st.metric(label=key, value=f"{value:.2f}")

def feature_correlation_heatmap(df: pd.DataFrame):
    """
    Displays a heatmap of feature correlations.
    """
    st.subheader("Feature Correlation Heatmap")
    corr = df.corr()
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale='Viridis'
    ))
    st.plotly_chart(fig)