"""
Live API test against the deployed Render service.
Tests all course-required endpoints.
"""
import requests
import json
import sys

BASE = "https://co-teacher-wuza.onrender.com"
PASS = []
FAIL = []

def check(label, condition, detail=""):
    if condition:
        PASS.append(label)
        print(f"  ✅ {label}")
    else:
        FAIL.append(label)
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))

def test_endpoint(name, method, path, body=None):
    url = BASE + path
    print(f"\n{'='*60}")
    print(f"  {method} {path}")
    print(f"{'='*60}")
    try:
        if method == "GET":
            r = requests.get(url, timeout=90)
        else:
            r = requests.post(url, json=body, timeout=120)
        print(f"  HTTP {r.status_code}")
        return r
    except Exception as e:
        print(f"  ERROR: {e}")
        FAIL.append(name)
        return None


# ── 1. Health ─────────────────────────────────────────────────────────────────
r = test_endpoint("health", "GET", "/health")
if r:
    check("health: status 200", r.status_code == 200, r.status_code)
    try:
        data = r.json()
        check("health: status=healthy", data.get("status") == "healthy", data)
    except Exception as e:
        check("health: valid JSON", False, str(e))


# ── 2. GET /api/team_info ──────────────────────────────────────────────────────
r = test_endpoint("team_info", "GET", "/api/team_info")
if r:
    check("team_info: status 200", r.status_code == 200)
    try:
        data = r.json()
        print("  Response:", json.dumps(data, indent=4))
        check("team_info: has group_batch_order_number", "group_batch_order_number" in data, data.keys())
        check("team_info: has team_name", "team_name" in data, data.keys())
        check("team_info: has students list", isinstance(data.get("students"), list), data.get("students"))
        students = data.get("students", [])
        check("team_info: 3 students", len(students) == 3, len(students))
        if students:
            check("team_info: student has name+email", all("name" in s and "email" in s for s in students))
    except Exception as e:
        check("team_info: valid JSON", False, str(e))


# ── 3. GET /api/agent_info ─────────────────────────────────────────────────────
r = test_endpoint("agent_info", "GET", "/api/agent_info")
if r:
    check("agent_info: status 200", r.status_code == 200)
    try:
        data = r.json()
        check("agent_info: has description", bool(data.get("description")))
        check("agent_info: has purpose", bool(data.get("purpose")))
        check("agent_info: has prompt_template", bool(data.get("prompt_template")))
        template = data.get("prompt_template", {})
        check("agent_info: prompt_template has template key", "template" in template, template.keys())
        examples = data.get("prompt_examples", [])
        check("agent_info: has prompt_examples", len(examples) >= 1, len(examples))
        if examples:
            ex = examples[0]
            check("agent_info: example has prompt", "prompt" in ex)
            check("agent_info: example has full_response", "full_response" in ex)
            check("agent_info: example has steps", isinstance(ex.get("steps"), list))
            if ex.get("steps"):
                step = ex["steps"][0]
                check("agent_info: step has module", "module" in step)
                check("agent_info: step has prompt", "prompt" in step)
                check("agent_info: step has response", "response" in step)
    except Exception as e:
        check("agent_info: valid JSON", False, str(e))


# ── 4. GET /api/model_architecture (PNG) ──────────────────────────────────────
r = test_endpoint("model_architecture image", "GET", "/api/model_architecture")
if r:
    check("model_architecture: status 200", r.status_code == 200)
    ct = r.headers.get("content-type", "")
    check("model_architecture: content-type is image/png", "image/png" in ct, ct)
    check("model_architecture: PNG size > 10KB", len(r.content) > 10000, f"{len(r.content)} bytes")
    print(f"  PNG size: {len(r.content):,} bytes")


# ── 5. GET /api/model_architecture?format=json ────────────────────────────────
r = test_endpoint("model_architecture json", "GET", "/api/model_architecture?format=json")
if r:
    check("model_architecture json: status 200", r.status_code == 200)
    try:
        data = r.json()
        check("model_architecture json: has description", bool(data.get("description")))
        check("model_architecture json: has modules", bool(data.get("modules")))
        check("model_architecture json: has data_flow list", isinstance(data.get("data_flow"), list))
    except Exception as e:
        check("model_architecture json: valid JSON", False, str(e))


# ── 6. POST /api/execute — normal query ───────────────────────────────────────
r = test_endpoint("execute normal", "POST", "/api/execute",
                  body={"prompt": "What strategies work for students with ADHD?"})
if r:
    check("execute: status 200", r.status_code == 200)
    try:
        data = r.json()
        print("  Response keys:", list(data.keys()))
        check("execute: has status field", "status" in data)
        check("execute: status == ok", data.get("status") == "ok", data.get("status"))
        check("execute: error is null", data.get("error") is None, data.get("error"))
        check("execute: has response text", bool(data.get("response")))
        check("execute: has steps list", isinstance(data.get("steps"), list))
        steps = data.get("steps", [])
        check("execute: at least 1 step", len(steps) >= 1, len(steps))
        print(f"  Steps count: {len(steps)}")
        if steps:
            step = steps[0]
            check("execute: step has module", "module" in step, step.keys())
            check("execute: step has prompt", "prompt" in step, step.keys())
            check("execute: step has response", "response" in step, step.keys())
            print(f"  First step module: {step.get('module')}")
        print(f"  Response preview: {str(data.get('response',''))[:200]}")
    except Exception as e:
        check("execute: valid JSON", False, str(e))


# ── 7. POST /api/execute — error case (empty prompt) ──────────────────────────
r = test_endpoint("execute empty prompt", "POST", "/api/execute",
                  body={"prompt": ""})
if r:
    try:
        data = r.json()
        check("execute error: status == error", data.get("status") == "error", data.get("status"))
        check("execute error: response is null", data.get("response") is None, data.get("response"))
        check("execute error: has error message", bool(data.get("error")), data.get("error"))
        print(f"  Error response: {json.dumps(data, indent=4)}")
    except Exception as e:
        check("execute error: valid JSON", False, str(e))


# ── 8. GET /api/students ───────────────────────────────────────────────────────
r = test_endpoint("students", "GET", "/api/students")
if r:
    check("students: status 200", r.status_code == 200)
    try:
        data = r.json()
        print(f"  Students returned: {len(data) if isinstance(data, list) else data}")
    except Exception as e:
        check("students: valid JSON", False, str(e))


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS: {len(PASS)} passed, {len(FAIL)} failed")
print(f"{'='*60}")
if FAIL:
    print("  FAILED:")
    for f in FAIL:
        print(f"    ❌ {f}")
else:
    print("  All checks passed! ✅")
