import * as Blockly from 'blockly/core';

Blockly.defineBlocksWithJsonArray([
    {
        "type": "action_buy",
        "message0": "Buy(amount: %1)",
        "args0": [
            {
                "type": "field_number",
                "name": "AMOUNT",
                "value": 1
            }
        ],
        "previousStatement": null,
        "nextStatement": null,
        "colour": 160,
        "tooltip": "Executes a buy order.",
        "helpUrl": ""
    },
    {
        "type": "action_sell",
        "message0": "Sell(amount: %1)",
        "args0": [
            {
                "type": "field_number",
                "name": "AMOUNT",
                "value": 1
            }
        ],
        "previousStatement": null,
        "nextStatement": null,
        "colour": 160,
        "tooltip": "Executes a sell order.",
        "helpUrl": ""
    },
    {
        "type": "action_set_stop_loss",
        "message0": "Set Stop Loss(price: %1)",
        "args0": [
            {
                "type": "input_value",
                "name": "PRICE",
                "check": "Number"
            }
        ],
        "previousStatement": null,
        "nextStatement": null,
        "colour": 160,
        "tooltip": "Sets a stop loss order at a specified price.",
        "helpUrl": ""
    },
    {
        "type": "action_set_take_profit",
        "message0": "Set Take Profit(price: %1)",
        "args0": [
            {
                "type": "input_value",
                "name": "PRICE",
                "check": "Number"
            }
        ],
        "previousStatement": null,
        "nextStatement": null,
        "colour": 160,
        "tooltip": "Sets a take profit order at a specified price.",
        "helpUrl": ""
    }
]);