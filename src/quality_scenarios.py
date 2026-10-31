
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cold_chain.db"

NOW = "2026-10-31T00:00:00"


# ==========================================
# 1. DATABASE CONNECTION
# ==========================================

def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# 2. DATA QUALITY ISSUE TABLE
# ==========================================

def create_issue_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS DataQualityIssue (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_key TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            evidence TEXT NOT NULL,
            expected_rule TEXT NOT NULL,
            ground_truth INTEGER NOT NULL DEFAULT 1,
            detected INTEGER NOT NULL DEFAULT 0,
            detection_note TEXT,
            created_at TEXT NOT NULL,

            CHECK (ground_truth IN (0, 1)),
            CHECK (detected IN (0, 1))
        )
    """)


def get_issue(conn, key):
    return conn.execute("""
        SELECT *
        FROM DataQualityIssue
        WHERE issue_key = ?
    """, (key,)).fetchone()


def add_issue(
    conn,
    key,
    entity_type,
    entity_id,
    issue_type,
    evidence,
    expected_rule
):
    conn.execute("""
        INSERT OR IGNORE INTO DataQualityIssue (
            issue_key,
            entity_type,
            entity_id,
            issue_type,
            evidence,
            expected_rule,
            ground_truth,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        key,
        entity_type,
        str(entity_id),
        issue_type,
        json.dumps(evidence),
        expected_rule,
        NOW
    ))


# ==========================================
# 3. SCENARIO 1
# PHYSICALLY IMPOSSIBLE SENSOR READING
# ==========================================

def scenario_impossible_reading(conn):

    if get_issue(conn, "NEG-001"):
        return

    row = conn.execute("""
        SELECT reading_id, temperature, humidity
        FROM SensorReading
        WHERE data_quality = 'GOOD'
        ORDER BY reading_id
        LIMIT 1
    """).fetchone()

    if row is None:
        raise RuntimeError("No GOOD sensor reading available.")

    evidence = {
        "original_temperature": row["temperature"],
        "original_humidity": row["humidity"],
        "injected_temperature": 999.0
    }

    add_issue(
        conn,
        "NEG-001",
        "SensorReading",
        row["reading_id"],
        "PHYSICALLY_IMPOSSIBLE",
        evidence,
        "Temperature must remain within physically plausible limits."
    )

    conn.execute("""
        UPDATE SensorReading
        SET temperature = 999.0,
            data_quality = 'SUSPECT'
        WHERE reading_id = ?
    """, (row["reading_id"],))

    print("Scenario 1: Impossible reading created.")


# ==========================================
# 4. SCENARIO 2
# MISSING SENSOR INTERVAL
# ==========================================

def scenario_missing_interval(conn):

    if get_issue(conn, "NEG-002"):
        return

    rows = conn.execute("""
        SELECT
            sensor_id,
            reading_id,
            recorded_at,
            temperature,
            humidity
        FROM SensorReading
        ORDER BY sensor_id, recorded_at
    """).fetchall()

    chosen = None

    for i in range(len(rows) - 2):

        a = rows[i]
        b = rows[i + 1]
        c = rows[i + 2]

        if not (
            a["sensor_id"] == b["sensor_id"] == c["sensor_id"]
        ):
            continue

        time_a = datetime.fromisoformat(a["recorded_at"])
        time_b = datetime.fromisoformat(b["recorded_at"])
        time_c = datetime.fromisoformat(c["recorded_at"])

        if (
            time_b - time_a == timedelta(minutes=5)
            and time_c - time_b == timedelta(minutes=5)
        ):
            chosen = (a, b, c)
            break

    if chosen is None:
        raise RuntimeError(
            "Could not find three consecutive 5-minute readings."
        )

    a, b, c = chosen

    evidence = {
        "sensor_id": b["sensor_id"],
        "missing_reading_id": b["reading_id"],
        "missing_timestamp": b["recorded_at"],
        "previous_timestamp": a["recorded_at"],
        "next_timestamp": c["recorded_at"],
        "deleted_reading": {
            "temperature": b["temperature"],
            "humidity": b["humidity"]
        }
    }

    add_issue(
        conn,
        "NEG-002",
        "SensorReading",
        b["reading_id"],
        "MISSING_INTERVAL",
        evidence,
        "Sensor readings are expected every 5 minutes."
    )

    conn.execute("""
        DELETE FROM SensorReading
        WHERE reading_id = ?
    """, (b["reading_id"],))

    print("Scenario 2: Missing sensor interval created.")


