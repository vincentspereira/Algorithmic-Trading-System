# nautilus_trader_engine/rl/training/model_registry.py

"""
Management of trained RL models.

This module provides a simple registry for saving, versioning, and loading
trained RL models, their configurations, and performance metrics.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List

class ModelRegistry:
    """
    Manages the storage and retrieval of trained RL models.
    """

    def __init__(self, registry_path: str = "trained_models/registry"):
        self.registry_path = registry_path
        self.metadata_file = os.path.join(registry_path, "metadata.json")
        os.makedirs(self.registry_path, exist_ok=True)
        if not os.path.exists(self.metadata_file):
            self._save_metadata([])

    def _load_metadata(self) -> List[Dict[str, Any]]:
        with open(self.metadata_file, "r") as f:
            return json.load(f)

    def _save_metadata(self, metadata: List[Dict[str, Any]]):
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)

    def register_model(
        self,
        model_path: str,
        agent_name: str,
        hyperparams: Dict[str, Any],
        performance_metrics: Dict[str, float],
    ) -> str:
        """
        Registers a new model in the registry.

        Args:
            model_path (str): The path to the saved model file.
            agent_name (str): The name of the RL agent.
            hyperparams (dict): The hyperparameters used for training.
            performance_metrics (dict): Key performance indicators from backtesting.

        Returns:
            The ID of the newly registered model.
        """
        model_id = f"{agent_name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        model_dir = os.path.join(self.registry_path, model_id)
        os.makedirs(model_dir, exist_ok=True)

        # Copy model file to the registry
        shutil.copy(model_path, os.path.join(model_dir, "model.zip"))

        model_info = {
            "id": model_id,
            "agent_name": agent_name,
            "registration_date": datetime.now(timezone.utc).isoformat(),
            "hyperparameters": hyperparams,
            "performance": performance_metrics,
            "path": os.path.join(model_dir, "model.zip"),
        }
        
        # Save model-specific info
        with open(os.path.join(model_dir, "info.json"), "w") as f:
            json.dump(model_info, f, indent=4)

        # Update master metadata file
        metadata = self._load_metadata()
        metadata.append(model_info)
        self._save_metadata(metadata)

        return model_id

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Lists all registered models.

        Returns:
            A list of dictionaries, each containing information about a model.
        """
        return self._load_metadata()

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Retrieves information for a specific model.

        Args:
            model_id (str): The ID of the model.

        Returns:
            A dictionary with the model's information.
        """
        metadata = self._load_metadata()
        for model_info in metadata:
            if model_info["id"] == model_id:
                return model_info
        raise ValueError(f"Model with ID '{model_id}' not found.")

    def get_model_path(self, model_id: str) -> str:
        """
        Gets the file path of a registered model.

        Args:
            model_id (str): The ID of the model.

        Returns:
            The file path to the model.
        """
        model_info = self.get_model_info(model_id)
        return model_info["path"]