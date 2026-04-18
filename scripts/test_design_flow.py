"""End-to-end test: discovery → approval → design agent → design approval.

Tests the full pipeline from discovery through design with the skip-questions
shortcut to ensure the flow completes deterministically.

Usage:
    PYTHONPATH=. uv run python scripts/test_design_flow.py

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


def poll_status(
    client: httpx.Client, project_id: str, run_id: str, label: str
) -> dict:
    """Poll agent status until it reaches a terminal state."""
    for i in range(90):
        time.sleep(2)
        resp = client.get(f"{BASE}/projects/{project_id}/agents/{run_id}/status")
        data = resp.json()
        status = data["status"]
        print(f"    poll {i+1}: {label} status={status}")
        if status in ("paused_for_approval", "completed", "failed", "paused_for_input"):
            return data
    print(f"FAIL: {label} did not complete within 180 seconds")
    sys.exit(1)


def main() -> None:
    client = httpx.Client(timeout=60)
    errors: list[str] = []

    # ── Step 1: Create project ──
    print("\n── Step 1: Create project ──")
    resp = client.post(f"{BASE}/projects/", json={"name": "Design Flow Test"})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    print(f"OK: project {project_id}")

    # ── Step 2: Start discovery ──
    print("\n── Step 2: Start discovery ──")
    resp = client.post(
        f"{BASE}/projects/{project_id}/agents/discovery/start",
        json={"document_text": SAMPLE_TEXT},
    )
    assert resp.status_code == 201
    discovery_run_id = resp.json()["run_id"]
    print(f"OK: discovery run {discovery_run_id}")

    # ── Step 3: Wait for discovery, skip questions if needed ──
    print("\n── Step 3: Wait for discovery ──")
    data = poll_status(client, project_id, discovery_run_id, "discovery")

    if data["status"] == "paused_for_input":
        print("    skipping questions...")
        resp = client.post(
            f"{BASE}/projects/{project_id}/agents/{discovery_run_id}/skip-questions"
        )
        assert resp.status_code == 200
        data = poll_status(client, project_id, discovery_run_id, "discovery (post-skip)")

    if data["status"] == "failed":
        print(f"FAIL: discovery failed: {data.get('errors')}")
        sys.exit(1)

    print(f"    discovery final status: {data['status']}")

    # ── Step 4: Check discovery approval gate ──
    print("\n── Step 4: Check discovery approval gate ──")
    resp = client.get(f"{BASE}/projects/{project_id}/approvals/")
    approvals = resp.json()
    assert approvals["total"] >= 1, "No approval gates created"
    discovery_gate = approvals["approvals"][0]
    print(f"    gate {discovery_gate['id']} → {discovery_gate['status']}")

    # ── Step 5: Approve discovery → project advances to "design" ──
    print("\n── Step 5: Approve discovery ──")
    resp = client.post(
        f"{BASE}/projects/{project_id}/approvals/{discovery_gate['id']}/decide",
        json={"status": "approved", "reviewer_notes": "Good findings."},
    )
    assert resp.status_code == 200
    decide = resp.json()
    print(f"    project status: {decide['project_status']}")
    if decide["project_status"] != "design":
        errors.append(f"Expected 'design', got '{decide['project_status']}'")

    # ── Step 6: Start design agent ──
    print("\n── Step 6: Start design agent ──")
    resp = client.post(
        f"{BASE}/projects/{project_id}/agents/design/start",
        json={},
    )
    if resp.status_code != 201:
        print(f"FAIL: start design returned {resp.status_code}: {resp.text}")
        sys.exit(1)
    design_run_id = resp.json()["run_id"]
    print(f"OK: design run {design_run_id}")

    # ── Step 7: Wait for design agent to complete ──
    print("\n── Step 7: Wait for design agent ──")
    data = poll_status(client, project_id, design_run_id, "design")

    if data["status"] == "failed":
        print(f"FAIL: design agent failed: {data.get('errors')}")
        sys.exit(1)

    print(f"    design final status: {data['status']}")

    # ── Step 8: Retrieve design output and verify artifacts ──
    print("\n── Step 8: Retrieve design output ──")
    resp = client.get(
        f"{BASE}/projects/{project_id}/agents/{design_run_id}/design-output"
    )
    assert resp.status_code == 200
    output = resp.json()
    design = output.get("design", {})
    artifacts = output.get("artifacts", [])

    print(f"    design sections: {list(design.keys())}")
    print(f"    artifacts stored: {len(artifacts)}")

    expected_sections = [
        "architecture", "database_schema", "api_specification",
        "auth_design", "frontend_components",
    ]
    for section in expected_sections:
        if section not in design:
            errors.append(f"Missing design section: {section}")
        else:
            print(f"    ✓ {section}")

    if len(artifacts) < 5:
        errors.append(f"Expected 5 artifacts, got {len(artifacts)}")

    # ── Step 9: Check design approval gate ──
    print("\n── Step 9: Check design approval gate ──")
    resp = client.get(f"{BASE}/projects/{project_id}/approvals/")
    approvals = resp.json()
    # Should have 2 gates: discovery + design
    design_gates = [g for g in approvals["approvals"] if g["id"] != discovery_gate["id"]]
    if not design_gates:
        errors.append("No design approval gate created")
    else:
        design_gate = design_gates[0]
        print(f"    design gate {design_gate['id']} → {design_gate['status']}")
        if design_gate["status"] != "pending":
            errors.append(f"Expected pending, got {design_gate['status']}")

        # ── Step 10: Approve design → project advances to "prototype" ──
        print("\n── Step 10: Approve design ──")
        resp = client.post(
            f"{BASE}/projects/{project_id}/approvals/{design_gate['id']}/decide",
            json={"status": "approved", "reviewer_notes": "Good design."},
        )
        assert resp.status_code == 200
        decide = resp.json()
        print(f"    project status: {decide['project_status']}")
        if decide["project_status"] != "prototype":
            errors.append(f"Expected 'prototype', got '{decide['project_status']}'")

    # ── Summary ──
    print("\n" + "=" * 60)
    if errors:
        print("SOME CHECKS FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED!")
        print("  discovery → approved → design agent → 5 artifacts stored")
        print("  → design approved → project advanced to 'prototype'")


if __name__ == "__main__":
    main()