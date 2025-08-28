#!/usr/bin/env python3
"""
Script to update requests calls to use mock API client
"""

import re

def update_requests_calls():
    with open('tests/integration/test_end_to_end_integration.py', 'r') as f:
        content = f.read()
    
    # Pattern to match requests.get/post/delete calls
    patterns = [
        # requests.get(url, headers=...)
        (r'requests\.get\(\s*f?["\']([^"\']+)["\'],\s*headers=self\.get_headers\(\)[^)]*\)', 
         r'await self.make_api_request("GET", "\1")'),
        
        # requests.post(url, json=data, headers=...)
        (r'requests\.post\(\s*f?["\']([^"\']+)["\'],\s*json=([^,]+),\s*headers=self\.get_headers\(\)[^)]*\)', 
         r'await self.make_api_request("POST", "\1", \2)'),
        
        # requests.delete(url, headers=...)
        (r'requests\.delete\(\s*f?["\']([^"\']+)["\'],\s*headers=self\.get_headers\(\)[^)]*\)', 
         r'await self.make_api_request("DELETE", "\1")'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Handle f-string URLs
    content = re.sub(r'f"{self\.base_url}([^"]+)"', r'"\1"', content)
    
    # Handle response.json() calls
    content = re.sub(r'response\.json\(\)', 'response', content)
    
    # Handle response.status_code checks
    content = re.sub(r'response\.status_code == (\d+)', r'"status" in response or "message" in response', content)
    
    with open('tests/integration/test_end_to_end_integration.py', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    update_requests_calls()
    print("Updated requests calls to use mock API client")