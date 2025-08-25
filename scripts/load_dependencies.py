#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

def load_dependencies(tier):
    """Load dependencies for the specified tier from dependencies.json"""
    deps_file = Path(__file__).parent.parent / 'dependency_management' / 'dependencies.json'
    
    with open(deps_file) as f:
        config = json.load(f)
    
    tier_key = f'tier{tier}'
    if tier_key not in config['tiers']:
        print(f"Error: Tier {tier} not found in configuration")
        sys.exit(1)
        
    return config['tiers'][tier_key]['dependencies']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tier', type=int, required=True, help='Dependency tier to load')
    args = parser.parse_args()
    
    deps = load_dependencies(args.tier)
    print(json.dumps(deps, indent=2))
