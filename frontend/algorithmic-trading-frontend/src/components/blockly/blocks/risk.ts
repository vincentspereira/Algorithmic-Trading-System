import * as Blockly from 'blockly/core';

Blockly.defineBlocksWithJsonArray([
    {
        "type": "risk_position_sizing",
        "message0": "Position Size(risk per trade: %1%%)",
        "args0": [
            {
                "type": "field_number",
                "name": "RISK_PERCENT",
                "value": 1,
                "min": 0,
                "max": 100
            }
        ],
        "output": "Number",
        "colour": 290,
        "tooltip": "Calculates the position size based on a percentage of the account to risk.",
        "helpUrl": ""
    },
    {
        "type": "risk_max_drawdown",
        "message0": "Max Drawdown(percent: %1%%)",
        "args0": [
            {
                "type": "field_number",
                "name": "MAX_DRAWDOWN_PERCENT",
                "value": 20,
                "min": 0,
                "max": 100
            }
        ],
        "previousStatement": null,
        "nextStatement": null,
        "colour": 290,
        "tooltip": "Sets the maximum allowed drawdown for the strategy.",
        "helpUrl": ""
    }
]);