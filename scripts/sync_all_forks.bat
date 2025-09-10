@echo off
REM Automated synchronization script for all forked repositories

echo Starting automated synchronization of all forked repositories...

cd /d "c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"

python scripts\sync_forks_with_upstream.py

echo Synchronization complete.

pause
