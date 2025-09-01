
# Dependency Health Database Schema

This document outlines the proposed database schema for storing historical data about dependency health.

## Tables

### `dependencies`

This table stores the list of all monitored dependencies.

| Column | Type | Description |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | Unique identifier for the dependency. |
| `name` | `VARCHAR(255) NOT NULL` | Name of the dependency (e.g., 'react'). |
| `tier` | `VARCHAR(50) NOT NULL` | Criticality tier (e.g., 'Tier 1', 'Tier 2'). |
| `repository_url` | `VARCHAR(255)` | URL of the dependency's repository. |
| `created_at` | `TIMESTAMP` | Timestamp of when the dependency was added. |

### `dependency_health_checks`

This table stores the results of each health check for each dependency.

| Column | Type | Description |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | Unique identifier for the health check. |
| `dependency_id` | `INTEGER REFERENCES dependencies(id)` | Foreign key to the `dependencies` table. |
| `version` | `VARCHAR(50)` | The version of the dependency at the time of the check. |
| `security_status` | `VARCHAR(50)` | The security status (e.g., 'vulnerable', 'safe'). |
| `vulnerabilities` | `JSONB` | A JSON object containing details of any vulnerabilities found. |
| `checked_at` | `TIMESTAMP` | Timestamp of when the health check was performed. |

## Integration with Dashboard

This database schema can be integrated with the Dependency Health Dashboard to provide historical trend analysis. The dashboard can query the `dependency_health_checks` table to retrieve the health history of each dependency and visualize it as a time-series chart.

This will allow users to:

*   Track the security status of dependencies over time.
*   Identify dependencies that are frequently vulnerable.
*   Analyze the time it takes to remediate vulnerabilities.
