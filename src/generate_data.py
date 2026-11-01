
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import numpy as np

# ==========================================
# 1. CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "cold_chain.db"

RANDOM_SEED = 20261022
TOTAL_SHIPMENTS = 1000
TOTAL_CONTAINERS = 300
BATCH_SIZE = 10000

CREATED_AT = "2026-10-01T00:00:00"

rng = np.random.default_rng(RANDOM_SEED)


def get_connection():
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}\n"
            "Run: python src/init_db.py"
        )

    connection = sqlite3.connect(DATABASE_FILE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ==========================================
# 2. PRODUCTS
# ==========================================

def generate_products():
    return [
        ("PRD-000001", "Vaccines", "Medicine", 2, 8, 30, 70),
        ("PRD-000002", "Insulin", "Medicine", 2, 8, 30, 60),
        ("PRD-000003", "Frozen Food", "Food", -25, -18, 40, 60),
        ("PRD-000004", "Fresh Fruits", "Food", 2, 10, 85, 95),
        ("PRD-000005", "Dairy Products", "Food", 2, 6, 40, 75),
    ]


def insert_products(connection):
    products = generate_products()

    connection.executemany("""
        INSERT OR IGNORE INTO Product (
            product_id, product_name, product_category,
            min_temperature, max_temperature,
            min_humidity, max_humidity, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (*product, CREATED_AT)
        for product in products
    ])

    print("Products processed:", len(products))


# ==========================================
# 3. CONTAINERS
# ==========================================

def generate_containers():
    return [
        (
            f"CNT-{i:06d}",
            "Refrigerated",
            1000,
            "Litres",
            "Available",
            "2026-09-01",
            CREATED_AT
        )
        for i in range(1, TOTAL_CONTAINERS + 1)
    ]


def insert_containers(connection):
    containers = generate_containers()

    connection.executemany("""
        INSERT OR IGNORE INTO Container (
            container_id, container_type, capacity,
            capacity_unit, container_status,
            last_maintenance_date, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, containers)

    print("Containers processed:", len(containers))


# ==========================================
# 4. SHIPMENTS
# ==========================================

def generate_shipments():
    shipments = []

    product_ids = [
        product[0] for product in generate_products()
    ]

    locations = [
        "Hyderabad",
        "Bengaluru",
        "Chennai",
        "Mumbai",
        "Pune",
        "Delhi",
        "Vijayawada"
    ]

    start_date = datetime(2026, 10, 1)

    for i in range(1, TOTAL_SHIPMENTS + 1):

        departure = start_date + timedelta(
            days=int(rng.integers(0, 26))
        )

        journey_days = int(rng.integers(2, 6))

        expected_delivery = departure + timedelta(
            days=journey_days
        )

        status = str(rng.choice(
            ["Delivered", "In Transit"],
            p=[0.8, 0.2]
        ))

        actual_delivery = None

        if status == "Delivered":
            actual_delivery = expected_delivery + timedelta(
                hours=int(rng.integers(0, 25))
            )

        origin, destination = rng.choice(
            locations,
            size=2,
            replace=False
        )

        shipments.append((
            f"SHP-2026-{i:06d}",
            str(rng.choice(product_ids)),
            str(origin),
            str(destination),
            departure.isoformat(),
            expected_delivery.isoformat(),
            actual_delivery.isoformat() if actual_delivery else None,
            status,
            CREATED_AT
        ))

    return shipments


def insert_shipments(connection):
    shipments = generate_shipments()

    connection.executemany("""
        INSERT OR IGNORE INTO Shipment (
            shipment_id, product_id, origin, destination,
            departure_time, expected_delivery_time,
            actual_delivery_time, shipment_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, shipments)

    print("Shipments processed:", len(shipments))


# ==========================================
# 5. SENSORS
# ==========================================

def generate_sensors():
    sensors = []

    for i in range(1, TOTAL_CONTAINERS + 1):
        sensors.append((
            f"SNS-CNT-{i:06d}-TH",
            f"CNT-{i:06d}",
            "TemperatureHumidity",
            "Celsius/%RH",
            "2026-09-01",
            "2027-03-01",
            "Active",
            CREATED_AT
        ))

    return sensors


def insert_sensors(connection):
    sensors = generate_sensors()

    connection.executemany("""
        INSERT OR IGNORE INTO Sensor (
            sensor_id, container_id, sensor_type,
            measurement_unit, calibration_date,
            calibration_due_date, sensor_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sensors)

    print("Sensors processed:", len(sensors))


# ==========================================
# 6. SENSOR READINGS
# ==========================================

def generate_sensor_readings():
    start_date = datetime(2026, 10, 1)

    for i in range(1, TOTAL_CONTAINERS + 1):

        sensor_id = f"SNS-CNT-{i:06d}-TH"

        journey_days = int(rng.integers(2, 6))

        total_readings = journey_days * 24 * 12

        start_offset = int(rng.integers(0, 26))

        sensor_start = start_date + timedelta(
            days=start_offset
        )

        for j in range(total_readings):

            recorded_at = sensor_start + timedelta(
                minutes=5 * j
            )

            temperature = round(
                float(rng.normal(5.0, 0.7)), 2
            )

            humidity = round(
                float(rng.normal(55.0, 5.0)), 2
            )

            battery = round(
                float(rng.uniform(70, 100)), 2
            )

            signal = round(
                float(rng.uniform(60, 100)), 2
            )

            reading_id = (
                f"RDG-{sensor_id}-"
                f"{recorded_at.strftime('%Y%m%d%H%M')}"
            )

            yield (
                reading_id,
                sensor_id,
                recorded_at.isoformat(),
                temperature,
                humidity,
                battery,
                signal,
                "GOOD"
            )


def insert_sensor_readings(connection):

    batch = []
    total_processed = 0

    sql = """
        INSERT OR IGNORE INTO SensorReading (
            reading_id, sensor_id, recorded_at,
            temperature, humidity, battery_level,
            signal_strength, data_quality
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    for reading in generate_sensor_readings():

        batch.append(reading)

        if len(batch) >= BATCH_SIZE:
            connection.executemany(sql, batch)
            total_processed += len(batch)
            batch.clear()

    if batch:
        connection.executemany(sql, batch)
        total_processed += len(batch)

    print("Sensor readings processed:", total_processed)


# ==========================================
# 7. DATABASE VERIFICATION
# ==========================================

def verify_database(connection):

    print("\nDATABASE VERIFICATION")
    print("=" * 45)

    tables = [
        "Product",
        "Container",
        "Shipment",
        "Sensor",
        "SensorReading"
    ]

    for table in tables:

        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count:,}")

    # Validate expected base dataset counts.
    expected_counts = {
        "Product": 5,
        "Container": TOTAL_CONTAINERS,
        "Shipment": TOTAL_SHIPMENTS,
        "Sensor": TOTAL_CONTAINERS
    }

    for table, expected in expected_counts.items():

        actual = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        if actual != expected:
            raise RuntimeError(
                f"{table} count mismatch. "
                f"Expected {expected}, found {actual}"
            )

    # Validate foreign keys.
    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign key errors: {foreign_key_errors[:5]}"
        )

    # Validate database integrity.
    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(
            f"Database integrity check failed: {integrity}"
        )

    # Validate 5-minute reading intervals.
    interval_errors = connection.execute("""
        WITH reading_intervals AS (
            SELECT
                sensor_id,
                recorded_at,
                LAG(recorded_at) OVER (
                    PARTITION BY sensor_id
                    ORDER BY recorded_at
                ) AS previous_time
            FROM SensorReading
        )
        SELECT COUNT(*)
        FROM reading_intervals
        WHERE previous_time IS NOT NULL
          AND (
              (julianday(recorded_at) -
               julianday(previous_time)) * 1440
          ) < 0
    """).fetchone()[0]

    if interval_errors:
        raise RuntimeError(
            "Invalid sensor reading timestamp order detected."
        )

    print("\nForeign key validation: PASSED")
    print("Database integrity: PASSED")
    print("Reading timestamp order: PASSED")


# ==========================================
# 8. MAIN EXECUTION
# ==========================================

def main():

    print("YottaFlex Cold Chain Data Generator")
    print("=" * 45)
    print("Random seed:", RANDOM_SEED)

    connection = get_connection()

    try:

        insert_products(connection)
        insert_containers(connection)
        insert_shipments(connection)
        insert_sensors(connection)
        # Sensor readings are generated after shipment-container assignments.

        verify_database(connection)

        connection.commit()

        print("\nDATA GENERATION COMPLETED!")

    except Exception as error:

        connection.rollback()

        print("\nDATA GENERATION FAILED")
        print("ERROR:", error)

        raise

    finally:

        connection.close()


if __name__ == "__main__":
    main()

