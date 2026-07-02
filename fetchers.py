import requests
from datetime import datetime

from filters import WORKDAY_SEARCH_TEXT, is_recently_posted

# 5 pages × 20 jobs = 100 raw jobs max per company (fast scan).
MAX_WORKDAY_PAGES = 5
MAX_RAW_JOBS = 100

WORKDAY_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Language": "en-US",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def workday_jobs(company):
    tenant = company["tenant"]
    wd_server = company.get("wd_server", "wd1")
    site = company["site"]
    company_name = company["name"]

    base_url = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
    api = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"
    headers = {
        **WORKDAY_HEADERS,
        "Referer": f"{base_url}/en-US/{site}",
    }

    payload = {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": WORKDAY_SEARCH_TEXT,
    }

    jobs = []
    pages = 0

    while pages < MAX_WORKDAY_PAGES:
        pages += 1

        response = None
        for attempt in range(3):
            try:
                response = requests.post(
                    api, json=payload, headers=headers, timeout=30
                )
                break
            except requests.RequestException as exc:
                if attempt == 2:
                    print(f"[workday] {company_name}: request failed - {exc}")
        if response is None:
            break

        if response.status_code != 200:
            print(
                f"[workday] {company_name}: API returned {response.status_code} "
                f"({api})"
            )
            break

        try:
            data = response.json()
        except ValueError:
            print(f"[workday] {company_name}: invalid JSON response")
            break

        postings = data.get("jobPostings", [])
        if not postings:
            break

        page_jobs = []

        for job in postings:
            bullet_fields = job.get("bulletFields") or []
            job_id = (bullet_fields[0] if bullet_fields else "") + job.get("title", "")
            external_path = job.get("externalPath", "")
            page_jobs.append(
                {
                    "id": job_id,
                    "company": company_name,
                    "title": job.get("title", "Unknown"),
                    "location": job.get("locationsText", "Not specified"),
                    "url": f"{base_url}/en-US/{site}{external_path}",
                    "posted_on": job.get("postedOn", ""),
                    "posted_at": "",
                }
            )

        jobs.extend(page_jobs)

        if not any(is_recently_posted(job) for job in page_jobs):
            break

        if len(jobs) >= MAX_RAW_JOBS:
            break

        if len(postings) < payload["limit"]:
            break

        payload["offset"] += payload["limit"]

    return jobs


def greenhouse_jobs(company):
    board = company["board"]
    company_name = company["name"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as exc:
        print(f"[greenhouse] {company_name}: request failed - {exc}")
        return []

    if response.status_code != 200:
        print(f"[greenhouse] {company_name}: API returned {response.status_code}")
        return []

    data = response.json()
    jobs = []

    for job in data.get("jobs", []):
        location = job.get("location") or {}
        first_published = job.get("first_published", "")
        posted_on = ""
        if first_published:
            try:
                posted_dt = datetime.fromisoformat(first_published)
                posted_on = posted_dt.strftime("%Y-%m-%d")
            except ValueError:
                posted_on = first_published

        jobs.append(
            {
                "id": str(job["id"]),
                "company": company_name,
                "title": job.get("title", "Unknown"),
                "location": location.get("name", "Not specified"),
                "url": job.get("absolute_url", ""),
                "posted_on": posted_on,
                "posted_at": first_published,
            }
        )

    return jobs
