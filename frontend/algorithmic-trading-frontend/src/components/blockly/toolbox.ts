export const toolbox = {
    "kind": "flyoutToolbox",
    "contents": [
        {
            "kind": "category",
            "name": "Indicators",
            "colour": "230",
            "contents": [
                {
                    "kind": "block",
                    "type": "indicator_sma"
                },
                {
                    "kind": "block",
                    "type": "indicator_ema"
                },
                {
                    "kind": "block",
                    "type": "indicator_rsi"
                },
                {
                    "kind": "block",
                    "type": "indicator_macd"
                },
                {
                    "kind": "block",
                    "type": "indicator_bollinger_bands"
                }
            ]
        },
        {
            "kind": "category",
            "name": "Conditions",
            "colour": "210",
            "contents": [
                {
                    "kind": "block",
                    "type": "condition_price_above"
                },
                {
                    "kind": "block",
                    "type": "condition_price_below"
                },
                {
                    "kind": "block",
                    "type": "condition_crossover"
                },
                {
                    "kind": "block",
                    "type": "condition_threshold"
                }
            ]
        },
        {
            "kind": "category",
            "name": "Actions",
            "colour": "160",
            "contents": [
                {
                    "kind": "block",
                    "type": "action_buy"
                },
                {
                    "kind": "block",
                    "type": "action_sell"
                },
                {
                    "kind": "block",
                    "type": "action_set_stop_loss"
                },
                {
                    "kind": "block",
                    "type": "action_set_take_profit"
                }
            ]
        },
        {
            "kind": "category",
            "name": "Risk",
            "colour": "290",
            "contents": [
                {
                    "kind": "block",
                    "type": "risk_position_sizing"
                },
                {
                    "kind": "block",
                    "type": "risk_max_drawdown"
                }
            ]
        }
    ]
};