# ==========================================
# 5. SCENARIO 3
# DELIVERY BEFORE DEPARTURE
# ==========================================

def scenario_early_delivery(conn):

    if get_issue(conn, "NEG-003"):
        return

    row = conn.execute("""
        SELECT
            shipment_id,
            departure_time,
            actual_delivery_time
        FROM Shipment
        WHERE actual_delivery_time IS NOT NULL
        ORDER BY shipment_id
        LIMIT 1
    """).fetchone()

    if row is None:
        raise RuntimeError("No delivered shipment available.")

    departure = datetime.fromisoformat(row["departure_time"])
    bad_time = (departure - timedelta(hours=1)).isoformat()

    evidence = {
        "original_delivery_time": row["actual_delivery_time"],
        "injected_delivery_time": bad_time,
        "departure_time": row["departure_time"]
    }

    add_issue(
        conn,
        "NEG-003",
        "Shipment",
        row["shipment_id"],
        "DELIVERY_BEFORE_DEPARTURE",
        evidence,
        "Delivery cannot occur before shipment departure."
    )

    conn.execute("""
        UPDATE Shipment
        SET actual_delivery_time = ?
        WHERE shipment_id = ?
    """, (bad_time, row["shipment_id"]))

    print("Scenario 3: Invalid delivery timestamp created.")


# ==========================================
# 6. SCENARIO 4
# WRONG PRODUCT THRESHOLD
# ==========================================

