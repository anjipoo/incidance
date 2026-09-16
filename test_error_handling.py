import requests

# End-to-end error handling checks for Step 12.
# Run this with the FastAPI server already running (uvicorn backend.main:app --reload).
# Place this file in your project root before running.

BASE_URL = "http://127.0.0.1:8000"


def check(description: str, condition: bool, extra: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {description}" + (f" — {extra}" if extra else ""))


def test_empty_log():
    response = requests.post(f"{BASE_URL}/incidents/analyze", json={"log": ""})
    check(
        "Empty log returns 400",
        response.status_code == 400,
        f"got {response.status_code}: {response.text}",
    )


def test_whitespace_only_log():
    response = requests.post(f"{BASE_URL}/incidents/analyze", json={"log": "   \n   "})
    check(
        "Whitespace-only log returns 400",
        response.status_code == 400,
        f"got {response.status_code}",
    )


def test_missing_field():
    # Sends a body without the required "log" field entirely.
    response = requests.post(f"{BASE_URL}/incidents/analyze", json={})
    check(
        "Missing 'log' field returns 422 (FastAPI/Pydantic validation)",
        response.status_code == 422,
        f"got {response.status_code}",
    )


def test_malformed_json():
    # Sends genuinely broken JSON, not just a wrong shape.
    response = requests.post(
        f"{BASE_URL}/incidents/analyze",
        data="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    check(
        "Malformed JSON body returns 4xx, not a 500",
        400 <= response.status_code < 500,
        f"got {response.status_code}",
    )


def test_invalid_incident_id():
    response = requests.get(f"{BASE_URL}/incidents/999999")
    check(
        "Nonexistent incident ID returns 404",
        response.status_code == 404,
        f"got {response.status_code}: {response.text}",
    )


def test_non_integer_incident_id():
    response = requests.get(f"{BASE_URL}/incidents/not-a-number")
    check(
        "Non-integer incident ID returns 422 (path type validation)",
        response.status_code == 422,
        f"got {response.status_code}",
    )


def test_health_check():
    response = requests.get(f"{BASE_URL}/health")
    check(
        "Health check returns 200 with expected body",
        response.status_code == 200 and response.json().get("status") == "healthy",
        f"got {response.status_code}: {response.text}",
    )


def test_valid_request_still_works():
    # Sanity check that error-path testing didn't leave anything broken.
    response = requests.post(
        f"{BASE_URL}/incidents/analyze",
        json={"log": "ERROR: Connection refused to PostgreSQL at 10.0.0.21:5432"},
    )
    check(
        "A normal valid request still succeeds",
        response.status_code == 200,
        f"got {response.status_code}",
    )


def run_all():
    print("Running end-to-end error handling tests against", BASE_URL)
    print("Make sure `uvicorn backend.main:app --reload` is running in another terminal.\n")

    test_health_check()
    test_empty_log()
    test_whitespace_only_log()
    test_missing_field()
    test_malformed_json()
    test_invalid_incident_id()
    test_non_integer_incident_id()
    test_valid_request_still_works()


if __name__ == "__main__":
    run_all()