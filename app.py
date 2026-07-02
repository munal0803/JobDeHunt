from datetime import datetime

from flask import Flask, jsonify, render_template, request

from database import get_all_jobs, set_job_applied
from filters import (
    LOCATION_KEYWORDS,
    MAX_POSTED_DAYS,
    TITLE_EXCLUDE_KEYWORDS,
    TITLE_KEYWORDS,
    TOP_JOBS_LIMIT,
    has_excluded_title,
    posted_sort_key,
)

app = Flask(__name__)


@app.route("/")
def index():
    jobs = [job for job in get_all_jobs() if not has_excluded_title(job)]
    jobs.sort(key=posted_sort_key)
    open_jobs = [job for job in jobs if not job.get("applied")]
    applied_jobs = [job for job in jobs if job.get("applied")]
    companies = sorted({job["company"] for job in jobs})
    locations = sorted({job["location"] for job in jobs if job.get("location")})
    last_scan = jobs[0]["saved_at"] if jobs else None

    return render_template(
        "index.html",
        open_jobs=open_jobs,
        applied_jobs=applied_jobs,
        jobs=open_jobs,
        companies=companies,
        locations=locations,
        total=len(jobs),
        open_count=len(open_jobs),
        applied_count=len(applied_jobs),
        last_scan=last_scan,
        title_keywords=", ".join(TITLE_KEYWORDS),
        title_exclude_keywords=", ".join(TITLE_EXCLUDE_KEYWORDS),
        location_keywords=", ".join(LOCATION_KEYWORDS),
        max_posted_days=MAX_POSTED_DAYS,
        top_jobs_limit=TOP_JOBS_LIMIT,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@app.route("/api/jobs/applied", methods=["POST"])
def update_applied_status():
    data = request.get_json(silent=True) or {}
    job_id = data.get("id")
    if not job_id:
        return jsonify({"ok": False, "error": "Missing job id"}), 400

    applied = bool(data.get("applied", True))
    updated = set_job_applied(job_id, applied)
    if not updated:
        return jsonify({"ok": False, "error": "Job not found"}), 404

    return jsonify({"ok": True, "id": job_id, "applied": applied})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
