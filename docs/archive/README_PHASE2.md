# Algorithmic Trading System - Phase 2

Phase 2 introduces a feature queries endpoint, a comprehensive Streamlit research dashboard, and an enhanced gRPC streaming server.

## 1. Feature Queries Endpoint

The feature queries endpoint provides a flexible way to retrieve historical and real-time features for various financial instruments.

**Endpoint:** `GET /api/v1/features/{symbol}`

**Authentication:** Requires a valid JWT token.

**Query Parameters:**

*   `symbol` (str, required): The trading symbol (e.g., AAPL, GOOGL).
*   `start_date` (datetime, required): The start of the time range.
*   `end_date` (datetime, required): The end of the time range.
*   `feature_types` (List[str], required): A list of feature types to retrieve. Supported types: `market_data`, `indicators`, `volume_analysis`.
*   `aggregation` (str, optional, default: "1d"): The time aggregation level (e.g., `1m`, `5m`, `1h`, `1d`).

## Historical Documentation

This document represents the Phase 2 setup instructions from an earlier version of the system. It has been archived for reference purposes.

## Current Status

Phase 2 has been completed and integrated into the comprehensive system architecture. For current setup instructions, refer to the main documentation in the docs/ directory.