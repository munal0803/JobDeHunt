from companies import companies
from database import delete_excluded_title_jobs, job_exists, save_job
from fetchers import greenhouse_jobs, workday_jobs
from filters import TITLE_EXCLUDE_KEYWORDS, apply_job_pipeline, is_recently_posted


def run():
    removed = delete_excluded_title_jobs(TITLE_EXCLUDE_KEYWORDS)
    if removed:
        print(f"Removed {removed} jobs with excluded title keywords.", flush=True)

    new_jobs = []
    updated = 0

    for company in companies:
        print(f"Checking {company['name']}...", flush=True)

        try:
            if company["type"] == "greenhouse":
                jobs = greenhouse_jobs(company)
            elif company["type"] == "workday":
                jobs = workday_jobs(company)
            else:
                print(f"Unknown company type: {company['type']}")
                continue
        except Exception as exc:
            print(f"  Error while checking {company['name']}: {exc}", flush=True)
            continue

        recent_count = sum(1 for job in jobs if is_recently_posted(job))
        matching_jobs = apply_job_pipeline(jobs)
        print(
            f"  Fetched {len(jobs)} → {recent_count} recent → "
            f"{len(matching_jobs)} final match",
            flush=True,
        )

        for job in matching_jobs:
            is_new = not job_exists(job["id"])
            save_job(job)
            if is_new:
                new_jobs.append(job)
            else:
                updated += 1

    print(f"\nScan complete: {len(new_jobs)} new, {updated} updated in database.")
    print("Open the dashboard: python app.py  →  http://127.0.0.1:5000")


if __name__ == "__main__":
    run()
