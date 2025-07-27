import * as Blockly from 'blockly/core';

Blockly.defineBlocksWithJsonArray([
    {
        "type": "indicator_sma",
        "message0": "SMA(period: %1, source: %2)",
        "args0": [
            {
                "type": "field_number",
                "name": "PERIOD",
                "value": 20
            },
            {
                "type": "field_dropdown",
                "name": "SOURCE",
                "options": [
                    ["close", "close"],
                    ["open", "open"],
                    ["high", "high"],
                    ["low", "low"]
                ]
            }
        ],
        "output": "Number",
        "colour": 230,
        "tooltip": "Simple Moving Average",
        "helpUrl": ""
    },
    {
        "type": "indicator_ema",
        "message0": "EMA(period: %1, source: %2)",
        "args0": [
            {
                "type": "field_number",
                "name": "PERIOD",
                "value": 20
            },
            {
                "type": "field_dropdown",
                "name": "SOURCE",
                "options": [
                    ["close", "close"],
                    ["open", "open"],
                    ["high", "high"],
                    ["low", "low"]
                ]
            }
        ],
        "output": "Number",
        "colour": 230,
        "tooltip": "Exponential Moving Average",
        "helpUrl": ""
    },
    {
        "type": "indicator_rsi",
        "message0": "RSI(period: %1, source: %2)",
        "args0": [
            {
                "type": "field_number",
                "name": "PERIOD",
                "value": 14
            },
            {
                "type": "field_dropdown",
                "name": "SOURCE",
                "options": [
                    ["close", "close"],
                    ["open", "open"],
                    ["high", "high"],
                    ["low", "low"]
                ]
            }
        ],
        "output": "Number",
        "colour": 230,
        "tooltip": "Relative Strength Index",
        "helpUrl": ""
    },
    {
        "type": "indicator_macd",
        "message0": "MACD(fast: %1, slow: %2, signal: %3, source: %4)",
        "args0": [
            {
                "type": "field_number",
                "name": "FAST",
                "value": 12
            },
            {
                "type": "field_number",
                "name": "SLOW",
                "value": 26
            },
            {
                "type": "field_number",
                "name": "SIGNAL",
                "value": 9
            },
            {
                "type": "field_dropdown",
                "name": "SOURCE",
                "options": [
                    ["close", "close"],
                    ["open", "open"],
                    ["high", "high"],
                    ["low", "low"]
                ]
            }
        ],
        "output": "Object",
        "colour": 230,
        "tooltip": "Moving Average Convergence Divergence",
        "helpUrl": ""
    },
    {
        "type": "indicator_bollinger_bands",
        "message0": "Bollinger Bands(period: %1, std_dev: %2, source: %3)",
        "args0": [
            {
                "type": "field_number",
                "name": "PERIOD",
                "value": 20
            },
            {
                "type": "field_number",
                "name": "STD_DEV",
                "value": 2
            },
            {
                "type": "field_dropdown",
                "name": "SOURCE",
                "options": [
                    ["close", "close"],
                    ["open", "open"],
                    ["high", "high"],
                    ["low", "low"]
                ]
            }
        ],
        "output": "Object",
        "colour": 230,
        "tooltip": "Bollinger Bands",
        "helpUrl": ""
    }
]);