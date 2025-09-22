"""
Shared utility functions for the algorithmic trading system.
"""

import logging
import os
import yaml
from pathlib import Path

def get_project_root() -> Path:
    """Returns the project root folder."""
    return Path(__file__).resolve().parent.parent.parent

def load_config(config_file: str = "config.yaml") -> dict:
    """
    Loads a YAML configuration file.

    Args:
        config_file: The name of the configuration file.

    Returns:
        A dictionary containing the configuration.
    """
    config_path = get_project_root() / "config" / config_file
    with open(config_path, "r") as f:
        return yaml.safe_load(f)