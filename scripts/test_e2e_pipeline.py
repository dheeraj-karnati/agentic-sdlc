"""End-to-end test: runs all 4 agents through the full SDLC pipeline via the API.

Usage:
    uv run python scripts/test_e2e_pipeline.py

Flow:
    1. Create a new project
    2. Discovery Agent → poll until done → approve
    3. Design Agent → poll until done → approve
    4. Prototype Agent → poll until done → approve
    5. Planning Agent → poll until done → verify epics/stories
"""

import asyncio
import sys
import time

import httpx

BASE = "http://localhost:8000"
POLL_INTERVAL = 5  # seconds between status polls
MAX_WAIT = 600  # max seconds to wait for an agent (10 min)

SAMPLE_DOCUMENT = """\
VISION Application - Legacy System Documentation

1. BUSINESS RULES
- BR-001: All purchase orders over $10,000 require manager approval before processing.
- BR-002: Inventory levels must be checked before any order is confirmed.
  If stock < requested quantity, backorder is created automatically.
- BR-003: Customer discount tiers: Bronze (0-5%), Silver (5-10%), Gold (10-15%).
  Tier is calculated based on rolling 12-month purchase history.
- BR-004: Returns must be processed within 30 days of delivery.
  Restocking fee of 15% applies to non-defective returns.

2. REQUIREMENTS
- FR-001: Users must be able to search products by name, SKU, or category.
- FR-002: Dashboard shall display real-time inventory levels across all warehouses.
- FR-003: System shall generate monthly sales reports grouped by region and product.
- NFR-001: Page load time must be under 2 seconds for 95th percentile.
- NFR-002: System must support 500 concurrent users without degradation.

3. TECHNICAL DETAILS
- Architecture: 3-tier monolith (4GL UI → Business Logic → Oracle 11g DB)
- Database: 47 tables, heavy use of stored procedures for business logic
- Integration: EDI interface with 3 supplier systems, FTP-based file exchange
- Authentication: LDAP-based SSO, 4 role levels (viewer, operator, manager, admin)
- Batch jobs: Nightly inventory reconciliation, weekly report generation
"""


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0, follow_redirects=True) as c:
        # ── 0. Health check ──
        r = await c.get("/health")
        if r.status_code != 200:
            print(f"FAIL: health check returned {r.status_code}")
            sys.exit(1)
        print("OK  Health check passed\n")

        # ── 1. Create project ──
        r = await c.post("/api/projects/", json={
            "name": "E2E Pipeline Test",
            "description": "Automated end-to-end pipeline test run",
        })
        assert r.status_code == 201, f"Create project failed: {r.status_code} {r.text}"
        project = r.json()
        pid = project["id"]
        print(f"OK  Created project: {pid}")
        print(f"    Status: {project['status']}\n")

        # ── 2. Discovery Agent ──
        print("=" * 60)
        print("PHASE 1: DISCOVERY AGENT")
        print("=" * 60)

        # Set project status to discovery (start_discovery does this)
        r = await c.post(f"/api/projects/{pid}/agents/discovery/start", json={
            "document_text": SAMPLE_DOCUMENT,
        })
        assert r.status_code == 201, f"Start discovery failed: {r.status_code} {r.text}"
        discovery_run_id = r.json()["run_id"]
        print(f"OK  Discovery started: run_id={discovery_run_id}")

        # Poll for completion
        status = await poll_agent(c, pid, discovery_run_id, "Discovery")

        # If paused for input (clarity questions), skip and proceed
        if status == "paused_for_input":
            print("    Discovery has clarification questions — skipping to proceed")
            r = await c.post(
                f"/api/projects/{pid}/agents/{discovery_run_id}/skip-questions"
            )
            assert r.status_code == 200, f"Skip questions failed: {r.status_code} {r.text}"
            print("OK  Questions skipped, re-running discovery")
            status = await poll_agent(c, pid, discovery_run_id, "Discovery (skip)")

        if status == "failed":
            print("FAIL: Discovery agent failed")
            await print_status(c, pid, discovery_run_id)
            sys.exit(1)

        # Approve discovery
        gate_id = await get_pending_gate(c, pid)
        if not gate_id:
            print("FAIL: No pending approval gate after discovery")
            sys.exit(1)
        await approve_gate(c, pid, gate_id, "Discovery")

        # Verify project advanced to 'design'
        project = await get_project(c, pid)
        print(f"    Project status: {project['status']}")
        assert project["status"] == "design", f"Expected 'design', got '{project['status']}'"
        print()

        # ── 3. Design Agent ──
        print("=" * 60)
        print("PHASE 2: DESIGN AGENT")
        print("=" * 60)

        r = await c.post(f"/api/projects/{pid}/agents/design/start")
        assert r.status_code == 201, f"Start design failed: {r.status_code} {r.text}"
        design_run_id = r.json()["run_id"]
        print(f"OK  Design started: run_id={design_run_id}")

        status = await poll_agent(c, pid, design_run_id, "Design")
        if status == "failed":
            print("FAIL: Design agent failed")
            await print_status(c, pid, design_run_id)
            sys.exit(1)

        gate_id = await get_pending_gate(c, pid)
        if not gate_id:
            print("FAIL: No pending approval gate after design")
            sys.exit(1)
        await approve_gate(c, pid, gate_id, "Design")

        project = await get_project(c, pid)
        print(f"    Project status: {project['status']}")
        assert project["status"] == "prototype", f"Expected 'prototype', got '{project['status']}'"
        print()

        # ── 4. Prototype Agent ──
        print("=" * 60)
        print("PHASE 3: PROTOTYPE AGENT")
        print("=" * 60)

        r = await c.post(f"/api/projects/{pid}/agents/prototype/start")
        assert r.status_code == 201, f"Start prototype failed: {r.status_code} {r.text}"
        proto_run_id = r.json()["run_id"]
        print(f"OK  Prototype started: run_id={proto_run_id}")

        status = await poll_agent(c, pid, proto_run_id, "Prototype")
        if status == "failed":
            print("FAIL: Prototype agent failed")
            await print_status(c, pid, proto_run_id)
            sys.exit(1)

        gate_id = await get_pending_gate(c, pid)
        if not gate_id:
            print("FAIL: No pending approval gate after prototype")
            sys.exit(1)
        await approve_gate(c, pid, gate_id, "Prototype")

        project = await get_project(c, pid)
        print(f"    Project status: {project['status']}")
        assert project["status"] == "planning", f"Expected 'planning', got '{project['status']}'"
        print()

        # ── 5. Planning Agent ──
        print("=" * 60)
        print("PHASE 4: PLANNING AGENT")
        print("=" * 60)

        r = await c.post(f"/api/projects/{pid}/planning/start")
        assert r.status_code == 201, f"Start planning failed: {r.status_code} {r.text}"
        planning_run_id = r.json()["run_id"]
        print(f"OK  Planning started: run_id={planning_run_id}")

        status = await poll_agent(c, pid, planning_run_id, "Planning")
        if status == "failed":
            print("FAIL: Planning agent failed")
            await print_status(c, pid, planning_run_id)
            sys.exit(1)

        # Check plan artifact was created
        r = await c.get(f"/api/projects/{pid}/planning/{planning_run_id}/artifact")
        assert r.status_code == 200, f"Get artifact failed: {r.status_code} {r.text}"
        artifact = r.json()
        plan = artifact["plan"]
        epics_in_plan = plan.get("epics", [])
        total_stories = sum(len(e.get("stories", [])) for e in epics_in_plan)
        print(f"    Plan artifact: {len(epics_in_plan)} epics, {total_stories} stories")

        if epics_in_plan:
            print(f"    Sample epic: {epics_in_plan[0]['title']}")
            epic_stories = epics_in_plan[0].get("stories", [])
            if epic_stories:
                print(f"    Sample story: {epic_stories[0]['title']}")

        # Approve planning gate
        gate_id = await get_pending_gate(c, pid)
        if gate_id:
            await approve_gate(c, pid, gate_id, "Planning")

        # Import plan to DB tables
        r = await c.post(f"/api/projects/{pid}/planning/{planning_run_id}/import")
        assert r.status_code == 200, f"Import plan failed: {r.status_code} {r.text}"
        import_result = r.json()
        print(f"    Imported: {import_result['epics_imported']} epics, {import_result['stories_imported']} stories")

        # Verify epics and stories in DB
        r = await c.get(f"/api/projects/{pid}/planning/epics")
        epics = r.json()

        r = await c.get(f"/api/projects/{pid}/planning/stories")
        stories = r.json()

        # ── Summary ──
        print()
        print("=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        project = await get_project(c, pid)
        print(f"  Project: {project['name']}")
        print(f"  Final status: {project['status']}")
        print(f"  Epics: {len(epics)}")
        print(f"  Stories: {len(stories)}")
        print(f"  All 4 agents ran successfully!")


async def poll_agent(
    client: httpx.AsyncClient, pid: str, run_id: str, label: str
) -> str:
    """Poll agent status until it leaves running/pending state."""
    start = time.time()
    last_status = ""
    while time.time() - start < MAX_WAIT:
        r = await client.get(f"/api/projects/{pid}/agents/{run_id}/status")
        if r.status_code != 200:
            print(f"    Poll error: {r.status_code}")
            await asyncio.sleep(POLL_INTERVAL)
            continue

        data = r.json()
        status = data["status"]

        if status != last_status:
            elapsed = int(time.time() - start)
            print(f"    [{elapsed:>3}s] {label}: {status}")
            last_status = status

        if status in ("completed", "paused_for_approval", "failed", "paused_for_input"):
            return status

        await asyncio.sleep(POLL_INTERVAL)

    print(f"TIMEOUT: {label} agent did not complete within {MAX_WAIT}s")
    return "timeout"


async def get_pending_gate(client: httpx.AsyncClient, pid: str) -> str | None:
    """Find the most recent pending approval gate."""
    r = await client.get(f"/api/projects/{pid}/approvals/")
    if r.status_code != 200:
        return None
    for gate in r.json()["approvals"]:
        if gate["status"] == "pending":
            return gate["id"]
    return None


async def approve_gate(
    client: httpx.AsyncClient, pid: str, gate_id: str, label: str
) -> None:
    """Approve an approval gate."""
    r = await client.post(f"/api/projects/{pid}/approvals/{gate_id}/decide", json={
        "status": "approved",
        "reviewer_notes": f"Auto-approved by E2E test",
    })
    assert r.status_code == 200, f"Approve {label} failed: {r.status_code} {r.text}"
    print(f"OK  {label} approved")


async def get_project(client: httpx.AsyncClient, pid: str) -> dict:
    """Fetch project details."""
    r = await client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
    return r.json()


async def print_status(client: httpx.AsyncClient, pid: str, run_id: str) -> None:
    """Print detailed agent status for debugging."""
    r = await client.get(f"/api/projects/{pid}/agents/{run_id}/status")
    if r.status_code == 200:
        import json
        print(json.dumps(r.json(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
