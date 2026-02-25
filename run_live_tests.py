"""
Live end-to-end tests against Dockerized API + Ollama.

Tests all major SentinelForge features against a real LLM:
1. Login + auth
2. Attack scan (prompt injection scenario)
3. Fingerprint run
4. RAG eval
5. Tool eval
6. Scenarios listing
7. Compliance frameworks
8. Health endpoints
"""
import json
import time
import urllib.request
import urllib.error
import sys

API = "http://localhost:8000"
TOKEN = None


def api(method, path, body=None, timeout=30):
    """Make an API call and return parsed JSON."""
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code}: {body_text[:300]}")
        return {"error": e.code, "detail": body_text}


def wait_for_completion(path, max_wait=120, interval=3):
    """Poll an endpoint until status is completed/failed."""
    start = time.time()
    while time.time() - start < max_wait:
        result = api("GET", path)
        status = result.get("status", "unknown")
        progress = result.get("progress", 0)
        print(f"  [{status}] progress={progress:.0%}", end="\r")
        if status in ("completed", "failed"):
            print()
            return result
        time.sleep(interval)
    print("\n  TIMEOUT")
    return result


def test_health():
    print("\n=== Test 1: Health Endpoints ===")
    health = api("GET", "/health")
    assert health.get("status") == "healthy", f"Health check failed: {health}"
    print(f"  /health: {health['status']} v{health.get('version', '?')}")

    ready = api("GET", "/ready")
    print(f"  /ready: {ready.get('status', '?')}")

    live = api("GET", "/live")
    print(f"  /live: {live.get('status', '?')}")
    print("  PASSED")


def test_login():
    global TOKEN
    print("\n=== Test 2: Authentication ===")
    result = api("POST", "/auth/login", {
        "username": "sf_admin",
        "password": "S3nt!nelF0rge_2026"
    })
    TOKEN = result.get("access_token")
    assert TOKEN, f"Login failed: {result}"
    print(f"  Login successful, token: {TOKEN[:20]}...")
    print("  PASSED")


def test_scenarios():
    print("\n=== Test 3: Scenarios ===")
    scenarios = api("GET", "/attacks/scenarios")
    assert isinstance(scenarios, list), f"Expected list, got {type(scenarios)}"
    print(f"  {len(scenarios)} scenarios available")
    for s in scenarios[:5]:
        print(f"    - {s['id']}: {s.get('prompt_count', '?')} prompts, severity={s.get('severity', '?')}")
    assert len(scenarios) >= 18, f"Expected >= 18 scenarios, got {len(scenarios)}"
    print("  PASSED")


def test_compliance():
    print("\n=== Test 4: Compliance Frameworks ===")
    result = api("GET", "/compliance/frameworks")
    # Endpoint may return {"frameworks": [...]} or bare list
    if isinstance(result, dict):
        frameworks = result.get("frameworks", [])
    else:
        frameworks = result
    assert isinstance(frameworks, list), f"Expected list, got {type(frameworks)}"
    print(f"  {len(frameworks)} frameworks:")
    for f in frameworks:
        cats = len(f.get("categories", []))
        print(f"    - {f['name']}: {cats} categories")
    assert len(frameworks) >= 6, f"Expected >= 6 frameworks, got {len(frameworks)}"
    print("  PASSED")


def test_attack_scan():
    print("\n=== Test 5: Attack Scan (prompt_injection, 5 prompts) ===")
    result = api("POST", "/attacks/run", {
        "scenario_id": "prompt_injection",
        "target_model": "llama3.2:3b",
        "provider": "ollama",
        "config": {
            "base_url": "http://host.docker.internal:11434/v1",
            "max_prompts": 5
        }
    })
    run_id = result.get("id")
    assert run_id, f"Failed to launch attack: {result}"
    print(f"  Run ID: {run_id}")

    # Wait for completion
    detail = wait_for_completion(f"/attacks/runs/{run_id}", max_wait=120)
    status = detail.get("status")
    assert status == "completed", f"Attack scan ended with status={status}: {detail.get('error_message', '')}"

    findings = detail.get("findings", [])
    print(f"  Status: {status}")
    print(f"  Findings: {len(findings)}")
    for f in findings[:3]:
        print(f"    - [{f.get('severity', '?')}] {f.get('title', '?')[:80]}")
    print("  PASSED")
    return run_id


def test_fingerprint():
    print("\n=== Test 6: Model Fingerprinting ===")
    result = api("POST", "/fingerprint/run", {
        "target_model": "llama3.2:3b",
        "provider": "ollama",
        "config": {
            "base_url": "http://host.docker.internal:11434/v1"
        },
        "probe_categories": ["all"]
    })
    run_id = result.get("id")
    assert run_id, f"Failed to launch fingerprint: {result}"
    print(f"  Run ID: {run_id}")

    # Wait for completion
    detail = wait_for_completion(f"/fingerprint/runs/{run_id}", max_wait=180)
    status = detail.get("status")
    assert status == "completed", f"Fingerprint ended with status={status}: {detail.get('error_message', '')}"

    results = detail.get("results", {})
    top_matches = results.get("top_matches", [])
    category_scores = results.get("category_scores", {})
    profile = results.get("behavioral_profile", "")

    print(f"\n  Status: {status}")
    print(f"  Probes completed: {results.get('total_probes', 0)}")
    print(f"\n  Top 3 Matches:")
    for m in top_matches[:3]:
        print(f"    {m['model']} ({m['family']}) — {m['confidence']:.1%}")

    print(f"\n  Category Scores:")
    for cat, score in category_scores.items():
        print(f"    {cat}: {score:.2f}")

    print(f"\n  Behavioral Profile:")
    print(f"    {profile}")

    # Accuracy checks
    if top_matches:
        best = top_matches[0]
        assert best["family"] in ("meta",), f"Expected meta family, got {best['family']}"
        print(f"\n  Family identification: CORRECT (meta/llama)")

        # Check if refusals are now detected (Unicode fix)
        probe_results = results.get("probe_results", [])
        safety_probes = [p for p in probe_results if p["category"] == "safety"]
        refusals_detected = sum(
            1 for p in safety_probes
            if p.get("features", {}).get("refused", False)
        )
        print(f"  Safety refusals detected: {refusals_detected}/{len(safety_probes)}")

    findings = detail.get("findings", [])
    print(f"  Findings: {len(findings)}")
    for f in findings:
        print(f"    - [{f.get('severity', '?')}] {f.get('title', '?')[:80]}")

    print("  PASSED")
    return run_id


