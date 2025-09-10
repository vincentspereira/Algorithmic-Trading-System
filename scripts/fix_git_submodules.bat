@echo off
REM Script to fix Git submodule commit issues
REM This script helps manage the submodules and fix commit problems

echo 🔧 Fixing Git Submodule Commit Issues
echo ===================================

REM Initialize and update submodules
echo 🔄 Initializing and updating submodules...
git submodule init
git submodule update

REM Check status of each submodule
echo 🔍 Checking submodule status...
git submodule status

echo 📝 Processing submodules with changes...

REM List of submodules with changes (from git status)
set SUBMODULES=forks/nautilus-trader forks/tier1/grpc forks/tier1/kafka forks/tier1/schema-registry forks/tier2/openbb forks/tier2/transformers forks/tier3/next.js_temp forks/tier3/react forks/tier3/react_temp forks/tier4/elasticsearch forks/tier4/grafana forks/tier4/grafana_temp forks/tier4/influxdb forks/tier4/kubernetes_temp forks/tier4/loki forks/tier4/quickfixj forks/tier4/tempo forks/tier4/unleash

for %%s in (%SUBMODULES%) do (
    echo Processing %%s...
    
    REM Check if submodule directory exists
    if exist "%%s" (
        REM Go to submodule directory
        cd "%%s"
        
        REM Check if there are actually changes
        git diff-index --quiet HEAD -- >nul 2>&1
        if errorlevel 1 (
            echo   Found changes in %%s
            
            REM Show what files have changed
            echo   Changed files:
            git status --porcelain
            
            echo   For now, we'll reset the submodule to match the parent repository
            echo   If you made intentional changes, you'll need to handle them manually
            git reset --hard
        ) else (
            echo   No changes in %%s
        )
        
        REM Go back to parent directory
        cd ..\..
    ) else (
        echo   Submodule directory %%s does not exist
    )
)

echo ✅ Submodule processing complete

REM Now update the parent repository to reflect submodule changes
echo 🔄 Updating parent repository submodule references...
git add .
git commit -m "Update submodule references"

echo ✅ All submodule issues should now be resolved
echo 💡 You can now push your changes with: git push origin main

pause