def scenario_wrong_policy(conn):

    issue = get_issue(conn, "NEG-004")

    if issue:
        # Existing issue may have been created by the older
        # evidence-only implementation.
        shipment_id = (
            issue["entity_id"]
            if issue["entity_id"].startswith("SHP-")
            else None
        )
    else:
        shipment_id = None

    if shipment_id:
        row = conn.execute("""
            SELECT
                sh.shipment_id,
                sh.product_id,
                sh.departure_time,
                wrong.policy_id AS wrong_policy_id,
                wrong.product_id AS wrong_product_id,
                s.sensor_id
            FROM Shipment sh
            JOIN ShipmentContainer sc
                ON sc.shipment_id = sh.shipment_id
            JOIN Sensor s
                ON s.container_id = sc.container_id
            JOIN ThresholdPolicy wrong
                ON wrong.product_id != sh.product_id
            WHERE sh.shipment_id = ?
            ORDER BY wrong.policy_id
            LIMIT 1
        """, (shipment_id,)).fetchone()
    else:
        row = conn.execute("""
            SELECT
                sh.shipment_id,
                sh.product_id,
                sh.departure_time,
                wrong.policy_id AS wrong_policy_id,
                wrong.product_id AS wrong_product_id,
                s.sensor_id
            FROM Shipment sh
            JOIN ShipmentContainer sc
                ON sc.shipment_id = sh.shipment_id
            JOIN Sensor s
                ON s.container_id = sc.container_id
            JOIN ThresholdPolicy wrong
                ON wrong.product_id != sh.product_id
            ORDER BY sh.shipment_id
            LIMIT 1
        """).fetchone()

    if row is None:
        raise RuntimeError(
            "Could not find shipment and mismatched product policy."
        )

    excursion_id = "EXC-NEG-004"

    start = datetime.fromisoformat(row["departure_time"])
    end = start + timedelta(minutes=5)

    evidence = {
        "shipment_id": row["shipment_id"],
        "shipment_product_id": row["product_id"],
        "applied_policy_id": row["wrong_policy_id"],
        "applied_policy_product_id": row["wrong_product_id"],
        "excursion_id": excursion_id
    }

    # Create an actual excursion using the WRONG product policy.
    existing = conn.execute("""
        SELECT excursion_id
        FROM Excursion
        WHERE excursion_id = ?
    """, (excursion_id,)).fetchone()

    if existing:
        conn.execute("""
            UPDATE Excursion
            SET shipment_id = ?,
                sensor_id = ?,
                policy_id = ?,
                start_time = ?,
                end_time = ?,
                duration_minutes = 5,
                ground_truth = 1
            WHERE excursion_id = ?
        """, (
            row["shipment_id"],
            row["sensor_id"],
            row["wrong_policy_id"],
            start.isoformat(),
            end.isoformat(),
            excursion_id
        ))
    else:
        conn.execute("""
            INSERT INTO Excursion (
                excursion_id,
                shipment_id,
                sensor_id,
                policy_id,
                excursion_type,
                start_time,
                end_time,
                duration_minutes,
                observed_min_value,
                observed_max_value,
                severity,
                excursion_status,
                ground_truth,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            excursion_id,
            row["shipment_id"],
            row["sensor_id"],
            row["wrong_policy_id"],
            "TEMPERATURE",
            start.isoformat(),
            end.isoformat(),
            5,
            9.0,
            12.0,
            "HIGH",
            "OPEN",
            1,
            NOW
        ))

    if issue:
        conn.execute("""
            UPDATE DataQualityIssue
            SET entity_type = 'Excursion',
                entity_id = ?,
                evidence = ?,
                expected_rule = ?
            WHERE issue_key = 'NEG-004'
        """, (
            excursion_id,
            json.dumps(evidence),
            "An excursion must use the threshold policy "
            "belonging to its shipment product."
        ))
    else:
        add_issue(
            conn,
            "NEG-004",
            "Excursion",
            excursion_id,
            "WRONG_PRODUCT_THRESHOLD",
            evidence,
            "An excursion must use the threshold policy "
            "belonging to its shipment product."
        )

    print("Scenario 4: Wrong product policy applied in database.")


# ==========================================
# 7. SCENARIO 5
# EXCURSION DURATION UNDERCOUNT
# ==========================================

def create_or_repair_undercount(conn):

    issue = get_issue(conn, "NEG-005")

    shipment = conn.execute("""
        SELECT
            sh.shipment_id,
            sh.departure_time,
            p.policy_id,
            s.sensor_id
        FROM Shipment sh
        JOIN ThresholdPolicy p
            ON p.product_id = sh.product_id
        JOIN ShipmentContainer sc
            ON sc.shipment_id = sh.shipment_id
        JOIN Sensor s
            ON s.container_id = sc.container_id
        ORDER BY sh.shipment_id
        LIMIT 1
    """).fetchone()

    if shipment is None:
        raise RuntimeError(
            "Could not find shipment, policy and sensor for excursion."
        )

    if issue:
        evidence = json.loads(issue["evidence"])
        excursion_id = str(issue["entity_id"])

        try:
            start = datetime.fromisoformat(evidence["start_time"])
        except (KeyError, ValueError):
            start = datetime.fromisoformat(shipment["departure_time"])
    else:
        excursion_id = "EXC-NEG-005"
        start = datetime.fromisoformat(shipment["departure_time"])

    end = start + timedelta(minutes=40)

    existing = conn.execute("""
        SELECT excursion_id
        FROM Excursion
        WHERE excursion_id = ?
    """, (excursion_id,)).fetchone()

    if existing:
        conn.execute("""
            UPDATE Excursion
            SET start_time = ?,
                end_time = ?,
                duration_minutes = 10,
                ground_truth = 1
            WHERE excursion_id = ?
        """, (
            start.isoformat(),
            end.isoformat(),
            excursion_id
        ))
    else:
        conn.execute("""
            INSERT INTO Excursion (
                excursion_id,
                shipment_id,
                sensor_id,
                policy_id,
                excursion_type,
                start_time,
                end_time,
                duration_minutes,
                observed_min_value,
                observed_max_value,
                severity,
                excursion_status,
                ground_truth,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            excursion_id,
            shipment["shipment_id"],
            shipment["sensor_id"],
            shipment["policy_id"],
            "TEMPERATURE",
            start.isoformat(),
            end.isoformat(),
            10,
            9.0,
            12.0,
            "HIGH",
            "OPEN",
            1,
            NOW
        ))

    evidence = {
        "excursion_id": excursion_id,
        "shipment_id": shipment["shipment_id"],
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "stored_duration_minutes": 10,
        "actual_duration_minutes": 40
    }

    if issue:
        conn.execute("""
            UPDATE DataQualityIssue
            SET entity_type = 'Excursion',
                entity_id = ?,
                evidence = ?,
                detected = 0,
                detection_note = NULL
            WHERE issue_key = 'NEG-005'
        """, (
            excursion_id,
            json.dumps(evidence)
        ))
    else:
        add_issue(
            conn,
            "NEG-005",
            "Excursion",
            excursion_id,
            "EXCURSION_DURATION_UNDERCOUNT",
            evidence,
            "Duration must equal end time minus start time."
        )

    print("Scenario 5: Excursion duration undercount created.")


