
import sqlite3
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cold_chain.db"

RANDOM_SEED = 20261022


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_aligned_readings(conn):
    """
    Fetch GOOD readings belonging to an active shipment assignment.
    Use the latest effective product-specific threshold policy.
    Preserve SUSPECT readings and negative scenario evidence.
    """

    query = """
        SELECT
            r.reading_id,
            policy.min_temperature,
            policy.max_temperature,
            policy.min_humidity,
            policy.max_humidity
        FROM SensorReading r

        JOIN Sensor s
            ON s.sensor_id = r.sensor_id

        JOIN ShipmentContainer sc
            ON sc.container_id = s.container_id

        JOIN Shipment sh
            ON sh.shipment_id = sc.shipment_id

        JOIN ThresholdPolicy policy
            ON policy.policy_id = (
                SELECT tp.policy_id
                FROM ThresholdPolicy tp
                WHERE tp.product_id = sh.product_id
                  AND tp.effective_from <= r.recorded_at
                  AND (
                      tp.effective_to IS NULL
                      OR tp.effective_to >= r.recorded_at
                  )
                ORDER BY tp.effective_from DESC
                LIMIT 1
            )

        WHERE r.recorded_at >= sc.assigned_at

          AND r.recorded_at <= COALESCE(
              sc.released_at,
              sh.expected_delivery_time
          )

          AND r.data_quality = 'GOOD'

        ORDER BY r.recorded_at, r.reading_id
    """

    return conn.execute(query).fetchall()


def generate_normal_reading(rng, min_t, max_t, min_h, max_h):
    """Generate temperature and humidity within policy limits."""

    temp_center = (min_t + max_t) / 2
    humidity_center = (min_h + max_h) / 2

    temp_std = max((max_t - min_t) / 8, 0.1)
    humidity_std = max((max_h - min_h) / 8, 0.5)

    temperature = float(
        np.clip(
            rng.normal(temp_center, temp_std),
            min_t,
            max_t
        )
    )

    humidity = float(
        np.clip(
            rng.normal(humidity_center, humidity_std),
            min_h,
            max_h
        )
    )

    return temperature, humidity


def verify_alignment(conn):
    """Verify database integrity and preserved negative evidence."""

    integrity = conn.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(
            f"Database integrity failed: {integrity}"
        )

    foreign_key_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign key errors: {foreign_key_errors[:5]}"
        )

    suspect_count = conn.execute("""
        SELECT COUNT(*)
        FROM SensorReading
        WHERE data_quality = 'SUSPECT'
    """).fetchone()[0]

    print("Database integrity: PASSED")
    print("Foreign key validation: PASSED")
    print("SUSPECT readings preserved:", suspect_count)


def main():

    print("PRODUCT-SPECIFIC READING ALIGNMENT")
    print("=" * 50)

    rng = np.random.default_rng(RANDOM_SEED)
    conn = get_connection()

    try:
        rows = get_aligned_readings(conn)

        if not rows:
            raise RuntimeError(
                "No eligible GOOD shipment-linked readings found. "
                "Check ShipmentContainer and ThresholdPolicy data."
            )

        updates = []

        for reading in rows:
            (
                reading_id,
                min_t,
                max_t,
                min_h,
                max_h
            ) = reading

            temperature, humidity = generate_normal_reading(
                rng,
                min_t,
                max_t,
                min_h,
                max_h
            )

            updates.append((
                temperature,
                humidity,
                reading_id
            ))

        conn.executemany("""
            UPDATE SensorReading
            SET temperature = ?,
                humidity = ?
            WHERE reading_id = ?
              AND data_quality = 'GOOD'
        """, updates)

        total = conn.execute("""
            SELECT COUNT(*)
            FROM SensorReading
        """).fetchone()[0]

        linked = conn.execute("""
            SELECT COUNT(DISTINCT r.reading_id)
            FROM SensorReading r
            JOIN Sensor s
                ON s.sensor_id = r.sensor_id
            JOIN ShipmentContainer sc
                ON sc.container_id = s.container_id
            JOIN Shipment sh
                ON sh.shipment_id = sc.shipment_id
            WHERE r.recorded_at >= sc.assigned_at
              AND r.recorded_at <= COALESCE(
                  sc.released_at,
                  sh.expected_delivery_time
              )
        """).fetchone()[0]

        updated = len(updates)
        unmatched = total - linked

        verify_alignment(conn)

        conn.commit()

        print("\nALIGNMENT SUMMARY")
        print("-" * 45)
        print(f"Shipment-linked GOOD readings updated: {updated:,}")
        print(f"Total sensor readings: {total:,}")
        print(f"Shipment-linked readings: {linked:,}")
        print(f"Unmatched readings: {unmatched:,}")

        print("\nREADING ALIGNMENT COMPLETED!")

    except Exception as error:
        conn.rollback()
        print("\nALIGNMENT FAILED:", error)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
