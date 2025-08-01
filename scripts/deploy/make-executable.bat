@echo off
REM Make deployment scripts executable on Windows

echo Making deployment scripts executable...

REM For Windows, we need to ensure scripts have proper permissions
REM and can be executed by the system

echo Setting execution policy for PowerShell scripts...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"

echo Deployment scripts are now ready for execution.
echo.
echo Available deployment scripts:
echo - blue-green-deployment.sh
echo - canary-deployment.sh  
echo - rollback-deployment.sh
echo - disaster-recovery.sh
echo - health-check.sh
echo.
echo To run these scripts on Windows, use:
echo   bash script-name.sh [options]
echo or
echo   wsl script-name.sh [options]
echo.
pause