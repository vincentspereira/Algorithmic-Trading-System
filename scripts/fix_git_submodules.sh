#!/bin/bash

# Script to fix Git submodule commit issues
# This script helps manage the submodules and fix commit problems

echo "🔧 Fixing Git Submodule Commit Issues"
echo "==================================="

# Initialize and update submodules
echo "🔄 Initializing and updating submodules..."
git submodule init
git submodule update

# Check status of each submodule
echo "🔍 Checking submodule status..."
git submodule status

# For each modified submodule, we need to either:
# 1. Commit the changes in the submodule
# 2. Reset the submodule to match the parent repository

echo "📝 Processing submodules with changes..."

# List of submodules with changes (from git status)
SUBMODULES=("forks/nautilus-trader" 
            "forks/tier1/grpc" 
            "forks/tier1/kafka" 
            "forks/tier1/schema-registry" 
            "forks/tier2/openbb" 
            "forks/tier2/transformers" 
            "forks/tier3/next.js_temp" 
            "forks/tier3/react" 
            "forks/tier3/react_temp" 
            "forks/tier4/elasticsearch" 
            "forks/tier4/grafana" 
            "forks/tier4/grafana_temp" 
            "forks/tier4/influxdb" 
            "forks/tier4/kubernetes_temp" 
            "forks/tier4/loki" 
            "forks/tier4/quickfixj" 
            "forks/tier4/tempo" 
            "forks/tier4/unleash")

for submodule in "${SUBMODULES[@]}"; do
    echo "Processing $submodule..."
    
    # Check if submodule directory exists
    if [ -d "$submodule" ]; then
        # Go to submodule directory
        cd "$submodule"
        
        # Check if there are actually changes
        if ! git diff-index --quiet HEAD --; then
            echo "  Found changes in $submodule"
            
            # Show what files have changed
            echo "  Changed files:"
            git status --porcelain
            
            # Ask user what to do
            echo "  What would you like to do?"
            echo "  1. Commit changes in submodule (if you made intentional changes)"
            echo "  2. Reset submodule to match parent repository (recommended if changes are accidental)"
            echo "  3. Skip this submodule"
            
            read -p "  Enter your choice (1/2/3): " choice
            
            case $choice in
                1)
                    echo "  Committing changes in $submodule"
                    git add .
                    read -p "  Enter commit message for submodule: " commit_msg
                    git commit -m "$commit_msg"
                    ;;
                2)
                    echo "  Resetting $submodule to match parent repository"
                    git reset --hard
                    ;;
                3)
                    echo "  Skipping $submodule"
                    ;;
                *)
                    echo "  Invalid choice, resetting to match parent repository"
                    git reset --hard
                    ;;
            esac
        else
            echo "  No changes in $submodule"
        fi
        
        # Go back to parent directory
        cd ../..
    else
        echo "  Submodule directory $submodule does not exist"
    fi
done

echo "✅ Submodule processing complete"

# Now update the parent repository to reflect submodule changes
echo "🔄 Updating parent repository submodule references..."
git add .
git commit -m "Update submodule references"

echo "✅ All submodule issues should now be resolved"
echo "💡 You can now push your changes with: git push origin main"