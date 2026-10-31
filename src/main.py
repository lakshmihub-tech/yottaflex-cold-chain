import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "cold_chain.db"


def check_database():
    """Check database availability and integrity."""

    if not DATABASE_FILE.exists():
        print("ERROR: Database not found.")
        print("Run: python src/init_db.py")
        return False

    try:
        with sqlite3.connect(DATABASE_FILE) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            if integrity != "ok":
                print("ERROR: Database integrity check failed.")
                return False

            foreign_key_errors = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if foreign_key_errors:
                print("ERROR: Foreign key validation failed.")
                return False

        return True

    except sqlite3.Error as error:
        print(f"Database error: {error}")
        return False


def display_summary():
    """Display important project data counts."""

    queries = {
        "Products": "SELECT COUNT(*) FROM Product",
        "Shipments": "SELECT COUNT(*) FROM Shipment",
        "Containers": "SELECT COUNT(*) FROM Container",
        "Sensors": "SELECT COUNT(*) FROM Sensor",
        "Sensor Readings": "SELECT COUNT(*) FROM SensorReading",
        "Route Stops": "SELECT COUNT(*) FROM RouteStop",
        "Excursions": "SELECT COUNT(*) FROM Excursion",
        "Corrective Actions": "SELECT COUNT(*) FROM CorrectiveAction",
    }

    with sqlite3.connect(DATABASE_FILE) as connection:
        print("\nPROJECT DATA SUMMARY")
        print("-" * 40)

        for label, query in queries.items():
            count = connection.execute(query).fetchone()[0]
            print(f"{label:<22}: {count:,}")

        print("-" * 40)


def main():
    print("=" * 55)
    print("YOTTAFLEX COLD CHAIN MONITORING SYSTEM")
    print("=" * 55)

    print("\nStep 1: Checking database...")

    if not check_database():
        print("\nSystem startup failed.")
        sys.exit(1)

    print("Database integrity: PASSED")
    print("Foreign key validation: PASSED")

    print("\nStep 2: Loading project summary...")
    display_summary()

    print("\nSYSTEM STATUS: READY")
    print("\nTo launch the dashboard, run:")
    print("streamlit run src/dashboard.py")


if __name__ == "__main__":
    main()