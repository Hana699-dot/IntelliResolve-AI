import sqlite3
from pathlib import Path
from datetime import datetime
import uuid
import pandas as pd

DB_PATH = Path(__file__).parent / "data" / "incidents.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_team TEXT NOT NULL,
                status TEXT NOT NULL,
                ai_summary TEXT,
                resolution_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            samples = [
                ("INC-1001","Office Wi-Fi keeps disconnecting","Several users in the finance wing report office Wi-Fi disconnections.","Network","High","Network Support","Open","Repeated wireless connectivity reports."),
                ("INC-1002","Unable to connect to office Wi-Fi","My laptop disconnects from the office wireless network every few minutes.","Network","High","Network Support","In Progress","Wireless connectivity issue."),
                ("INC-1003","VPN connection failed","Remote employee cannot establish a VPN connection.","Network","Medium","Network Support","Open","VPN connectivity failure."),
                ("INC-1004","Email login not working","Employee receives an authentication error while signing into email.","Access","High","Identity & Access Team","Open","Email authentication problem."),
                ("INC-1005","Laptop running slowly","System takes several minutes to open applications.","Hardware","Low","Desktop Support","Resolved","Slow endpoint performance.")
            ]
            for s in samples:
                conn.execute("""INSERT INTO incidents
                    (ticket_id,title,description,category,priority,assigned_team,status,ai_summary,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", (*s, now, now))

def create_ticket(title, description, category, priority, assigned_team, status="Open", ai_summary=""):
    ticket_id = f"INC-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute("""INSERT INTO incidents
            (ticket_id,title,description,category,priority,assigned_team,status,ai_summary,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ticket_id,title,description,category,priority,assigned_team,status,ai_summary,now,now))
    return ticket_id

def get_tickets():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM incidents ORDER BY created_at DESC").fetchall()
    return pd.DataFrame([dict(r) for r in rows])

def update_ticket(ticket_id, status, assigned_team, resolution_notes):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute("""UPDATE incidents SET status=?, assigned_team=?, resolution_notes=?, updated_at=?
                        WHERE ticket_id=?""",
                     (status,assigned_team,resolution_notes,now,ticket_id))

def get_ticket_stats():
    df = get_tickets()
    if df.empty:
        return {"total":0,"open":0,"resolved":0,"high":0}
    return {
        "total":len(df),
        "open":int(df["status"].isin(["Open","In Progress","Escalated"]).sum()),
        "resolved":int((df["status"]=="Resolved").sum()),
        "high":int(df["priority"].isin(["High","Critical"]).sum())
    }
