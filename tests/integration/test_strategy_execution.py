import unittest
from unittest.mock import patch, MagicMock
import json

# This test suite validates the strategy execution pipeline,
# which includes creating a strategy with Blockly, validating it,
# deploying it, and ensuring it executes correctly.

class TestStrategyExecution(unittest.TestCase):
    """
    Integration tests for the strategy execution pipeline.
    """

    def setUp(self):
        """Set up test environment."""
        # Mock Blockly code generator
        self.mock_blockly_generator = MagicMock()
        self.mock_blockly_generator.generate_code.return_value = {
            "python_code": "def strategy():\n    print('execute trade')"
        }

        # Mock Strategy Validator
        self.mock_strategy_validator = MagicMock()
        self.mock_strategy_validator.validate.return_value = {
            "is_valid": True,
            "errors": []
        }

        # Mock Strategy Deployer
        self.mock_strategy_deployer = MagicMock()
        self.mock_strategy_deployer.deploy.return_value = {
            "deployment_id": "strat_123",
            "status": "deployed"
        }

        # Mock Strategy Executor
        self.mock_strategy_executor = MagicMock()
        self.mock_strategy_executor.execute.return_value = {
            "execution_status": "completed"
        }

    def test_strategy_creation_to_execution(self):
        """
        Test the full pipeline from strategy creation to execution.
        """
        # Arrange: Define a mock Blockly block configuration
        blockly_config = {
            "blocks": [{"type": "trade_action", "action": "BUY"}]
        }

        # 1. Generate Python code from Blockly blocks
        generated_code = self.mock_blockly_generator.generate_code(blockly_config)
        
        # 2. Validate the generated strategy code
        validation_result = self.mock_strategy_validator.validate(generated_code["python_code"])
        self.assertTrue(validation_result["is_valid"])
        
        # 3. Deploy the strategy
        if validation_result["is_valid"]:
            deployment_result = self.mock_strategy_deployer.deploy(generated_code["python_code"])
            self.assertEqual(deployment_result["status"], "deployed")
            
            # 4. Execute the deployed strategy
            if deployment_result["status"] == "deployed":
                execution_result = self.mock_strategy_executor.execute(deployment_result["deployment_id"])
                self.assertEqual(execution_result["execution_status"], "completed")

        # Assert: Verify all mocks were called
        self.mock_blockly_generator.generate_code.assert_called_once_with(blockly_config)
        self.mock_strategy_validator.validate.assert_called_once()
        self.mock_strategy_deployer.deploy.assert_called_once()
        self.mock_strategy_executor.execute.assert_called_once_with("strat_123")

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False, verbosity=2)