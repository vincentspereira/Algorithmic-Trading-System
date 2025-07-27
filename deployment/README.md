# Production Deployment and Management

This document provides instructions for deploying, managing, and maintaining the production trading system.

## System Startup

To start the production system, run the appropriate deployment script:

**For Linux/macOS:**
```bash
./deployment/deploy_production.sh
```

**For Windows:**
```bat
.\deployment\deploy_production.bat
```

This will build and start all necessary Docker containers in detached mode.

## System Shutdown

To stop the production system, use the following Docker Compose command:

```bash
docker-compose -f docker-compose.prod.yml down
```

This will stop and remove all running containers associated with the production environment.

## Backup and Disaster Recovery

A script for testing backup and disaster recovery procedures is available in this directory. To run the test, execute the following command:

**For Linux/macOS:**
```bash
./deployment/test_backup_recovery.sh
```

**For Windows:**
```bat
.\deployment\test_backup_recovery.bat
```

This script will simulate a failure and recovery process to validate the backup and restore procedures.