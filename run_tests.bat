@echo off
echo Starting test execution...
set PYTHONPATH=.
echo PYTHONPATH set to current directory.
.\.venv\Scripts\activate
echo Virtual environment activated.
echo Calling pytest...
pytest --cov --verbose tests/ > test_output.txt 2>&1
echo Pytest execution finished.
echo See test_output.txt for results.
cmd /k
