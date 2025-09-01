
from typing import Dict, Any

from shared.config import settings

FIX_SETTINGS = {
    'default': {
        'ConnectionType': settings.FIX_CONNECTION_TYPE,
        'ReconnectInterval': settings.FIX_RECONNECT_INTERVAL,
        'FileStorePath': settings.FIX_FILE_STORE_PATH,
        'FileLogPath': settings.FIX_FILE_LOG_PATH,
        'StartTime': settings.FIX_START_TIME,
        'EndTime': settings.FIX_END_TIME,
        'HeartBtInt': settings.FIX_HEART_BT_INT,
        'CheckLatency': settings.FIX_CHECK_LATENCY,
        'Validation': settings.FIX_VALIDATION,
    },
    'session': {
        'BeginString': settings.FIX_BEGIN_STRING,
        'DefaultApplVerID': settings.FIX_DEFAULT_APPL_VER_ID,
        'TargetCompID': settings.FIX_TARGET_COMP_ID,
        'SenderCompID': settings.FIX_SENDER_COMP_ID,
        'SocketConnectHost': settings.FIX_SOCKET_CONNECT_HOST,
        'SocketConnectPort': settings.FIX_SOCKET_CONNECT_PORT,
    }
}

# Message routing rules (placeholder)
MESSAGE_ROUTING = {
    'NewOrderSingle': 'execution_service',
    'MarketDataRequest': 'market_data_service',
}
