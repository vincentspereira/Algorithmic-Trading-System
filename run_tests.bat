@echo off
echo Starting test execution...
set PYTHONPATH=%CD%;%CD%\\forks\\nautilus_trader;%CD%\\nautilus_trader_engine;%PYTHONPATH%
echo PYTHONPATH set to include project root, nautilus-trader fork, and engine.
call .\.venv\Scripts\activate.bat
echo Virtual environment activated.
echo Calling pytest...
pytest tests/unit/test_unit_portfolio_management.py --cov=. --cov-report=html --cov-report=term-missing -v
echo Pytest execution finished.
echo See test_output.txt for results.
cmd /k
