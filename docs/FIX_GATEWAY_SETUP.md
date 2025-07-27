# FIX Gateway Setup Guide

This document outlines the architecture, configuration, and testing procedures for the FIX Gateway, which provides institutional trading connectivity for the algorithmic trading system.

## 1. Architecture Overview

The FIX Gateway is implemented using QuickFIX/J, a Java-based open-source FIX engine. It runs as a dedicated Docker container (`fix-gateway`) and is responsible for all FIX session management, message parsing, and routing.

The gateway consists of two main components:
- **Acceptor:** Listens for incoming FIX connections from counterparties (e.g., brokers, exchanges). This is used for testing purposes with a client.
- **Initiator:** Establishes outgoing FIX connections to counterparties.

The Python-based `nautilus_trader_engine` communicates with the FIX Gateway to send and receive FIX messages.

## 2. Configuration

### Docker Compose

The `fix-gateway` service is defined in `docker-compose.yml`. Key configurations include:
- **Image:** `ghcr.io/quickfix-j/quickfix-j:2.3.0`
- **Ports:** `9876` (acceptor) and `9877` (initiator).
- **Volumes:**
  - `config/fix` is mounted to `/etc/quickfixj` for configuration files.
  - `fix_gateway_data` is used for persistent FIX session state and logs.

### QuickFIX/J Configuration

Configuration files are located in `config/fix/`:

- **`quickfixj-client.cfg`:** Configures the initiator (our side) for connecting to a FIX server.
- **`quickfixj-server.cfg`:** Configures the acceptor for local testing.
- **`FIX44.xml`:** The data dictionary for the FIX 4.4 protocol.

## 3. Testing Procedures

1.  **Start the Docker Environment:**
    ```bash
    docker-compose up -d fix-gateway
    ```

2.  **Run the Python FIX Client:**
    Execute the `fix_client.py` script to connect to the test acceptor:
    ```bash
    python nautilus_trader_engine/adapters/fix_client.py
    ```

3.  **Monitor Logs:**
    Check the logs for both the Docker container and the Python client to ensure a successful logon.

## 4. Troubleshooting Common Issues

- **Connection Refused:**
  - Verify that the `fix-gateway` container is running.
  - Check that the `SocketConnectHost` and `SocketConnectPort` in `quickfixj-client.cfg` are correct.

- **Session Disconnects:**
  - Ensure `SenderCompID` and `TargetCompID` are correctly configured and match on both client and server.
  - Check `HeartBtInt` (heartbeat interval) to prevent timeouts.

- **Invalid Message:**
  - Confirm that both sides are using the same FIX version and data dictionary (`FIX44.xml`).