@echo off
REM Batch script to organize missing repositories

echo Organizing missing repositories...

cd /d "c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Trae\Algorithmic Trading System"

python scripts\organize_missing_repositories.py

echo Repository organization complete.

pause