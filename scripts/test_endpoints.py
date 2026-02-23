"""Test API endpoints. Run with: python scripts/test_endpoints.py [base_url]"""

import json
import sys
import urllib.error
import urllib.request


def test_endpoint(url: str, name: str) -> bool:
    """GET an endpoint and print pass/fail. Returns True if status 200 and status==ok."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            ok = data.get("status") == "ok"
            print(f"  {name}: {'PASS' if ok else 'FAIL'} - {data}")
            return ok
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  {name}: FAIL - HTTP {e.code} - {body[:200]}")
        return False
    except Exception as e:
        print(f"  {name}: FAIL - {e}")
        return False


def _request(method: str, url: str, data: dict | None = None) -> tuple[int, dict]:
    """Send request and return (status_code, parsed_json)."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


def _request_expect_error(method: str, url: str, data: dict | None = None) -> tuple[int, dict]:
    """Send request expecting an error. Returns (status_code, parsed_json)."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_bytes = e.read() if e.fp else b"{}"
        return e.code, json.loads(body_bytes.decode()) if body_bytes else {}


def test_employee_endpoints(base: str) -> list[bool]:
    """Test employee CRUD. Returns list of pass/fail results."""
    results = []
    emp_id = None

    # GET /api/employees (list)
    try:
        status, data = _request("GET", f"{base}/api/employees")
        ok = status == 200 and "employees" in data and isinstance(data["employees"], list)
        results.append(ok)
        print(f"  GET /api/employees: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  GET /api/employees: FAIL - {e}")

    # POST /api/employees (create)
    try:
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "employee_number": "TEST-001",
            "role": "Tester",
            "active": True,
            "notes": "Created by test script",
        }
        status, data = _request("POST", f"{base}/api/employees", payload)
        ok = status == 201 and data.get("employee_number") == "TEST-001" and data.get("id")
        if ok:
            emp_id = data["id"]
        results.append(ok)
        print(f"  POST /api/employees: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  POST /api/employees: FAIL - {e}")

    if not emp_id:
        return results

    # GET /api/employees/<id>
    try:
        status, data = _request("GET", f"{base}/api/employees/{emp_id}")
        ok = status == 200 and data.get("id") == emp_id and data.get("first_name") == "Test"
        results.append(ok)
        print(f"  GET /api/employees/<id>: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  GET /api/employees/<id>: FAIL - {e}")

    # PUT /api/employees/<id>
    try:
        payload = {"first_name": "Updated", "notes": "Modified by test"}
        status, data = _request("PUT", f"{base}/api/employees/{emp_id}", payload)
        ok = status == 200 and data.get("first_name") == "Updated" and data.get("notes") == "Modified by test"
        results.append(ok)
        print(f"  PUT /api/employees/<id>: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  PUT /api/employees/<id>: FAIL - {e}")

    # GET /api/employees?active=true (filter)
    try:
        status, data = _request("GET", f"{base}/api/employees?active=true")
        ok = status == 200 and "employees" in data
        results.append(ok)
        print(f"  GET /api/employees?active=true: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  GET /api/employees?active=true: FAIL - {e}")

    # DELETE /api/employees/<id> (soft delete)
    try:
        status, data = _request("DELETE", f"{base}/api/employees/{emp_id}")
        ok = status == 200 and data.get("active") is False
        results.append(ok)
        print(f"  DELETE /api/employees/<id> (soft): {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  DELETE /api/employees/<id> (soft): FAIL - {e}")

    # DELETE /api/employees/<id>?hard=true (hard delete, cleanup)
    try:
        status, data = _request("DELETE", f"{base}/api/employees/{emp_id}?hard=true")
        ok = status == 200 and data.get("message") == "Employee deleted permanently"
        results.append(ok)
        print(f"  DELETE /api/employees/<id>?hard=true: {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  DELETE /api/employees/<id>?hard=true: FAIL - {e}")

    # GET /api/employees/<id> (404 after delete)
    try:
        status, data = _request_expect_error("GET", f"{base}/api/employees/{emp_id}")
        ok = status == 404 and data.get("error") == "Employee not found"
        results.append(ok)
        print(f"  GET /api/employees/<id> (404): {'PASS' if ok else 'FAIL'} - {status}")
    except Exception as e:
        results.append(False)
        print(f"  GET /api/employees/<id> (404): FAIL - {e}")

    return results


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
    print(f"Testing endpoints at {base}\n")

    results = [
        test_endpoint(f"{base}/api/health", "GET /api/health"),
        test_endpoint(f"{base}/api/health/db", "GET /api/health/db"),
    ]

    print("\nEmployee endpoints:")
    results.extend(test_employee_endpoints(base))

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
