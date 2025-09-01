
import json
import os
import subprocess
import sys

def check_fork_drift(config_file):
    """
    Checks for drift between forked repositories and their upstream counterparts.
    """
    with open(config_file, 'r') as f:
        config = json.load(f)

    for repo in config['repositories']:
        name = repo['name']
        path = repo['path']
        upstream_url = repo['upstream_url']

        print(f"Checking {name}...")

        if not os.path.isdir(path):
            print(f"  Error: Directory not found at {path}")
            continue

        # Add upstream remote if it doesn't exist
        remotes = subprocess.check_output(["git", "-C", path, "remote"]).decode()
        if "upstream" not in remotes:
            subprocess.run(["git", "-C", path, "remote", "add", "upstream", upstream_url])

        # Fetch latest changes from upstream
        subprocess.run(["git", "-C", path, "fetch", "upstream"])

        # Compare main branches
        try:
            diff = subprocess.check_output(["git", "-C", path, "diff", "main", "upstream/main"])
            if diff:
                print(f"  Drift detected in {name}:")
                print(diff.decode())
            else:
                print(f"  {name} is up to date with upstream.")
        except subprocess.CalledProcessError:
            print(f"  Error comparing branches for {name}. Does the upstream have a 'main' branch?")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_fork_drift.py <config_file>")
        sys.exit(1)

    check_fork_drift(sys.argv[1])
