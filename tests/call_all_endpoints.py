"""
Call all API endpoints and pretty-print the requests and responses.

Usage:
    python scripts/call_all_endpoints.py                          # default: http://localhost:8000
    python scripts/call_all_endpoints.py https://your-app.onrender.com
"""
import requests
import json
import sys

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

SEPARATOR = "=" * 70
SUB_SEPARATOR = "-" * 70


def pretty_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def call_endpoint(method, path, body=None, expect_json=True):
    url = f"{BASE_URL}{path}"

    print(f"\n{SEPARATOR}")
    print(f"  {method} {path}")
    print(SEPARATOR)

    if body:
        print(f"\n  Request body:")
        print(SUB_SEPARATOR)
        print(pretty_json(body))
        print(SUB_SEPARATOR)

    try:
        if method == "GET":
            r = requests.get(url, timeout=90)
        else:
            r = requests.post(url, json=body, timeout=120)

        print(f"\n  Status: {r.status_code}")
        print(f"  Content-Type: {r.headers.get('Content-Type', 'N/A')}")

        if not expect_json:
            size = len(r.content)
            print(f"  Binary response: {size:,} bytes")
            print(f"  (PNG image - not printed)")
        else:
            print(f"\n  Response:")
            print(SUB_SEPARATOR)
            try:
                data = r.json()
                print(pretty_json(data))
            except ValueError:
                print(r.text[:2000])
            print(SUB_SEPARATOR)

    except requests.ConnectionError:
        print(f"\n  ERROR: Could not connect to {url}")
        print(f"  Make sure the server is running.")
    except requests.Timeout:
        print(f"\n  ERROR: Request timed out.")
    except Exception as e:
        print(f"\n  ERROR: {e}")


def main():
    print(f"\n  Calling all endpoints on: {BASE_URL}\n")

    # 1. Health check
    call_endpoint("GET", "/health")

    # 2. Team info
    call_endpoint("GET", "/api/team_info")

    # 3. Agent info
    call_endpoint("GET", "/api/agent_info")

    # 4. Model architecture (PNG)
    call_endpoint("GET", "/api/model_architecture", expect_json=False)

    # 5. Model architecture (JSON metadata)
    call_endpoint("GET", "/api/model_architecture?format=json")

    # 6. Budget
    call_endpoint("GET", "/api/execute/budget")

    # 7. Students list
    call_endpoint("GET", "/api/students")

    # 8. Execute - simple query
    call_endpoint("POST", "/api/execute", body={
        "prompt": "What strategies work for ADHD students?"
    })

    # 9. Execute - student-specific query
    call_endpoint("POST", "/api/execute", body={
        "prompt": "What are Alex's triggers?",
        "student_name": "Alex"
    })

    # 10. Execute - error case (empty prompt)
    call_endpoint("POST", "/api/execute", body={
        "prompt": ""
    })

    print(f"\n{SEPARATOR}")
    print(f"  Done! All endpoints called.")
    print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    main()
