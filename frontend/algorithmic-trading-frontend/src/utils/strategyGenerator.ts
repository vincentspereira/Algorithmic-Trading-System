import * as Blockly from 'blockly/core';
import { pythonGenerator } from 'blockly/python';

pythonGenerator.forBlock['indicator_sma'] = function(block: Blockly.Block) {
  const period = block.getFieldValue('PERIOD');
  const source = block.getFieldValue('SOURCE');
  const code = `self.sma(period=${period}, source='${source}')`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['indicator_ema'] = function(block: Blockly.Block) {
  const period = block.getFieldValue('PERIOD');
  const source = block.getFieldValue('SOURCE');
  const code = `self.ema(period=${period}, source='${source}')`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['indicator_rsi'] = function(block: Blockly.Block) {
  const period = block.getFieldValue('PERIOD');
  const source = block.getFieldValue('SOURCE');
  const code = `self.rsi(period=${period}, source='${source}')`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['indicator_macd'] = function(block: Blockly.Block) {
  const fast = block.getFieldValue('FAST');
  const slow = block.getFieldValue('SLOW');
  const signal = block.getFieldValue('SIGNAL');
  const source = block.getFieldValue('SOURCE');
  const code = `self.macd(fast_period=${fast}, slow_period=${slow}, signal_period=${signal}, source='${source}')`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['indicator_bollinger_bands'] = function(block: Blockly.Block) {
  const period = block.getFieldValue('PERIOD');
  const std_dev = block.getFieldValue('STD_DEV');
  const source = block.getFieldValue('SOURCE');
  const code = `self.bollinger_bands(period=${period}, std_dev=${std_dev}, source='${source}')`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['condition_price_above'] = function(block: Blockly.Block) {
  const level = pythonGenerator.valueToCode(block, 'LEVEL', pythonGenerator.ORDER_ATOMIC);
  const code = `self.price > ${level}`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['condition_price_below'] = function(block: Blockly.Block) {
  const level = pythonGenerator.valueToCode(block, 'LEVEL', pythonGenerator.ORDER_ATOMIC);
  const code = `self.price < ${level}`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['condition_crossover'] = function(block: Blockly.Block) {
  const indicator1 = pythonGenerator.valueToCode(block, 'INDICATOR1', pythonGenerator.ORDER_ATOMIC);
  const indicator2 = pythonGenerator.valueToCode(block, 'INDICATOR2', pythonGenerator.ORDER_ATOMIC);
  const code = `self.crossover(${indicator1}, ${indicator2})`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['condition_threshold'] = function(block: Blockly.Block) {
  const indicator = pythonGenerator.valueToCode(block, 'INDICATOR', pythonGenerator.ORDER_ATOMIC);
  const operator = block.getFieldValue('OPERATOR');
  const threshold = pythonGenerator.valueToCode(block, 'THRESHOLD', pythonGenerator.ORDER_ATOMIC);
  const op = operator === 'GREATER' ? '>' : '<';
  const code = `${indicator} ${op} ${threshold}`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['action_buy'] = function(block: Blockly.Block) {
  const amount = block.getFieldValue('AMOUNT');
  return `self.buy(amount=${amount})\n`;
};

pythonGenerator.forBlock['action_sell'] = function(block: Blockly.Block) {
  const amount = block.getFieldValue('AMOUNT');
  return `self.sell(amount=${amount})\n`;
};

pythonGenerator.forBlock['action_set_stop_loss'] = function(block: Blockly.Block) {
  const price = pythonGenerator.valueToCode(block, 'PRICE', pythonGenerator.ORDER_ATOMIC);
  return `self.set_stop_loss(price=${price})\n`;
};

pythonGenerator.forBlock['action_set_take_profit'] = function(block: Blockly.Block) {
  const price = pythonGenerator.valueToCode(block, 'PRICE', pythonGenerator.ORDER_ATOMIC);
  return `self.set_take_profit(price=${price})\n`;
};

pythonGenerator.forBlock['risk_position_sizing'] = function(block: Blockly.Block) {
  const risk_percent = block.getFieldValue('RISK_PERCENT');
  const code = `self.position_size(risk_percent=${risk_percent})`;
  return [code, pythonGenerator.ORDER_ATOMIC];
};

pythonGenerator.forBlock['risk_max_drawdown'] = function(block: Blockly.Block) {
    const max_drawdown_percent = block.getFieldValue('MAX_DRAWDOWN_PERCENT');
    return `self.set_max_drawdown(percent=${max_drawdown_percent})\n`;
};

export const generateStrategyCode = (workspace: Blockly.Workspace): string => {
    const code = pythonGenerator.workspaceToCode(workspace);
    return `
from nautilus_trader.model.strategy import Strategy
from nautilus_trader_engine.strategies.blockly_strategy_template import BlocklyStrategyTemplate

class GeneratedStrategy(BlocklyStrategyTemplate):
    def on_tick(self):
        ${code.replace(/\n/g, '\n        ')}
`;
};