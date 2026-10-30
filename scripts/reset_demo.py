"""Clears alerts, sightings and cameras so a demo starts clean. Registered
people (and their photos) are kept.

Usage (from the repository root):
    python scripts/reset_demo.py            # real database
    python scripts/reset_demo.py some.db    # another database file
"""
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/intellitrack.db"
conn = sqlite3.connect(db_path)
for table in ("alerts", "sightings", "cameras"):
    conn.execute(f"DELETE FROM {table}")
conn.commit()
counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
          for t in ("people", "cameras", "sightings", "alerts")}
conn.close()
print(f"cleared {db_path}: {counts}")
