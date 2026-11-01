import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

DB = Path(__file__).resolve().parent.parent / "data" / "cold_chain_test.db"

def detect(conn):
    rows = conn.execute("""
        SELECT s.shipment_id, sn.sensor_id, p.policy_id,
               p.min_temperature, p.max_temperature,
               p.min_humidity, p.max_humidity,
               p.max_excursion_minutes,
               r.recorded_at, r.temperature, r.humidity
        FROM Shipment s
        JOIN ShipmentContainer a ON a.shipment_id=s.shipment_id
        JOIN Sensor sn ON sn.container_id=a.container_id
        JOIN ThresholdPolicy p ON p.product_id=s.product_id
        JOIN SensorReading r ON r.sensor_id=sn.sensor_id
        WHERE p.effective_from <= s.departure_time
          AND (p.effective_to IS NULL OR p.effective_to > s.departure_time)
          AND r.recorded_at >= s.departure_time
          AND r.recorded_at <= COALESCE(s.actual_delivery_time,s.expected_delivery_time)
        ORDER BY s.shipment_id,sn.sensor_id,r.recorded_at
    """).fetchall()

    streams = {}
    for row in rows:
        shipment,sensor,policy,lt,ht,lh,hh,allowed,ts,temp,humidity = row
        for kind,value,low,high in [
            ("TEMPERATURE",temp,lt,ht),("HUMIDITY",humidity,lh,hh)
        ]:
            if value is None or low is None or high is None:
                continue
            key=(shipment,sensor,policy,kind,allowed)
            streams.setdefault(key,[]).append((ts,value, value<low or value>high))

    episodes=[]
    for key, readings in streams.items():
        active=[]
        previous=None
        for ts,value,outside in readings:
            now=datetime.fromisoformat(ts)
            gap=previous is not None and (now-previous).total_seconds()>300
            if gap or not outside:
                if active:
                    episodes.append((key,active))
                    active=[]
            if outside:
                active.append((ts,value))
            previous=now
        if active:
            episodes.append((key,active))

    inserted=0
    for key, readings in episodes:
        shipment,sensor,policy,kind,allowed=key
        start=readings[0][0]
        end=readings[-1][0]
        duration=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).total_seconds()/60+5
        minimum=min(v for _,v in readings)
        maximum=max(v for _,v in readings)
        digest=hashlib.sha1(f"{shipment}|{sensor}|{kind}|{start}".encode()).hexdigest()[:16]
        excursion_id="EXC-AUTO-"+digest
        classification="PROLONGED" if duration>allowed else "BRIEF"
        cur=conn.execute("""
            INSERT OR IGNORE INTO Excursion
            (excursion_id,shipment_id,sensor_id,policy_id,excursion_type,
             start_time,end_time,duration_minutes,observed_min_value,
             observed_max_value,severity,excursion_status,ground_truth,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?, 'HIGH','OPEN',0,datetime('now'))
        """,(excursion_id,shipment,sensor,policy,kind,start,end,duration,minimum,maximum))
        if cur.rowcount:
            conn.execute("""
                INSERT OR IGNORE INTO CorrectiveAction
                (action_id,excursion_id,action_type,description,assigned_to,action_status,created_at)
                VALUES (?,?, 'QUALITY_REVIEW',?,?, 'OPEN',datetime('now'))
            """,("ACT-"+digest,excursion_id,
                 f"{classification} {kind.lower()} excursion; duration {duration:.1f} minutes; limit {allowed} minutes.",
                 "Cold Chain Operations Team"))
            inserted+=1

    conn.commit()
    print("Detected episodes:",len(episodes))
    print("New excursion records:",inserted)

if __name__=="__main__":
    if not DB.exists():
        raise FileNotFoundError(DB)
    with sqlite3.connect(DB) as conn:
        detect(conn)
