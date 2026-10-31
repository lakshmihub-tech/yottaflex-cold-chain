
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "cold_chain.db"


def get_connection():
    return sqlite3.connect(DATABASE_FILE)


def test_database_exists():
    assert DATABASE_FILE.exists()


def test_products_count():
    connection = get_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM Product"
    ).fetchone()[0]
    connection.close()

    assert count == 5


def test_containers_count():
    connection = get_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM Container"
    ).fetchone()[0]
    connection.close()

    assert count == 300


def test_shipments_count():
    connection = get_connection()
    count = connection.execute(
        "SELECT COUNT(*) FROM Shipment"
    ).fetchone()[0]
    connection.close()

    assert count == 1000


def test_shipments_have_valid_products():
    connection = get_connection()

    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM Shipment s
        LEFT JOIN Product p
        ON s.product_id = p.product_id
        WHERE p.product_id IS NULL
    """).fetchone()[0]

    connection.close()

    assert invalid == 0
