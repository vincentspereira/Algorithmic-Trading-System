@echo off
REM Script to fix Git submodule commit issues
REM This script helps manage the submodules and fix commit problems

echo 🔧 Fixing Git Submodule Commit Issues
echo ===================================

REM Check if we're in the right directory
if not exist ".git" (
    echo ❌ Error: This script must be run from the root of the Git repository
    echo Please navigate to the main project directory and try again.
    pause
    exit /b 1
)

echo 📂 Current directory: %CD%

REM Initialize and update submodules (if any)
echo 🔄 Initializing and updating submodules...
git submodule init 2>nul
git submodule update 2>nul

REM Check status of each submodule
echo 🔍 Checking submodule status...
git submodule status 2>nul

echo 📝 Processing submodules with changes...

REM List of submodules with changes (from git status)
set SUBMODULES=forks/nautilus-trader forks/tier1/grpc forks/tier1/kafka forks/tier1/schema-registry forks/tier2/openbb forks/tier2/transformers forks/tier3/next.js_temp forks/tier3/react forks/tier3/react_temp forks/tier4/elasticsearch forks/tier4/grafana forks/tier4/grafana_temp forks/tier4/influxdb forks/tier4/kubernetes_temp forks/tier4/loki forks/tier4/quickfixj forks/tier4/tempo forks/tier4/unleash

echo ⚠️  WARNING: This script will remove the .git directories from the following submodules:
for %%s in (%SUBMODULES%) do (
    echo   - %%s
)
echo.
echo This will convert them from nested Git repositories to regular directories.
echo Any uncommitted changes in these repositories will be lost.
echo.

set /p CONFIRM="Do you want to proceed? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo Operation cancelled.
    pause
    exit /b 1
)

for %%s in (%SUBMODULES%) do (
    echo Processing %%s...
    
    REM Check if submodule directory exists
    if exist "%%s" (
        REM Check if it has a .git directory
        if exist "%%s\.git" (
            echo   Removing .git directory from %%s...
            rmdir /s /q "%%s\.git"
            if errorlevel 1 (
                echo   ❌ Failed to remove .git directory from %%s
            ) else (
                echo   ✅ Successfully removed .git directory from %%s
            )
        ) else (
            echo   No .git directory found in %%s
        )
    ) else (
        echo   Directory %%s does not exist
    )
)

echo ✅ Submodule processing complete

REM Now add all the directories to Git tracking
echo 🔄 Adding directories to Git tracking...
git add forks/

REM Commit the changes
echo 📦 Committing changes...
git commit -m "Convert nested Git repositories to regular directories"

echo ✅ All submodule issues should now be resolved
echo 💡 You can now push your changes with: git push origin main

pause