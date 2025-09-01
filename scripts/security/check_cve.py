
import requests
import sys

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/1.0"

def check_cve(dependency_file):
    """
    Checks for vulnerabilities in a list of dependencies.
    """
    with open(dependency_file, 'r') as f:
        dependencies = f.readlines()

    for dependency in dependencies:
        dependency = dependency.strip()
        if not dependency or dependency.startswith('#'):
            continue

        try:
            name, version = dependency.split('==')
        except ValueError:
            print(f"Skipping invalid dependency format: {dependency}")
            continue

        print(f"Checking {name}=={version}...")
        response = requests.get(NVD_API_URL, params={"cpeMatchString": f"cpe:/a:*:*{name}:{version}"})

        if response.status_code == 200:
            data = response.json()
            if data['result']['CVE_Items']:
                print(f"  Vulnerabilities found for {name}=={version}:")
                for item in data['result']['CVE_Items']:
                    cve_id = item['cve']['CVE_data_meta']['ID']
                    description = item['cve']['description']['description_data'][0]['value']
                    print(f"    - {cve_id}: {description}")
            else:
                print(f"  No vulnerabilities found for {name}=={version}")
        else:
            print(f"  Error checking {name}=={version}: {response.status_code}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_cve.py <dependency_file>")
        sys.exit(1)

    check_cve(sys.argv[1])
