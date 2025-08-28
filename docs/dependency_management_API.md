# API Documentation

## Overview
The Dependency Management System exposes several REST APIs for managing dependencies, notifications, and security scanning. This document details the available endpoints, request/response formats, and authentication requirements.

## Base URLs
- API Service: `http://localhost:8000`
- Notification Service: `http://localhost:8001`
- Security Service: `http://localhost:8002`

## Authentication
All APIs require an API key passed in the header:
```
Authorization: Bearer <api_key>
```

## API Service Endpoints

### Dependency Health
GET `/api/dependencies/health`

Returns health status for all dependencies.

#### Response
```json
{
  "dependencies": [
    {
      "name": "string",
      "version": "string",
      "tier": integer,
      "last_updated": "string (ISO 8601)",
      "status": "string (healthy|warning|critical)",
      "vulnerabilities": [
        {
          "cve_id": "string",
          "severity": "string",
          "description": "string"
        }
      ],
      "updates_available": boolean,
      "performance_metrics": {
        "uptime": number,
        "response_time": number,
        "error_rate": number
      }
    }
  ]
}
```

### Dependency Details
GET `/api/dependencies/{name}/details`

Returns detailed information about a specific dependency.

#### Parameters
- `name` (path) - Dependency name

#### Response
```json
{
  "name": "string",
  "version": "string",
  "tier": integer,
  "repository": "string",
  "customizations": [
    {
      "name": "string",
      "description": "string",
      "files": ["string"]
    }
  ],
  "health_metrics": {
    "uptime": number,
    "response_time": number,
    "error_rate": number
  },
  "recent_updates": [
    {
      "version": "string",
      "date": "string (ISO 8601)",
      "type": "string",
      "status": "string"
    }
  ]
}
```

### Approve Update
POST `/api/dependencies/{name}/approve-update`

Approves a pending update for a dependency.

#### Parameters
- `name` (path) - Dependency name

#### Request Body
```json
{
  "version": "string",
  "comment": "string"
}
```

#### Response
```json
{
  "status": "string",
  "message": "string"
}
```

## Notification Service Endpoints

### Send Notification
POST `/notify`

Sends a notification through configured channels.

#### Request Body
```json
{
  "title": "string",
  "message": "string",
  "priority": "string (critical|high|medium|low)",
  "tier": integer,
  "details": {
    "key": "value"
  },
  "recipients": ["string"]
}
```

#### Response
```json
{
  "status": "string",
  "channels": ["string"],
  "timestamp": "string (ISO 8601)"
}
```

### Notification Status
GET `/notification-status`

Returns status of recent notifications.

#### Response
```json
{
  "notifications": [
    {
      "id": "string",
      "title": "string",
      "status": "string",
      "timestamp": "string (ISO 8601)",
      "channels": ["string"]
    }
  ]
}
```

## Security Service Endpoints

### Security Scan
POST `/scan`

Triggers a security scan for specified dependencies.

#### Request Body
```json
{
  "dependencies": [
    {
      "name": "string",
      "version": "string",
      "repo_path": "string"
    }
  ]
}
```

#### Response
```json
{
  "scan_id": "string",
  "timestamp": "string (ISO 8601)",
  "status": "string"
}
```

### Vulnerability Report
GET `/vulnerabilities`

Returns vulnerability report for all dependencies.

#### Response
```json
{
  "dependencies": [
    {
      "name": "string",
      "version": "string",
      "vulnerabilities": [
        {
          "cve_id": "string",
          "description": "string",
          "severity": "string",
          "cvss_score": number,
          "affected_versions": ["string"],
          "fix_versions": ["string"],
          "references": ["string"]
        }
      ],
      "sast_findings": [
        {
          "severity": "string",
          "confidence": "string",
          "description": "string",
          "file": "string",
          "line": integer
        }
      ],
      "risk_score": number
    }
  ]
}
```

## Error Responses
All APIs use standard HTTP status codes and return errors in the following format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

Common error codes:
- 400 - Bad Request
- 401 - Unauthorized
- 403 - Forbidden
- 404 - Not Found
- 429 - Too Many Requests
- 500 - Internal Server Error

## Rate Limiting
All APIs implement rate limiting:
- Tier 1/2 endpoints: 100 requests/minute
- Tier 3/4 endpoints: 60 requests/minute
- Security scan endpoint: 10 requests/minute

## Webhooks
The system can send webhooks for various events:

### Configuration
```json
{
  "url": "string",
  "events": ["dependency.update", "security.vulnerability"],
  "secret": "string"
}
```

### Event Types
- `dependency.update` - New update available
- `dependency.approved` - Update approved
- `security.vulnerability` - New vulnerability found
- `security.scan.complete` - Security scan completed

### Webhook Payload
```json
{
  "event": "string",
  "timestamp": "string (ISO 8601)",
  "data": {}
}
```
