import sqlite3
import csv
import os

DB_PATH = "data/cold_chain.db"
OUTPUT_PATH = "reports/ground_truth.csv"

os.makedirs("reports", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT issue_key, entity_type, entity_id, issue_type,
           evidence, expected_rule, ground_truth,
           detected, detection_note
    FROM DataQualityIssue
    ORDER BY issue_key
""")

rows = cursor.fetchall()
columns = [description[0] for description in cursor.description]

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(columns)
    writer.writerows(rows)

conn.close()

print(f"Exported {len(rows)} ground-truth records.")
print(f"File created: {OUTPUT_PATH}")