# ==========================================
# 8. DETECTION ENGINE
# ==========================================

def detect_issues(conn):

    issues = conn.execute("""
        SELECT *
        FROM DataQualityIssue
        WHERE ground_truth = 1
        ORDER BY issue_id
    """).fetchall()

    for issue in issues:

        evidence = json.loads(issue["evidence"])
        issue_type = issue["issue_type"]

        detected = False
        note = "No matching violation detected."

        # ----------------------------------
        # Scenario 1: Impossible reading
        # ----------------------------------

        if issue_type == "PHYSICALLY_IMPOSSIBLE":

            row = conn.execute("""
                SELECT temperature, humidity
                FROM SensorReading
                WHERE reading_id = ?
            """, (issue["entity_id"],)).fetchone()

            detected = bool(
                row and (
                    row["temperature"] is not None
                    and (
                        row["temperature"] < -80
                        or row["temperature"] > 100
                    )
                    or row and (
                        row["humidity"] is not None
                        and (
                            row["humidity"] < 0
                            or row["humidity"] > 100
                        )
                    )
                )
            )

            note = (
                "Physically impossible sensor value detected."
                if detected else
                "No physically impossible sensor value found."
            )

        # ----------------------------------
        # Scenario 2: Missing interval
        # ----------------------------------

        elif issue_type == "MISSING_INTERVAL":

            sensor_id = evidence["sensor_id"]
            missing_at = evidence["missing_timestamp"]

            before = conn.execute("""
                SELECT recorded_at
                FROM SensorReading
                WHERE sensor_id = ?
                  AND recorded_at < ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (sensor_id, missing_at)).fetchone()

            after = conn.execute("""
                SELECT recorded_at
                FROM SensorReading
                WHERE sensor_id = ?
                  AND recorded_at > ?
                ORDER BY recorded_at
                LIMIT 1
            """, (sensor_id, missing_at)).fetchone()

            if before and after:

                gap = (
                    datetime.fromisoformat(after["recorded_at"])
                    - datetime.fromisoformat(before["recorded_at"])
                ).total_seconds() / 60

                detected = gap > 5

                note = (
                    f"Missing sensor interval detected: {gap:.0f} minutes."
                )

            else:
                note = "Could not locate readings around missing timestamp."

        # ----------------------------------
        # Scenario 3: Early delivery
        # ----------------------------------

        elif issue_type == "DELIVERY_BEFORE_DEPARTURE":

            row = conn.execute("""
                SELECT departure_time, actual_delivery_time
                FROM Shipment
                WHERE shipment_id = ?
            """, (issue["entity_id"],)).fetchone()

            detected = bool(
                row
                and row["actual_delivery_time"]
                and datetime.fromisoformat(
                    row["actual_delivery_time"]
                ) < datetime.fromisoformat(
                    row["departure_time"]
                )
            )

            note = (
                "Delivery occurred before shipment departure."
                if detected else
                "Delivery timestamp is valid."
            )

        # ----------------------------------
        # Scenario 4: Wrong product policy
        # ----------------------------------

        elif issue_type == "WRONG_PRODUCT_THRESHOLD":

            excursion_id = str(issue["entity_id"])

            row = conn.execute("""
                SELECT
                    sh.product_id AS shipment_product_id,
                    p.product_id AS policy_product_id
                FROM Excursion e
                JOIN Shipment sh
                    ON sh.shipment_id = e.shipment_id
                JOIN ThresholdPolicy p
                    ON p.policy_id = e.policy_id
                WHERE e.excursion_id = ?
            """, (excursion_id,)).fetchone()

            detected = bool(
                row
                and row["shipment_product_id"]
                != row["policy_product_id"]
            )

            note = (
                "Applied policy belongs to a different product."
                if detected else
                "Applied policy matches shipment product."
            )

        # ----------------------------------
        # Scenario 5: Duration undercount
        # ----------------------------------

        elif issue_type == "EXCURSION_DURATION_UNDERCOUNT":

            excursion_id = str(issue["entity_id"])

            row = conn.execute("""
                SELECT start_time, end_time, duration_minutes
                FROM Excursion
                WHERE excursion_id = ?
            """, (excursion_id,)).fetchone()

            if row and row["end_time"]:

                start = datetime.fromisoformat(row["start_time"])
                end = datetime.fromisoformat(row["end_time"])

                actual_minutes = (
                    end - start
                ).total_seconds() / 60

                stored_minutes = float(row["duration_minutes"])

                detected = (
                    actual_minutes >= 0
                    and abs(actual_minutes - stored_minutes) > 0.01
                )

                note = (
                    f"Stored duration: {stored_minutes:.0f} min; "
                    f"calculated duration: {actual_minutes:.0f} min."
                )

            else:
                note = "Excursion record or end timestamp is missing."

        conn.execute("""
            UPDATE DataQualityIssue
            SET detected = ?,
                detection_note = ?
            WHERE issue_id = ?
        """, (
            int(detected),
            note,
            issue["issue_id"]
        ))


# ==========================================
# 9. VALIDATION REPORT
# ==========================================

def print_validation_report(conn):

    results = conn.execute("""
        SELECT
            issue_key,
            issue_type,
            ground_truth,
            detected,
            detection_note
        FROM DataQualityIssue
        WHERE ground_truth = 1
        ORDER BY issue_key
    """).fetchall()

    print("\n" + "=" * 65)
    print("YOTTAFLEX - NEGATIVE SCENARIO VALIDATION")
    print("=" * 65)

    for row in results:

        status = (
            "DETECTED"
            if row["detected"]
            else "NOT DETECTED"
        )

        print(f"\n{row['issue_key']} - {row['issue_type']}")
        print(f"Status: {status}")
        print(f"Details: {row['detection_note']}")

    total = len(results)
    detected_count = sum(row["detected"] for row in results)

    rate = (
        detected_count / total * 100
        if total else 0
    )

    print("\n" + "-" * 65)
    print(f"Total scenarios: {total}")
    print(f"Detected: {detected_count}")
    print(f"Not detected: {total - detected_count}")
    print(f"Detection rate: {rate:.1f}%")

    if total == 5 and detected_count == 5:
        print("\nALL FIVE NEGATIVE SCENARIOS DETECTED!")
    else:
        print("\nVALIDATION NEEDS INVESTIGATION.")


# ==========================================
# 10. MAIN
# ==========================================

def main():

    conn = connect()

    try:
        create_issue_table(conn)

        scenario_impossible_reading(conn)
        scenario_missing_interval(conn)
        scenario_early_delivery(conn)
        scenario_wrong_policy(conn)
        create_or_repair_undercount(conn)

        detect_issues(conn)

        # Check foreign keys before committing.
        fk_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise RuntimeError(
                f"Foreign key validation failed: {fk_errors[:5]}"
            )

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Database integrity check failed: {integrity}"
            )

        conn.commit()

        print_validation_report(conn)

        print("\nDatabase integrity: PASSED")
        print("Foreign key validation: PASSED")

    except Exception as error:
        conn.rollback()
        print("\nNEGATIVE SCENARIO GENERATION FAILED")
        print("Error:", error)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
