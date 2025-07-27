# FIX Connection and Session Configuration

FIX_SETTINGS = {
    'default': {
        'ConnectionType': 'initiator',
        'ReconnectInterval': 60,
        'FileStorePath': '/var/lib/quickfixj/client',
        'FileLogPath': '/var/lib/quickfixj/logs/client',
        'StartTime': '00:00:00',
        'EndTime': '00:00:00',
        'HeartBtInt': 30,
        'CheckLatency': 'Y',
        'Validation': 'Y',
    },
    'session': {
        'BeginString': 'FIX.4.4',
        'DefaultApplVerID': 'FIX.4.4',
        'TargetCompID': 'SERVER',
        'SenderCompID': 'CLIENT1',
        'SocketConnectHost': 'fix-gateway',
        'SocketConnectPort': 9876,
    }
}

# Message routing rules (placeholder)
MESSAGE_ROUTING = {
    'NewOrderSingle': 'execution_service',
    'MarketDataRequest': 'market_data_service',
}