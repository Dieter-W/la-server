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


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
    print(f"Testing endpoints at {base}\n")

    results = [
        test_endpoint(f"{base}/api/health", "GET /api/health"),
        test_endpoint(f"{base}/api/health/db", "GET /api/health/db"),
    ]

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
