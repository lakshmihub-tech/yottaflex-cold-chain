import sqlite3
import os
from datetime import datetime

DB_PATH = "data/cold_chain.db"
OUTPUT_PATH = "reports/validation_report.txt"

os.makedirs("reports", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

report = []
report.append("YOTTAFLEX COLD CHAIN - VALIDATION REPORT")
report.append("=" * 45)
report.append(f"Generated: {datetime.now()}")
report.append("")

cur.execute("PRAGMA integrity_check")
report.append("DATABASE INTEGRITY:")
report.append(str(cur.fetchone()[0]))
report.append("")

cur.execute("PRAGMA foreign_key_check")
fk_errors = cur.fetchall()
report.append("FOREIGN KEY CHECK:")
report.append(f"Violations: {len(fk_errors)}")
for error in fk_errors:
    report.append(str(error))
report.append("")

cur.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""")

report.append("TABLE RECORD COUNTS:")
for (table,) in cur.fetchall():
    count = cur.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]
    report.append(f"{table}: {count}")

report.append("")
report.append("NEGATIVE SCENARIO DETECTION:")

cur.execute("""
    SELECT issue_key, issue_type, ground_truth,
           detected, detection_note
    FROM DataQualityIssue
    ORDER BY issue_key
""")

issues = cur.fetchall()
detected_count = sum(1 for row in issues if row[3] == 1)

for issue in issues:
    report.append(str(issue))

report.append("")
report.append(f"Total scenarios: {len(issues)}")
report.append(f"Detected scenarios: {detected_count}")
report.append(f"Detection rate: {detected_count}/{len(issues)}")

conn.close()

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("\n".join(report))
print(f"\nReport saved: {OUTPUT_PATH}")