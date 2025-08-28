# Dependency Management System Documentation

## Overview

The Dependency Management System is a critical component of the Algorithmic Trading System, designed to proactively manage, monitor, and integrate over 60 external open-source repositories and best-of-breed components. Its primary goal is to ensure system stability, security, and compliance by automating dependency lifecycle management, from initial forking to continuous updates and integration testing.

## Architectural Principles

*   **Tiered Organization:** Dependencies are categorized into four tiers based on criticality, allowing for differentiated monitoring and update strategies.
*   **Automation-First:** Workflows are heavily automated using GitHub Actions, Renovate, and custom Python scripts to minimize manual overhead.
*   **Security-Conscious:** Integrates security scanning and branch protection rules to maintain a secure supply chain.
*   **Observable:** Designed to provide clear visibility into the health and status of all dependencies.

## Key Components and Workflows

### 1. Dependency Inventory (`dependencies.json`)

*   **Location:** `dependency_management/dependencies.json`
*   **Purpose:** This JSON file serves as the single source of truth for all external dependencies. It lists each dependency with its name, repository URL, fork URL, current version, customization notes, and branch protection requirements. Dependencies are organized into `tier1`, `tier2`, `tier3`, and `tier4` based on their criticality.

### 2. Repository Management (`repository_manager.py`)

*   **Location:** `dependency_management/repository_manager.py`
*   **Purpose:** A Python script responsible for interacting with the GitHub API to:
    *   Fork external repositories into the organization's private GitHub account.
    *   Apply predefined branch protection rules to the forked repositories.
*   **Automation:** This script is automatically triggered by the `Repository Manager` GitHub Actions workflow (`.github/workflows/repository-manager.yml`) whenever `dependencies.json` is updated. This ensures that new dependencies are automatically forked and configured.

### 3. Automated Dependency Monitoring (Renovate)

*   **Workflow:** `.github/workflows/dependency-monitoring.yml`
*   **Configuration:** `renovate.json` (located in the project root)
*   **Purpose:** Utilizes Renovate, an automated dependency update tool, to continuously monitor all declared dependencies for new versions. It automatically creates pull requests (PRs) for available updates.
*   **Tiered Scheduling:** The `renovate.json` configuration defines specific schedules and automerge behaviors for each dependency tier, aligning with their criticality (e.g., more frequent checks for Tier 1, monthly for Tier 4).

### 4. Update Integration Pipeline

*   **Workflow:** `.github/workflows/update-integration.yml`
*   **Purpose:** This CI/CD pipeline is triggered on every pull request (including those created by Renovate) to validate dependency updates in an isolated environment.
*   **Process:**
    1.  Checks out the code from the PR.
    2.  Builds all necessary Docker containers defined in `docker-compose.local.yml`.
    3.  Runs a comprehensive test suite within a dedicated `test` Docker service (defined in `docker-compose.local.yml` and built from `Dockerfile.test`).
    4.  Notifies on test failures, preventing breaking changes from being merged.

### 5. Dependency Health Dashboard (Placeholder)

*   **Location:** `dependency_management/dashboard/`
*   **Purpose:** A future web-based interface designed to provide a real-time, centralized view of all dependency statuses, including versions, vulnerabilities, and integration test results.
*   **Current Status:** Currently a placeholder with a basic directory structure, a `README.md` outlining its future development, a static `index.html` frontend, and a placeholder FastAPI API endpoint (`dependency_management/api/dependency_api.py`).
*   **Future Data Sources:** Will integrate data from `dependencies.json`, GitHub API, Renovate output, Prometheus, CVE databases, and CI/CD test results.

## Key Files and Their Roles

*   `dependency_management/dependencies.json`: Central inventory of all dependencies.
*   `dependency_management/repository_manager.py`: Script for forking and branch protection.
*   `renovate.json`: Renovate configuration for automated updates.
*   `.github/workflows/dependency-monitoring.yml`: GitHub Actions workflow for running Renovate.
*   `.github/workflows/repository-manager.yml`: GitHub Actions workflow for automating repository setup.
*   `.github/workflows/update-integration.yml`: GitHub Actions workflow for validating dependency updates.
*   `docker-compose.local.yml`: Defines local development and testing environment, including the `test` service.
*   `Dockerfile.test`: Dockerfile for building the test environment.
*   `tests/unit/test_repository_manager.py`: Unit tests for `repository_manager.py`.
*   `dependency_management/dashboard/`: Directory for the Dependency Health Dashboard.
*   `dependency_management/api/dependency_api.py`: Placeholder for the dashboard's backend API.
