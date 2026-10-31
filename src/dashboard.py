from pathlib import Path
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cold_chain.db"

st.set_page_config(
    page_title="YottaFlex Cold Chain",
    page_icon="❄️",
    layout="wide"
)

st.title("❄️ YottaFlex Cold Chain Control Tower")
st.caption("Shipment Monitoring | Sensor Telemetry | Excursion Management")

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()


def read_sql(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


try:
    shipments = read_sql("""
        SELECT s.shipment_id, s.product_id, p.product_name,
               s.origin, s.destination, s.departure_time,
               s.expected_delivery_time, s.actual_delivery_time,
               s.shipment_status
        FROM Shipment s
        JOIN Product p ON s.product_id = p.product_id
        ORDER BY s.shipment_id
    """)

    products = read_sql("""
        SELECT product_id, product_name, min_temperature,
               max_temperature, min_humidity, max_humidity
        FROM Product ORDER BY product_name
    """)

    excursions = read_sql("""
        SELECT e.excursion_id, e.shipment_id, e.sensor_id,
               e.excursion_type, e.start_time, e.end_time,
               e.duration_minutes, e.observed_min_value,
               e.observed_max_value, e.severity,
               e.excursion_status, e.ground_truth
        FROM Excursion e
        ORDER BY e.start_time DESC
    """)

    issues = read_sql("""
        SELECT issue_id, issue_key, entity_type, entity_id,
               issue_type, evidence, expected_rule,
               ground_truth, detected, detection_note
        FROM DataQualityIssue
        ORDER BY issue_id
    """)

    actions = read_sql("""
        SELECT action_id, excursion_id, action_type,
               description, assigned_to, action_status,
               started_at, completed_at, outcome
        FROM CorrectiveAction
        ORDER BY created_at DESC
    """)

    sensor_status = read_sql("""
        SELECT sensor_status, COUNT(*) AS sensor_count
        FROM Sensor GROUP BY sensor_status
    """)

    route_stops = read_sql("""
        SELECT shipment_id, location_name, planned_arrival_time,
               actual_arrival_time, stop_status
        FROM RouteStop
        WHERE planned_arrival_time IS NOT NULL
          AND actual_arrival_time IS NOT NULL
    """)

except Exception as error:
    st.error("Unable to read project database.")
    st.exception(error)
    st.stop()


# Sidebar filters
st.sidebar.header("Dashboard Filters")

product_names = ["All"] + products["product_name"].dropna().tolist()
selected_product = st.sidebar.selectbox("Select product", product_names)

filtered = shipments.copy()

if selected_product != "All":
    filtered = filtered[filtered["product_name"] == selected_product]

shipment_options = ["All"] + sorted(filtered["shipment_id"].tolist())
selected_shipment = st.sidebar.selectbox("Select shipment", shipment_options)

if selected_shipment != "All":
    filtered = filtered[filtered["shipment_id"] == selected_shipment]

selected_ids = set(filtered["shipment_id"].tolist())

filtered_excursions = excursions[
    excursions["shipment_id"].isin(selected_ids)
].copy()

filtered_issues = issues.copy()

# KPI section
st.subheader("Operational Summary")

total_shipments = len(filtered)
in_transit = filtered["shipment_status"].astype(str).str.lower().eq("in transit").sum()
delivered = filtered["shipment_status"].astype(str).str.lower().eq("delivered").sum()
total_excursions = len(filtered_excursions)
critical = (
    filtered_excursions["severity"].astype(str).str.upper().eq("CRITICAL").sum()
    if not filtered_excursions.empty else 0
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Shipments", f"{total_shipments:,}")
c2.metric("In Transit", f"{in_transit:,}")
c3.metric("Delivered", f"{delivered:,}")
c4.metric("Excursions", f"{total_excursions:,}")
c5.metric("Critical", f"{critical:,}")

st.divider()

# Shipment overview
st.subheader("Shipment Overview")

left, right = st.columns(2)

with left:
    if not filtered.empty:
        status_data = (
            filtered["shipment_status"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Count")
        )
        fig = px.pie(
            status_data,
            names="Status",
            values="Count",
            hole=0.45,
            title="Shipment Status Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No shipments available for this filter.")

with right:
    if not filtered_excursions.empty:
        severity_data = (
            filtered_excursions["severity"]
            .fillna("UNKNOWN")
            .value_counts()
            .rename_axis("Severity")
            .reset_index(name="Count")
        )
        fig = px.bar(
            severity_data,
            x="Severity",
            y="Count",
            title="Excursions by Severity"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No persisted excursions for this selection.")

# Shipment table
st.subheader("Shipment Details")
st.dataframe(filtered, use_container_width=True, hide_index=True)

# Telemetry
st.subheader("Temperature and Humidity Monitoring")

if selected_shipment == "All":
    st.info("Select one shipment from the sidebar to view its sensor readings.")
else:
    telemetry = read_sql("""
        SELECT r.recorded_at, r.temperature, r.humidity,
               r.data_quality, sn.sensor_id
        FROM ShipmentContainer sc
        JOIN Sensor sn ON sn.container_id = sc.container_id
        JOIN SensorReading r ON r.sensor_id = sn.sensor_id
        WHERE sc.shipment_id = ?
          AND r.recorded_at >= sc.assigned_at
          AND (sc.released_at IS NULL OR r.recorded_at <= sc.released_at)
        ORDER BY r.recorded_at
    """, (selected_shipment,))

    if not telemetry.empty:
        telemetry["recorded_at"] = pd.to_datetime(
            telemetry["recorded_at"], errors="coerce"
        )

        good = telemetry[telemetry["data_quality"] == "GOOD"].copy()

        if not good.empty:
            fig = px.line(
                good,
                x="recorded_at",
                y="temperature",
                color="sensor_id",
                title="Temperature Timeline"
            )
            st.plotly_chart(fig, use_container_width=True)

            fig = px.line(
                good,
                x="recorded_at",
                y="humidity",
                color="sensor_id",
                title="Humidity Timeline"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.caption(
            f"Total readings: {len(telemetry):,} | "
            f"GOOD readings: {len(good):,} | "
            f"Non-GOOD readings: {len(telemetry) - len(good):,}"
        )
        st.dataframe(telemetry.tail(100), use_container_width=True, hide_index=True)
    else:
        st.warning("No sensor readings found for this shipment.")

# Excursion history
st.subheader("Excursion History")

if not filtered_excursions.empty:
    st.dataframe(
        filtered_excursions,
        use_container_width=True,
        hide_index=True
    )
    st.caption(
        "Ground-truth test records are included. Review ground_truth "
        "and evidence before treating a record as a real operational event."
    )
else:
    st.info("No excursion records found.")

# Data quality
st.subheader("Data Quality Monitoring")

q1, q2, q3 = st.columns(3)
q1.metric("Quality Issues", len(filtered_issues))
q2.metric(
    "Detected Issues",
    int(filtered_issues["detected"].fillna(0).sum())
)
q3.metric(
    "Ground Truth Issues",
    int(filtered_issues["ground_truth"].fillna(0).sum())
)

if not filtered_issues.empty:
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)

# Sensor health
st.subheader("Sensor Health")

if not sensor_status.empty:
    st.dataframe(sensor_status, use_container_width=True, hide_index=True)

# Route delays
st.subheader("Route Delay Monitoring")

if not route_stops.empty:
    route_stops["planned_arrival_time"] = pd.to_datetime(
        route_stops["planned_arrival_time"], errors="coerce"
    )
    route_stops["actual_arrival_time"] = pd.to_datetime(
        route_stops["actual_arrival_time"], errors="coerce"
    )
    route_stops["delay_minutes"] = (
        route_stops["actual_arrival_time"] -
        route_stops["planned_arrival_time"]
    ).dt.total_seconds() / 60

    valid_delays = route_stops.dropna(subset=["delay_minutes"]).copy()

    if not valid_delays.empty:
        late = int((valid_delays["delay_minutes"] > 0).sum())
        d1, d2 = st.columns(2)
        d1.metric("Late Route Stops", late)
        d2.metric(
            "Median Delay (minutes)",
            f"{valid_delays['delay_minutes'].median():.1f}"
        )
        st.dataframe(valid_delays, use_container_width=True, hide_index=True)
    else:
        st.info("No valid route delay observations.")
else:
    st.info("No route delay observations available.")

# Corrective action workflow
st.subheader("Corrective Action Management")

if excursions.empty:
    st.warning("No persisted excursion is available for corrective action.")
else:
    with st.form("create_corrective_action"):
        excursion_ids = excursions["excursion_id"].dropna().tolist()

        selected_excursion = st.selectbox(
            "Select excursion",
            excursion_ids
        )

        action_type = st.selectbox(
            "Action type",
            [
                "INSPECT_CONTAINER",
                "CHECK_SENSOR",
                "MOVE_TO_BACKUP_STORAGE",
                "QUALITY_REVIEW",
                "CONTACT_CARRIER"
            ]
        )

        description = st.text_area("Action description")
        assigned_to = st.text_input("Assigned to")
        submitted = st.form_submit_button("Create Corrective Action")

    if submitted:
        if not description.strip():
            st.error("Please enter an action description.")
        else:
            now = datetime.now().isoformat(timespec="seconds")
            action_id = "ACT-" + datetime.now().strftime("%Y%m%d%H%M%S%f")

            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO CorrectiveAction (
                        action_id, excursion_id, action_type,
                        description, assigned_to, action_status,
                        started_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?)
                """, (
                    action_id,
                    selected_excursion,
                    action_type,
                    description.strip(),
                    assigned_to.strip() or None,
                    now,
                    now
                ))
                conn.commit()

            st.success(f"Corrective action created: {action_id}")
            st.rerun()

if not actions.empty:
    st.write("Existing Corrective Actions")
    st.dataframe(actions, use_container_width=True, hide_index=True)

    with st.form("update_corrective_action"):
        action_ids = actions["action_id"].dropna().tolist()
        selected_action = st.selectbox("Select action to update", action_ids)

        new_status = st.selectbox(
            "New status",
            ["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
        )

        outcome = st.text_input("Outcome / closure note")
        update_submitted = st.form_submit_button("Update Action")

    if update_submitted:
        completed_at = (
            datetime.now().isoformat(timespec="seconds")
            if new_status == "COMPLETED" else None
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                UPDATE CorrectiveAction
                SET action_status = ?,
                    outcome = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE action_id = ?
            """, (
                new_status,
                outcome.strip() or None,
                completed_at,
                selected_action
            ))
            conn.commit()

        st.success("Corrective action updated.")
        st.rerun()
else:
    st.info("No corrective actions have been created yet.")

# Export
st.subheader("Export Reports")

st.download_button(
    "Download Excursion Report (CSV)",
    filtered_excursions.to_csv(index=False).encode("utf-8"),
    file_name="yottaflex_excursion_report.csv",
    mime="text/csv"
)

st.download_button(
    "Download Data Quality Report (CSV)",
    filtered_issues.to_csv(index=False).encode("utf-8"),
    file_name="yottaflex_data_quality_report.csv",
    mime="text/csv"
)

st.caption(
    "YottaFlex Cold Chain Monitoring Prototype | "
    "Review data-quality evidence before making product-safety decisions."
)
