"""End-to-end test: project creation → discovery → approval gate → approve → project advances.

Usage:
    PYTHONPATH=. uv run python scripts/test_full_flow.py

Requires the FastAPI server to be running on http://127.0.0.1:8000.
"""

import sys
import time

import httpx

BASE = "http://127.0.0.1:8000/api"
SAMPLE_TEXT = """\
ACME Inventory Management System - Legacy Application Overview

The system manages warehouse inventory across 3 regional distribution centers.
It tracks product SKUs, quantities, reorder points, and supplier relationships.

Business Rules:
- Reorder is triggered automatically when stock falls below the reorder point.
- Each product has exactly one primary supplier and up to two backup suppliers.
- Inventory adjustments over $10,000 require manager approval.
- Monthly reconciliation reports are generated on the 1st of each month.
- Products with no movement for 90 days are flagged for review.

Technical Details:
- Built on Visual Basic 6 with a Microsoft Access backend (2003 era).
- Barcode scanning integration via RS-232 serial port.
- Reports generated as Crystal Reports .rpt files.
- Single-server deployment, no high availability.
"""


def main() -> None:
    client = httpx.Client(timeout=60)
    errors: list[str] = []

    # ── Step 1: Create project ──
    print("\n── Step 1: Create project ──")
    resp = client.post(f"{BASE}/projects/", json={"name": "Full Flow Test Project"})
    if resp.status_code != 201:
        print(f"FAIL: create project returned {resp.status_code}: {resp.text}")
        sys.exit(1)
    project = resp.json()
    project_id = project["id"]
    print(f"OK: project created → {project_id} (status: {project['status']})")

    # ── Step 2: Start discovery ──
    print("\n── Step 2: Start discovery agent ──")
    resp = client.post(
        f"{BASE}/projects/{project_id}/agents/discovery/start",
        json={"document_text": SAMPLE_TEXT},
    )
    if resp.status_code != 201:
        print(f"FAIL: start discovery returned {resp.status_code}: {resp.text}")
        sys.exit(1)
    run_id = resp.json()["run_id"]
    print(f"OK: discovery started → run_id={run_id}")

    # Verify project status is now "discovery"
    resp = client.get(f"{BASE}/projects/{project_id}")
    proj_status = resp.json()["status"]
    print(f"    project status after start: {proj_status}")
    if proj_status != "discovery":
        errors.append(f"Expected project status 'discovery', got '{proj_status}'")

    # ── Step 3: Poll for agent completion ──
    print("\n── Step 3: Wait for discovery to complete ──")
    for i in range(60):
        time.sleep(2)
        resp = client.get(f"{BASE}/projects/{project_id}/agents/{run_id}/status")
        status_data = resp.json()
        status = status_data["status"]
        print(f"    poll {i+1}: status={status}")
        if status in ("paused_for_approval", "completed", "failed", "paused_for_input"):
            break
    else:
        print("FAIL: agent did not complete within 120 seconds")
        sys.exit(1)

    # If agent paused for input (asking questions), skip questions and proceed
    if status == "paused_for_input":
        questions = status_data.get("pending_questions", [])
        print(f"    agent has {len(questions)} clarification questions — skipping to proceed")
        resp = client.post(
            f"{BASE}/projects/{project_id}/agents/{run_id}/skip-questions",
        )
        if resp.status_code != 200:
            print(f"    skip FAILED: {resp.status_code} → {resp.text}")
            sys.exit(1)
        print(f"    skip OK: {resp.json().get('message')}")

        # Poll again for completion
        for i in range(60):
            time.sleep(2)
            resp = client.get(f"{BASE}/projects/{project_id}/agents/{run_id}/status")
            status = resp.json()["status"]
            print(f"    poll {i+1}: status={status}")
            if status in ("paused_for_approval", "completed", "failed"):
                break
        else:
            print("FAIL: agent did not complete after skipping questions")
            sys.exit(1)

    if status == "failed":
        print(f"    agent failed: {resp.json().get('errors')}")

    # Check approval gates
    print("\n── Step 3b: Check approval gates ──")
    resp = client.get(f"{BASE}/projects/{project_id}/approvals/")
    approvals = resp.json()
    total = approvals["total"]
    print(f"    total approval gates: {total}")

    if total == 0:
        print("FAIL: no approval gates created despite agent completing")
        sys.exit(1)

    gate = approvals["approvals"][0]
    gate_id = gate["id"]
    gate_status = gate["status"]
    print(f"    gate {gate_id} → status: {gate_status}")
    if gate_status != "pending":
        errors.append(f"Expected gate status 'pending', got '{gate_status}'")

    # ── Step 4: Approve the gate ──
    print("\n── Step 4: Submit approval decision ──")
    resp = client.post(
        f"{BASE}/projects/{project_id}/approvals/{gate_id}/decide",
        json={"status": "approved", "reviewer_notes": "Looks good, proceed to design."},
    )
    if resp.status_code != 200:
        print(f"FAIL: decide returned {resp.status_code}: {resp.text}")
        sys.exit(1)
    decide = resp.json()
    print(f"    decision status: {decide['status']}")
    print(f"    project status: {decide['project_status']}")
    print(f"    message: {decide['message']}")

    # ── Step 5: Verify project advanced to "design" ──
    print("\n── Step 5: Verify project advanced ──")
    resp = client.get(f"{BASE}/projects/{project_id}")
    final_status = resp.json()["status"]
    print(f"    final project status: {final_status}")

    if final_status != "design":
        errors.append(f"Expected final status 'design', got '{final_status}'")

    # ── Summary ──
    print("\n" + "=" * 50)
    if errors:
        print("SOME CHECKS FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED - Full flow works end-to-end!")
        print("  project created → discovery ran → approval gate created (pending)")
        print("  → approved → project advanced to 'design'")


if __name__ == "__main__":
    main()