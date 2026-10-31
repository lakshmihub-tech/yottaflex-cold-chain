
import sqlite3
from pathlib import Path

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

SCHEMA_FILE = BASE_DIR / "src" / "schema.sql"
DATA_DIR = BASE_DIR / "data"
DATABASE_FILE = DATA_DIR / "cold_chain.db"


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Verify schema file
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_FILE}"
        )

    connection = sqlite3.connect(DATABASE_FILE)

    try:
        # Enable foreign key constraints
        connection.execute("PRAGMA foreign_keys = ON")

        # Read SQL schema
        schema = SCHEMA_FILE.read_text(encoding="utf-8")

        if not schema.strip():
            raise ValueError("Schema file is empty.")

        # Execute schema
        connection.executescript(schema)

        # Verify database integrity
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        # Verify foreign key relationships
        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        # Get all tables
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        # Display results
        print("\n" + "=" * 50)
        print("YOTTAFLEX COLD CHAIN DATABASE")
        print("=" * 50)

        print("\nDatabase location:")
        print(DATABASE_FILE)

        print("\nTables created / verified:")

        for table in tables:
            print(f"  - {table[0]}")

        print(f"\nTotal tables: {len(tables)}")

        print("\nIntegrity check:", integrity)

        if foreign_key_errors:
            print("\nForeign key errors:")
            for error in foreign_key_errors:
                print(error)

            raise RuntimeError(
                "Database foreign key validation failed."
            )

        print("Foreign key validation: PASSED")

        if integrity != "ok":
            raise RuntimeError(
                "Database integrity check failed."
            )

        print("\nDATABASE INITIALIZATION SUCCESSFUL!")

    finally:
        connection.close()


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    initialize_database()
