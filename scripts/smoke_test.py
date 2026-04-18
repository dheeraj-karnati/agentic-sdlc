"""
Smoke test: Verify the complete AI pipeline works.
Tests: Anthropic API -> LangChain -> pgvector -> PostgreSQL

Run with: uv run python scripts/smoke_test.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def test_anthropic() -> None:
    """Test Claude API via LangChain."""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=200,
    )
    response = await llm.ainvoke("Respond with exactly: SMOKE_TEST_PASSED")
    assert "SMOKE_TEST_PASSED" in response.content
    print("[PASS] Anthropic API + LangChain working")


async def test_database() -> None:
    """Test PostgreSQL connection and pgvector extension."""
    import asyncpg

    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://sdlc:sdlc_password@localhost:5432/agentic_sdlc")
    conn = await asyncpg.connect(db_url)

    # Basic connectivity
    result = await conn.fetchval("SELECT 1")
    assert result == 1

    # pgvector extension
    result = await conn.fetchval(
        "SELECT extname FROM pg_extension WHERE extname='vector'"
    )
    assert result == "vector"

    # Tables exist
    count = await conn.fetchval(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='projects'"
    )
    assert count == 1

    await conn.close()
    print("[PASS] PostgreSQL + pgvector working")


async def test_vector_storage() -> None:
    """Test storing and retrieving vector embeddings."""
    import asyncpg

    db_url = os.getenv("DATABASE_URL_SYNC", "postgresql://sdlc:sdlc_password@localhost:5432/agentic_sdlc")
    conn = await asyncpg.connect(db_url)

    # Create test project
    project_id = await conn.fetchval(
        "INSERT INTO projects (name, description) "
        "VALUES ('Smoke Test', 'Testing vector storage') "
        "RETURNING id"
    )

    # Insert test vector
    test_vector = [0.1] + [0.0] * 1535
    vector_str = "[" + ",".join(str(v) for v in test_vector) + "]"

    await conn.execute(
        "INSERT INTO business_context "
        "(project_id, category, title, content, embedding) "
        "VALUES ($1, 'test', 'Smoke Test Entry', 'Test content', $2::vector)",
        project_id,
        vector_str,
    )

    # Similarity search
    result = await conn.fetchval(
        "SELECT title FROM business_context "
        "ORDER BY embedding <=> $1::vector LIMIT 1",
        vector_str,
    )
    assert result == "Smoke Test Entry"

    # Cleanup
    await conn.execute("DELETE FROM business_context WHERE project_id = $1", project_id)
    await conn.execute("DELETE FROM projects WHERE id = $1", project_id)
    await conn.close()
    print("[PASS] Vector embedding storage and similarity search working")


async def test_redis() -> None:
    """Test Redis connectivity."""
    import redis.asyncio as aioredis

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    r = aioredis.from_url(redis_url)
    await r.set("smoke_test", "ok")
    val = await r.get("smoke_test")
    assert val == b"ok"
    await r.delete("smoke_test")
    await r.aclose()
    print("[PASS] Redis working")


async def main() -> None:
    print("=== Agentic SDLC Smoke Test ===")
    print()

    failures = 0

    for test_fn in [test_database, test_vector_storage, test_redis, test_anthropic]:
        try:
            await test_fn()
        except Exception as e:
            print(f"[FAIL] {test_fn.__name__}: {e}")
            failures += 1

    print()
    if failures == 0:
        print("All smoke tests passed! Your environment is ready.")
    else:
        print(f"{failures} test(s) failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
