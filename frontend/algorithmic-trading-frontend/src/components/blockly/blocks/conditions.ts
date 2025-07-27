import * as Blockly from 'blockly/core';

Blockly.defineBlocksWithJsonArray([
    {
        "type": "condition_price_above",
        "message0": "Price above %1",
        "args0": [
            {
                "type": "input_value",
                "name": "LEVEL",
                "check": "Number"
            }
        ],
        "output": "Boolean",
        "colour": 210,
        "tooltip": "Checks if the current price is above a certain level.",
        "helpUrl": ""
    },
    {
        "type": "condition_price_below",
        "message0": "Price below %1",
        "args0": [
            {
                "type": "input_value",
                "name": "LEVEL",
                "check": "Number"
            }
        ],
        "output": "Boolean",
        "colour": 210,
        "tooltip": "Checks if the current price is below a certain level.",
        "helpUrl": ""
    },
    {
        "type": "condition_crossover",
        "message0": "Crossover of %1 and %2",
        "args0": [
            {
                "type": "input_value",
                "name": "INDICATOR1",
                "check": "Number"
            },
            {
                "type": "input_value",
                "name": "INDICATOR2",
                "check": "Number"
            }
        ],
        "output": "Boolean",
        "colour": 210,
        "tooltip": "Checks if the first indicator has crossed over the second indicator.",
        "helpUrl": ""
    },
    {
        "type": "condition_threshold",
        "message0": "%1 is %2 than %3",
        "args0": [
            {
                "type": "input_value",
                "name": "INDICATOR",
                "check": "Number"
            },
            {
                "type": "field_dropdown",
                "name": "OPERATOR",
                "options": [
                    ["greater", "GREATER"],
                    ["less", "LESS"]
                ]
            },
            {
                "type": "input_value",
                "name": "THRESHOLD",
                "check": "Number"
            }
        ],
        "output": "Boolean",
        "colour": 210,
        "tooltip": "Checks if an indicator is above or below a certain threshold.",
        "helpUrl": ""
    }
]);