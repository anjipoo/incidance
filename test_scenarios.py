import requests
import json

BASE_URL = "http://127.0.0.1:8000"

DEMO_LOGS = {
    "database": (
        "ERROR: Connection refused to PostgreSQL at 10.0.0.21:5432\n"
        "Retry attempt 3/3 failed\n"
        "Application shutting down"
    ),
    "api": (
        "ERROR: Payment service returned HTTP 503\n"
        "Request timed out after 30 seconds"
    ),
    "dns": (
        "ERROR: Temporary failure in name resolution\n"
        "Unable to resolve api.payment-service.local"
    ),
    "filesystem": (
        "ERROR: Failed to write transaction.log\n"
        "No space left on device"
    ),
    "authentication": (
        "ERROR: Authentication failed\n"
        "Access token expired\n"
        "Request rejected with HTTP 401"
    ),
}


def run_demo():
    for expected_category, log in DEMO_LOGS.items():
        response = requests.post(f"{BASE_URL}/incidents/analyze", json={"log": log})

        if response.status_code != 200:
            print(f"[FAIL] {expected_category}: HTTP {response.status_code} - {response.text}")
            continue

        result = response.json()
        actual_category = result["category"]
        match = "OK" if actual_category == expected_category else "MISMATCH"

        print(f"[{match}] expected={expected_category} actual={actual_category} "
              f"severity={result['severity']} confidence={result['confidence']}")
        print(f"  root_cause: {result['root_cause']}")
        print(f"  top_similar: {result['similar_incidents'][0]['log']} "
              f"(similarity={result['similar_incidents'][0]['similarity']:.2f})")
        print()


if __name__ == "__main__":
    run_demo()