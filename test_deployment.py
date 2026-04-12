#!/usr/bin/env python3
"""Deployment test script for Baxter-Claw Bridge Server."""

import requests
import json
import sys

BASE_URL = "http://localhost:8420"

def test_health():
    """Test health endpoint."""
    print("Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_status():
    """Test status endpoint."""
    print("\nTesting /status...")
    response = requests.get(f"{BASE_URL}/status")
    print(f"  Status: {response.status_code}")
    data = response.json()
    print(f"  Connected: {data.get('connected')}")
    print(f"  Enabled: {data.get('enabled')}")
    return response.status_code == 200

def test_enable():
    """Test enable endpoint."""
    print("\nTesting /enable...")
    response = requests.post(f"{BASE_URL}/enable")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_home():
    """Test home primitive."""
    print("\nTesting /primitives/home...")
    response = requests.post(
        f"{BASE_URL}/primitives/home",
        json={"arm": "right"}
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_move_to():
    """Test move_to primitive."""
    print("\nTesting /primitives/move_to...")
    response = requests.post(
        f"{BASE_URL}/primitives/move_to",
        json={
            "arm": "right",
            "position": [0.7, -0.2, 0.3],
            "orientation": [0, 0, 0]
        }
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_pick():
    """Test pick primitive."""
    print("\nTesting /primitives/pick...")
    response = requests.post(
        f"{BASE_URL}/primitives/pick",
        json={
            "arm": "right",
            "position": [0.6, -0.3, 0.0]
        }
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def test_place():
    """Test place primitive."""
    print("\nTesting /primitives/place...")
    response = requests.post(
        f"{BASE_URL}/primitives/place",
        json={
            "arm": "right",
            "position": [0.5, -0.4, 0.0]
        }
    )
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    return response.status_code == 200

def main():
    """Run all tests."""
    print("=" * 60)
    print("Baxter-Claw Bridge Server Deployment Test")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("Status Check", test_status),
        ("Enable Robot", test_enable),
        ("Home Primitive", test_home),
        ("Move To Primitive", test_move_to),
        ("Pick Primitive", test_pick),
        ("Place Primitive", test_place),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Bridge Server is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())