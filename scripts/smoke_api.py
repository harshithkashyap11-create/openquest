import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


base_url = os.environ.get("CLASS_PULSE_API_URL", "http://127.0.0.1:8000").rstrip("/")


def get_json(path: str):
    request = Request(f"{base_url}{path}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def check(path: str, summary):
    status, payload = get_json(path)
    print(f"GET {path}: {status} — {summary(payload)}")
    return payload


def count(payload):
    return f"{len(payload)} records"


try:
    check("/health", lambda payload: payload.get("status", "healthy"))
    classes = check("/api/demo/classes", count)
    if not classes:
        print("No demo classes are loaded; import the synthetic dataset to continue.")
        sys.exit(0)

    class_id = classes[0]["id"]
    checks = [
        (f"/api/demo/classes/{class_id}/students", count),
        (f"/api/classes/{class_id}/assessment-summary", lambda data: f"{data['submitted_students']} students submitted"),
        (f"/api/classes/{class_id}/diagnoses/summary", lambda data: f"{data['total_diagnoses']} diagnoses"),
        (f"/api/classes/{class_id}/groups", count),
        (f"/api/classes/{class_id}/progress", lambda data: f"{data['completed_reassessments']} completed reassessments"),
        (f"/api/classes/{class_id}/intervention-assignments", count),
    ]
    for path, summarize in checks:
        check(path, summarize)
except (HTTPError, URLError, TimeoutError, KeyError, ValueError) as error:
    print(f"API smoke check failed: {error}", file=sys.stderr)
    sys.exit(1)
