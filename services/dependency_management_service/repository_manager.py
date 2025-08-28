"""
Repository management system for dependency management.

Handles repository tiering, monitoring, and automated updates to ensure the stability
and security of the algorithmic trading platform. This script is responsible for
forking repositories, setting up branch protection, and managing dependencies based on
a tiered configuration file.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import requests
from requests.exceptions import RequestException

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class BranchProtection:
    """
    Data class for branch protection rules configuration.

    Attributes:
        requires_pull_request (bool): Whether to require a pull request before merging.
        required_reviewers (int): The number of required reviewers for a pull request.
        dismiss_stale_reviews (bool): Whether to dismiss stale pull request approvals when new commits are pushed.
        require_up_to_date (bool): Whether to require branches to be up to date before merging.
    """

    requires_pull_request: bool = True
    required_reviewers: int = 1
    dismiss_stale_reviews: bool = False
    require_up_to_date: bool = True


@dataclass
class Dependency:
    """
    Data class for dependency repository configuration.

    Attributes:
        name (str): The name of the dependency.
        repository (str): The URL of the original repository.
        fork (str): The URL of the forked repository.
        version (str): The version of the dependency.
        customizations (List[str]): A list of customizations made to the dependency.
        branch_protection (BranchProtection): The branch protection rules for the dependency.
    """

    name: str
    repository: str
    fork: str
    version: str
    customizations: List[str]
    branch_protection: BranchProtection


@dataclass
class TierConfig:
    """
    Data class for a dependency tier configuration.

    Attributes:
        description (str): A description of the tier.
        dependencies (List[Dependency]): A list of dependencies in the tier.
    """

    description: str
    dependencies: List[Dependency]


class RepositoryManager:
    """
    Manages tiered dependencies, including forking, branch protection, and configuration.

    This class reads a configuration file that defines tiers of dependencies and
    automates the process of setting up these dependencies in a controlled and

    secure manner.

    Attributes:
        config_path (Path): The path to the dependency configuration file.
        github_token (str): The GitHub token for API authentication.
        config (Dict): The loaded configuration from the JSON file.
        github_api_base_url (str): The base URL for the GitHub API.
    """

    github_api_base_url: str = "https://api.github.com"

    def __init__(self, config_path: str, github_token: str):
        """
        Initializes the RepositoryManager.

        Args:
            config_path (str): The path to the dependency configuration file.
            github_token (str): The GitHub token for API authentication.
        """
        self.config_path = Path(config_path)
        self.github_token = github_token
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """
        Loads the repository management configuration from a JSON file.

        Returns:
            Dict: The loaded configuration.

        Raises:
            SystemExit: If the configuration file is not found, cannot be decoded, or
                        if an unexpected error occurs.
        """
        logging.info(f"Attempting to load configuration from {self.config_path}")
        try:
            with self.config_path.open("r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            logging.error(
                f"Error decoding JSON from configuration file: {self.config_path}. "
                "Please check its format."
            )
            sys.exit(1)
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while loading configuration: {e}"
            )
            sys.exit(1)

    def _get_headers(self) -> Dict[str, str]:
        """
        Constructs the headers for GitHub API requests.

        Returns:
            Dict[str, str]: The headers for API requests.
        """
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _fork_exists(self, fork_name: str) -> bool:
        """
        Checks if a forked repository already exists.

        Args:
            fork_name (str): The name of the fork to check (e.g., 'owner/repo').

        Returns:
            bool: True if the fork exists, False otherwise.
        """
        fork_url = f"{self.github_api_base_url}/repos/{fork_name}"
        try:
            response = requests.get(fork_url, headers=self._get_headers())
            if response.status_code == 200:
                logging.info(f"Fork {fork_name} already exists.")
                return True
            elif response.status_code == 404:
                logging.info(f"Fork {fork_name} does not exist.")
                return False
            else:
                logging.error(
                    f"Error checking fork {fork_name}. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
        except RequestException as e:
            logging.error(f"Network error while checking fork {fork_name}: {e}")
            return False

    def _create_fork(self, repo: str, fork_name: str) -> bool:
        """
        Creates a new fork of a repository.

        Args:
            repo (str): The original repository to fork (e.g., 'owner/repo').
            fork_name (str): The desired name for the new fork.

        Returns:
            bool: True if the fork was created successfully, False otherwise.
        """
        logging.info(f"Attempting to create fork {fork_name} from {repo}...")
        source_owner, source_repo = repo.split("/")[-2:]
        fork_api_url = (
            f"{self.github_api_base_url}/repos/{source_owner}/{source_repo}/forks"
        )
        owner, _ = fork_name.split("/")
        fork_payload = {"organization": owner} if owner != self.github_token else {}

        try:
            response = requests.post(
                fork_api_url, headers=self._get_headers(), json=fork_payload
            )
            if response.status_code in [201, 202]:
                logging.info(f"Successfully created fork {fork_name}")
                return True
            else:
                logging.error(
                    f"Failed to create fork for {repo}. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
        except RequestException as e:
            logging.error(f"Network error while creating fork for {repo}: {e}")
            return False

    def setup_fork(self, repo: str, fork_name: str) -> bool:
        """
        Ensures a fork of a repository exists, creating it if necessary.

        Args:
            repo (str): The original repository to fork.
            fork_name (str): The name of the fork to create.

        Returns:
            bool: True if the fork exists or was created successfully, False otherwise.
        """
        try:
            if self._fork_exists(fork_name):
                return True
            return self._create_fork(repo, fork_name)
        except Exception as e:
            logging.error(
                f"An unexpected error occurred during fork setup for {repo}: {e}"
            )
            return False

    def setup_branch_protection(
        self, repo_name: str, protection: BranchProtection
    ) -> bool:
        """
        Sets up branch protection rules for the main branch of a repository.

        Args:
            repo_name (str): The name of the repository (e.g., 'owner/repo').
            protection (BranchProtection): The branch protection rules to apply.

        Returns:
            bool: True if branch protection was set up successfully, False otherwise.
        """
        logging.info(f"Setting up branch protection for {repo_name}")
        protection_url = (
            f"{self.github_api_base_url}/repos/{repo_name}/branches/main/protection"
        )

        data = {
            "required_status_checks": None,
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": protection.dismiss_stale_reviews,
                "require_code_owner_reviews": False,
                "required_approving_review_count": protection.required_reviewers,
            },
            "restrictions": None,
        }

        try:
            response = requests.put(
                protection_url, headers=self._get_headers(), json=data
            )
            if response.status_code == 200:
                logging.info(f"Successfully set branch protection for {repo_name}")
                return True
            else:
                logging.error(
                    f"Failed to set branch protection for {repo_name}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
        except RequestException as e:
            logging.error(
                f"Network error while setting up branch protection for {repo_name}: {e}"
            )
            return False
        except Exception as e:
            logging.error(
                "An unexpected error occurred during branch protection setup for "
                f"{repo_name}: {e}"
            )
            return False

    def setup_all_tiers(self) -> bool:
        """
        Iterates through all configured tiers and sets up their repositories.

        This method processes each dependency in each tier, setting up forks and
        branch protection as defined in the configuration.

        Returns:
            bool: True if all tiers were set up successfully, False otherwise.
        """
        overall_success = True
        for tier_name, tier_data in self.config.get("tiers", {}).items():
            logging.info(f"--- Setting up {tier_name} ---")
            for dep_data in tier_data.get("dependencies", []):
                try:
                    bp_data = dep_data.pop("branch_protection", {})
                    protection = BranchProtection(**bp_data)
                    dep = Dependency(branch_protection=protection, **dep_data)

                    logging.info(f"Processing dependency: {dep.name}")

                    if not self.setup_fork(dep.repository, dep.fork):
                        logging.error(
                            f"Skipping {dep.name} due to fork setup failure."
                        )
                        overall_success = False
                        continue

                    # Placeholder for enabling branch protection setup
                    # if not self.setup_branch_protection(dep.fork, dep.branch_protection):
                    #     logging.error(f"Branch protection setup failed for {dep.name}")
                    #     overall_success = False

                except KeyError as e:
                    logging.error(
                        f"Missing key in dependency data for "
                        f"{dep_data.get('name', 'unknown')}: {e}"
                    )
                    overall_success = False
                except Exception as e:
                    logging.error(
                        f"An unexpected error occurred while processing dependency "
                        f"{dep_data.get('name', 'unknown')}: {e}"
                    )
                    overall_success = False

            logging.info(f"--- Finished {tier_name} ---")
        return overall_success


def main():
    """
    Main entry point for the automated repository management script.

    This function retrieves the necessary GitHub token, initializes the
    RepositoryManager, and starts the setup process for all tiers.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN environment variable not set.")
        sys.exit(1)

    # The configuration file is expected to be in the same directory as the script.
    config_path = Path(__file__).parent / "dependencies.json"

    manager = RepositoryManager(config_path=str(config_path), github_token=github_token)

    if not manager.setup_all_tiers():
        logging.error("Repository management script failed during execution.")
        sys.exit(1)

    logging.info("Repository management script completed successfully.")


if __name__ == "__main__":
    main()