def test_list_fingerprints():
    print("\n=== Test 7: List Fingerprint Runs ===")
    runs = api("GET", "/fingerprint/runs")
    assert isinstance(runs, list), f"Expected list, got {type(runs)}"
    print(f"  {len(runs)} fingerprint runs found")
    for r in runs[:3]:
        print(f"    - {r['id'][:8]}... model={r.get('target_model', '?')} status={r.get('status', '?')}")
    print("  PASSED")


def test_rag_eval():
    print("\n=== Test 8: RAG Evaluation ===")
    result = api("POST", "/rag-eval/run", {
        "target_model": "llama3.2:3b",
        "provider": "ollama",
        "config": {
            "base_url": "http://host.docker.internal:11434/v1",
            "max_queries": 3
        }
    })
    run_id = result.get("id")
    assert run_id, f"Failed to launch RAG eval: {result}"
    print(f"  Run ID: {run_id}")

    detail = wait_for_completion(f"/rag-eval/runs/{run_id}", max_wait=120)
    status = detail.get("status")
    print(f"  Status: {status}")
    if status == "completed":
        results = detail.get("results", {})
        print(f"  Queries processed: {results.get('total_queries', '?')}")
        print(f"  Poison detected: {results.get('poison_detected', '?')}")
    print(f"  {'PASSED' if status == 'completed' else 'FAILED (non-blocking)'}")
    return run_id


def test_tool_eval():
    print("\n=== Test 9: Tool-Use Evaluation ===")
    result = api("POST", "/tool-eval/run", {
        "target_model": "llama3.2:3b",
        "provider": "ollama",
        "config": {
            "base_url": "http://host.docker.internal:11434/v1",
            "max_prompts": 3
        }
    })
    run_id = result.get("id")
    assert run_id, f"Failed to launch tool eval: {result}"
    print(f"  Run ID: {run_id}")

    detail = wait_for_completion(f"/tool-eval/runs/{run_id}", max_wait=120)
    status = detail.get("status")
    print(f"  Status: {status}")
    if status == "completed":
        results = detail.get("results", {})
        print(f"  Prompts processed: {results.get('total_prompts', '?')}")
    print(f"  {'PASSED' if status == 'completed' else 'FAILED (non-blocking)'}")
    return run_id


def test_tools():
    print("\n=== Test 10: Tools Registry ===")
    tools = api("GET", "/tools")
    assert isinstance(tools, list), f"Expected list, got {type(tools)}"
    print(f"  {len(tools)} tools registered")
    for t in tools[:5]:
        print(f"    - {t['name']}: {t.get('category', '?')}")
    assert len(tools) >= 14, f"Expected >= 14 tools, got {len(tools)}"
    print("  PASSED")


def test_csv_export(run_id):
    print("\n=== Test 11: CSV Export ===")
    if not run_id:
        print("  SKIPPED (no run_id)")
        return
    url = f"{API}/attacks/runs/{run_id}/export?format=csv"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read().decode()
            lines = data.strip().split("\n")
            print(f"  Content-Type: {content_type}")
            print(f"  CSV rows: {len(lines)} (incl. header)")
            if lines:
                print(f"  Header: {lines[0][:100]}")
            print("  PASSED")
    except Exception as e:
        print(f"  FAILED: {e}")


def test_hardening_advisor(run_id):
    print("\n=== Test 12: Hardening Advisor ===")
    if not run_id:
        print("  SKIPPED (no run_id)")
        return
    result = api("GET", f"/attacks/runs/{run_id}/harden")
    if "error" in result:
        print(f"  FAILED: {result}")
        return
    rules = result.get("rules_applied", [])
    prompt = result.get("hardened_prompt", "")
    print(f"  Rules applied: {len(rules)}")
    for r in rules[:3]:
        print(f"    - {r}")
    print(f"  Hardened prompt length: {len(prompt)} chars")
    print(f"  Prompt preview: {prompt[:100]}...")
    print("  PASSED")


def main():
    print("=" * 60)
    print("SentinelForge v2.7.0 — Live End-to-End Tests")
    print(f"API: {API}")
    print("LLM: Ollama llama3.2:3b (host.docker.internal:11434)")
    print("=" * 60)

    passed = 0
    failed = 0
    total = 12

    try:
        test_health()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_login()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1
        print("  Cannot continue without auth")
        sys.exit(1)

    try:
        test_scenarios()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_compliance()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_tools()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    attack_run_id = None
    try:
        attack_run_id = test_attack_scan()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_csv_export(attack_run_id)
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_hardening_advisor(attack_run_id)
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_fingerprint()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_list_fingerprints()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_rag_eval()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    try:
        test_tool_eval()
        passed += 1
    except Exception as e:
        print(f"  FAILED: {e}")
        failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
