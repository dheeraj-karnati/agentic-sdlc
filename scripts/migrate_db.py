"""Apply the full init-db.sql schema to the database, executing statements one at a time.

asyncpg doesn't support multiple statements in one execute(), so we split
the SQL file on semicolons and run each statement individually.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from src.config import settings


def main() -> None:
    sql_path = Path(__file__).parent.parent / "infra" / "docker" / "init-db.sql"
    sql_content = sql_path.read_text()

    # Use sync driver (replace asyncpg with psycopg2/pg8000)
    sync_url = settings.database_url_sync
    if not sync_url:
        sync_url = settings.database_url.replace("+asyncpg", "")
    print(f"Connecting to: {sync_url}")

    engine = create_engine(sync_url)

    # Split on semicolons but be careful with $$ blocks
    # We need a smarter split that respects DO $$ ... END $$; blocks
    statements: list[str] = []
    current = ""
    in_dollar_block = False

    for line in sql_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") and not in_dollar_block:
            continue  # skip comments outside blocks

        # Track $$ blocks
        dollar_count = line.count("$$")
        if dollar_count % 2 == 1:
            in_dollar_block = not in_dollar_block

        current += line + "\n"

        if stripped.endswith(";") and not in_dollar_block:
            stmt = current.strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = ""

    print(f"Found {len(statements)} SQL statements to execute")

    with engine.connect() as conn:
        for i, stmt in enumerate(statements, 1):
            # Show first line of each statement
            first_line = stmt.split("\n")[0][:80]
            try:
                conn.execute(text(stmt))
                print(f"  [{i}/{len(statements)}] OK: {first_line}")
            except Exception as e:
                err_msg = str(e).split("\n")[0]
                # Skip "already exists" errors
                if "already exists" in err_msg or "DuplicateObject" in err_msg:
                    print(f"  [{i}/{len(statements)}] SKIP (exists): {first_line}")
                else:
                    print(f"  [{i}/{len(statements)}] ERROR: {first_line}")
                    print(f"    {err_msg}")

        conn.commit()
        print("\nMigration committed!")

        # Verify
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [row[0] for row in result.all()]
        print(f"\nTables ({len(tables)}): {tables}")

        result = conn.execute(text(
            "SELECT typname FROM pg_type WHERE typtype='e' "
            "AND typname NOT LIKE 'pg_%' ORDER BY typname"
        ))
        enums = [row[0] for row in result.all()]
        print(f"Enums ({len(enums)}): {enums}")


if __name__ == "__main__":
    main()
