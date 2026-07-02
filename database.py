import sqlite3
from datetime import datetime

DB_PATH = "jobs.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY,
    company TEXT,
    title TEXT,
    location TEXT,
    url TEXT,
    posted_on TEXT,
    saved_at TEXT
)
""")

cursor.execute("PRAGMA table_info(jobs)")
_columns = {row[1] for row in cursor.fetchall()}
if "posted_on" not in _columns:
    cursor.execute("ALTER TABLE jobs ADD COLUMN posted_on TEXT DEFAULT ''")
if "saved_at" not in _columns:
    cursor.execute("ALTER TABLE jobs ADD COLUMN saved_at TEXT DEFAULT ''")
if "applied" not in _columns:
    cursor.execute("ALTER TABLE jobs ADD COLUMN applied INTEGER NOT NULL DEFAULT 0")
if "applied_at" not in _columns:
    cursor.execute("ALTER TABLE jobs ADD COLUMN applied_at TEXT DEFAULT ''")

conn.commit()


def job_exists(job_id):
    cursor.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,))
    return cursor.fetchone() is not None


def count_jobs():
    cursor.execute("SELECT COUNT(*) FROM jobs")
    return cursor.fetchone()[0]


def save_job(job):
    saved_at = datetime.now().isoformat(timespec="seconds")
    cursor.execute(
        """
        INSERT INTO jobs (id, company, title, location, url, posted_on, saved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            company = excluded.company,
            title = excluded.title,
            location = excluded.location,
            url = excluded.url,
            posted_on = excluded.posted_on,
            saved_at = excluded.saved_at
        WHERE applied = 0 OR applied IS NULL
        """,
        (
            job["id"],
            job["company"],
            job["title"],
            job["location"],
            job["url"],
            job.get("posted_on", ""),
            saved_at,
        ),
    )
    conn.commit()


def delete_excluded_title_jobs(keywords):
    if not keywords:
        return 0

    conditions = " OR ".join("LOWER(title) LIKE ?" for _ in keywords)
    params = [f"%{keyword.lower()}%" for keyword in keywords]
    cursor.execute(f"DELETE FROM jobs WHERE {conditions}", params)
    deleted = cursor.rowcount
    conn.commit()
    return deleted


def set_job_applied(job_id, applied):
    applied_at = datetime.now().isoformat(timespec="seconds") if applied else ""
    cursor.execute(
        """
        UPDATE jobs
        SET applied = ?, applied_at = ?
        WHERE id = ?
        """,
        (1 if applied else 0, applied_at, job_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def get_all_jobs():
    cursor.execute(
        """
        SELECT id, company, title, location, url, posted_on, saved_at, applied, applied_at
        FROM jobs
        ORDER BY saved_at DESC, company ASC, title ASC
        """
    )
    rows = []
    for row in cursor.fetchall():
        job = dict(row)
        job["applied"] = bool(job.get("applied"))
        rows.append(job)
    return rows
