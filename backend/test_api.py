"""
Quick API test script
"""
import requests
import json

base_url = "http://localhost:8000"

# Test health endpoint
print("Testing health endpoint...")
response = requests.get(f"{base_url}/health")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}\n")

# Test process endpoint
print("Testing process endpoint...")
data = {"message": "고객 정보 검색해줘"}
response = requests.post(f"{base_url}/api/v1/process", json=data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
else:
    print(f"Error: {response.text}\n")

# Test agents list
print("\nTesting agents list...")
response = requests.get(f"{base_url}/api/v1/agents")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Available agents: {json.dumps(response.json(), indent=2)}")
else:
    print(f"Error: {response.text}")

# Test mock DB
print("\nTesting mock database...")
response = requests.get(f"{base_url}/api/db/mock/customers")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    customers = response.json()
    print(f"Found {len(customers)} customers")
    if customers:
        print(f"First customer: {json.dumps(customers[0], indent=2, ensure_ascii=False)}")
else:
    print(f"Error: {response.text}")