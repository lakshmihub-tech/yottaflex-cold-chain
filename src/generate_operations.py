

import sqlite3
import heapq
import random
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "cold_chain.db"

CREATED_AT = "2026-10-01T00:00:00"
RANDOM_SEED = 20261022


def parse_datetime(value, field_name):
    """Convert a database timestamp into datetime safely."""
    if not value:
        raise ValueError(f"Missing required timestamp: {field_name}")

    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid timestamp in {field_name}: {value}"
        ) from error


def generate_threshold_policies(connection):
    products = connection.execute("""
        SELECT product_id, min_temperature, max_temperature,
               min_humidity, max_humidity
        FROM Product
        ORDER BY product_id
    """).fetchall()

    if not products:
        raise RuntimeError("No products found. Generate base data first.")

    policies = []

    for product in products:
        product_id, min_t, max_t, min_h, max_h = product

        policies.append((
            f"POL-{product_id}-V1",
            product_id,
            min_t,
            max_t,
            min_h,
            max_h,
            30,
            "2026-01-01T00:00:00",
            None,
            CREATED_AT
        ))

    connection.executemany("""
        INSERT OR IGNORE INTO ThresholdPolicy (
            policy_id, product_id,
            min_temperature, max_temperature,
            min_humidity, max_humidity,
            max_excursion_minutes,
            effective_from, effective_to, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, policies)

    print("Threshold policies:", len(policies))


def generate_assignments(connection):
    shipments = connection.execute("""
        SELECT shipment_id, departure_time,
               expected_delivery_time, actual_delivery_time
        FROM Shipment
        ORDER BY departure_time, shipment_id
    """).fetchall()

    containers = connection.execute("""
        SELECT container_id
        FROM Container
        ORDER BY container_id
    """).fetchall()

    if not shipments:
        raise RuntimeError("No shipments found.")

    if not containers:
        raise RuntimeError("No containers found.")

    available = [
        (datetime.min, row[0])
        for row in containers
    ]
    heapq.heapify(available)

    assignments = []
    conflicts = 0

    for shipment in shipments:
        shipment_id, departure, expected, actual = shipment

        departure_dt = parse_datetime(
            departure, f"{shipment_id}.departure_time"
        )
        expected_dt = parse_datetime(
            expected, f"{shipment_id}.expected_delivery_time"
        )

        actual_dt = (
            parse_datetime(
                actual, f"{shipment_id}.actual_delivery_time"
            )
            if actual else None
        )

        if expected_dt < departure_dt:
            raise ValueError(
                f"Expected delivery precedes departure: {shipment_id}"
            )

        available_at, container_id = heapq.heappop(available)

        if available_at > departure_dt:
            conflicts += 1

        release_dt = max(
            actual_dt or expected_dt,
            departure_dt
        )

        released_at = (
            release_dt.isoformat() if actual else None
        )

        assignments.append((
            f"ASN-{shipment_id}",
            shipment_id,
            container_id,
            departure_dt.isoformat(),
            released_at
        ))

        heapq.heappush(
            available,
            (release_dt, container_id)
        )

    connection.executemany("""
        INSERT OR IGNORE INTO ShipmentContainer (
            assignment_id, shipment_id, container_id,
            assigned_at, released_at
        ) VALUES (?, ?, ?, ?, ?)
    """, assignments)

    print("Shipment-container assignments:", len(assignments))
    print("Container scheduling conflicts:", conflicts)


# ==========================================
# ASSIGNMENT-BASED SENSOR READINGS
# ==========================================

def generate_assignment_readings(connection):
    """Generate deterministic sensor readings for each shipment."""

    rng = random.Random(RANDOM_SEED)

    assignments = connection.execute("""
        SELECT
            a.assignment_id,
            s.departure_time,
            s.expected_delivery_time,
            s.actual_delivery_time,
            p.min_temperature,
            p.max_temperature,
            p.min_humidity,
            p.max_humidity,
            sn.sensor_id
        FROM ShipmentContainer a
        JOIN Shipment s
            ON s.shipment_id = a.shipment_id
        JOIN Product p
            ON p.product_id = s.product_id
        JOIN Sensor sn
            ON sn.container_id = a.container_id
        ORDER BY a.assigned_at, a.assignment_id
    """).fetchall()

    if not assignments:
        raise RuntimeError(
            "No assignments found. Generate assignments first."
        )

    sql = """
        INSERT OR IGNORE INTO SensorReading (
            reading_id, sensor_id, recorded_at,
            temperature, humidity, battery_level,
            signal_strength, data_quality
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch = []
    total = 0

    for row in assignments:
        (
            assignment_id,
            departure,
            expected,
            actual,
            min_t,
            max_t,
            min_h,
            max_h,
            sensor_id
        ) = row

        start = parse_datetime(
            departure, f"{assignment_id}.departure_time"
        )

        expected_end = parse_datetime(
            expected, f"{assignment_id}.expected_delivery_time"
        )

        actual_end = (
            parse_datetime(
                actual, f"{assignment_id}.actual_delivery_time"
            )
            if actual else None
        )

        # Invalid early delivery must not shorten the trip.
        end = (
            actual_end
            if actual_end and actual_end >= start
            else expected_end
        )

        if end < start:
            raise ValueError(
                f"Invalid shipment window: {assignment_id}"
            )

        temp_mid = (min_t + max_t) / 2
        humidity_mid = (min_h + max_h) / 2

        temp_sd = max((max_t - min_t) / 8, 0.05)
        humidity_sd = max((max_h - min_h) / 8, 0.1)

        current = start

        while current <= end:

            temperature = round(
                max(
                    min_t,
                    min(max_t, rng.gauss(temp_mid, temp_sd))
                ),
                2
            )

            humidity = round(
                max(
                    min_h,
                    min(max_h, rng.gauss(humidity_mid, humidity_sd))
                ),
                2
            )

            battery = round(rng.uniform(70, 100), 2)
            signal = round(rng.uniform(60, 100), 2)

            reading_id = (
                f"RDG-{sensor_id}-"
                f"{current.strftime('%Y%m%d%H%M')}"
            )

            batch.append((
                reading_id,
                sensor_id,
                current.isoformat(),
                temperature,
                humidity,
                battery,
                signal,
                "GOOD"
            ))

            if len(batch) >= 10000:
                connection.executemany(sql, batch)
                total += len(batch)
                batch.clear()

            current += timedelta(minutes=5)

    if batch:
        connection.executemany(sql, batch)
        total += len(batch)

    print("Assignment-based sensor readings:", total)


def generate_route_stops(connection):
    shipments = connection.execute("""
        SELECT shipment_id, origin, destination,
               departure_time, expected_delivery_time,
               actual_delivery_time
        FROM Shipment
        ORDER BY shipment_id
    """).fetchall()

    stops = []

    for shipment in shipments:
        (
            shipment_id,
            origin,
            destination,
            departure,
            expected,
            actual
        ) = shipment

        departure_dt = parse_datetime(
            departure, f"{shipment_id}.departure_time"
        )
        expected_dt = parse_datetime(
            expected, f"{shipment_id}.expected_delivery_time"
        )

        actual_dt = (
            parse_datetime(
                actual, f"{shipment_id}.actual_delivery_time"
            )
            if actual else None
        )

        journey_end = actual_dt or expected_dt

        midpoint = departure_dt + (
            max(journey_end, departure_dt) - departure_dt
        ) / 2

        locations = [
            (1, origin, departure_dt, departure_dt),
            (2, f"{origin} Transit Hub", midpoint, midpoint),
            (3, destination, expected_dt, actual_dt)
        ]

        for sequence, location, planned, actual_time in locations:
            stops.append((
                f"RST-{shipment_id}-{sequence:02d}",
                shipment_id,
                sequence,
                location,
                planned.isoformat(),
                actual_time.isoformat() if actual_time else None,
                (planned + timedelta(minutes=30)).isoformat(),
                (
                    (actual_time + timedelta(minutes=30)).isoformat()
                    if actual_time else None
                ),
                "Completed" if actual_time else "Pending"
            ))

    connection.executemany("""
        INSERT OR IGNORE INTO RouteStop (
            route_stop_id, shipment_id, stop_sequence,
            location_name, planned_arrival_time,
            actual_arrival_time, planned_departure_time,
            actual_departure_time, stop_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stops)

    print("Route stops:", len(stops))


def generate_custody_events(connection):
    shipments = connection.execute("""
        SELECT shipment_id, origin, destination,
               departure_time, actual_delivery_time
        FROM Shipment
        ORDER BY shipment_id
    """).fetchall()

    events = []

    for shipment in shipments:
        shipment_id, origin, destination, departure, actual = shipment

        departure_dt = parse_datetime(
            departure, f"{shipment_id}.departure_time"
        )

        events.append((
            f"CUS-{shipment_id}-001",
            shipment_id,
            "PICKUP",
            "Origin Warehouse",
            origin,
            departure_dt.isoformat(),
            "Shipment collected from origin",
            CREATED_AT
        ))

        if actual:
            actual_dt = parse_datetime(
                actual, f"{shipment_id}.actual_delivery_time"
            )

            events.append((
                f"CUS-{shipment_id}-002",
                shipment_id,
                "DELIVERED",
                "Destination Warehouse",
                destination,
                actual_dt.isoformat(),
                "Shipment delivered to destination",
                CREATED_AT
            ))

    connection.executemany("""
        INSERT OR IGNORE INTO CustodyEvent (
            custody_event_id, shipment_id,
            event_type, handled_by, location,
            event_time, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, events)

    print("Custody events:", len(events))


def verify_operations(connection):
    tables = [
        "ThresholdPolicy",
        "ShipmentContainer",
        "SensorReading",
        "RouteStop",
        "CustodyEvent"
    ]

    print("\nOPERATIONS VERIFICATION")

    for table in tables:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count:,}")

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign key validation failed: {foreign_key_errors[:5]}"
        )

    print("Foreign key validation: PASSED")


def main():
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}"
        )

    connection = sqlite3.connect(DATABASE_FILE)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        generate_threshold_policies(connection)
        generate_assignments(connection)
        generate_assignment_readings(connection)
        generate_route_stops(connection)
        generate_custody_events(connection)

        verify_operations(connection)
        connection.commit()

        print("\nOPERATIONS DATA GENERATED SUCCESSFULLY!")

    except Exception:
        connection.rollback()
        print("\nOPERATIONS GENERATION FAILED. Changes rolled back.")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
