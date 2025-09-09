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

# Test graph invoke endpoint (if needed for testing)
print("Testing graph invoke endpoint...")
data = {"input": {"message": "고객 정보 검색해줘"}}
response = requests.post(f"{base_url}/api/graph/invoke", json=data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
else:
    print(f"Error: {response.text}\n")

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