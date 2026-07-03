import html
import re
import time
import requests
from datetime import datetime, timezone

from filters import WORKDAY_SEARCH_TEXT, is_recently_posted

# 5 pages × 20 jobs = 100 raw jobs max per company (fast scan).
MAX_WORKDAY_PAGES = 5
MAX_RAW_JOBS = 100

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_PAGE_SIZE = 25
LINKEDIN_MAX_PAGES = 2  # keep volume low against an unofficial, ToS-restricted endpoint
LINKEDIN_PAGE_DELAY_SECONDS = 2

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


def _xml_field(block, tag):
    match = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.DOTALL)
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith("<![CDATA[") and value.endswith("]]>"):
        value = value[len("<![CDATA["):-len("]]>")]
    # Feed double-escapes entities (e.g. &amp;#39;), so unescape twice.
    return html.unescape(html.unescape(value)).strip()


def successfactors_jobs(company):
    """SAP SuccessFactors career sites expose active postings via a hidden
    Google-for-Jobs XML feed at /sitemap.xml. It has no posting date field
    (only expiration_date), so every job is treated as posted "today" on
    each fetch; id-based dedup in database.py prevents re-notification.
    """
    feed_url = company["feed_url"]
    company_name = company["name"]

    try:
        response = requests.get(
            feed_url,
            headers={"User-Agent": WORKDAY_HEADERS["User-Agent"], "Accept": "application/xml"},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"[successfactors] {company_name}: request failed - {exc}")
        return []

    if response.status_code != 200:
        print(f"[successfactors] {company_name}: feed returned {response.status_code}")
        return []

    now_iso = datetime.now(timezone.utc).isoformat()
    jobs = []

    for block in re.findall(r"<item>(.*?)</item>", response.text, re.DOTALL):
        title = _xml_field(block, "title")
        link = _xml_field(block, "link")
        job_id = _xml_field(block, "id") or _xml_field(block, "guid")
        location = _xml_field(block, "location")

        if not title or not link:
            continue

        jobs.append(
            {
                "id": job_id or link,
                "company": company_name,
                "title": title,
                "location": location or "Not specified",
                "url": link,
                "posted_on": "today",
                "posted_at": now_iso,
            }
        )

    return jobs


def _parse_linkedin_card(card):
    id_match = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', card)
    title_match = re.search(r'<h3 class="base-search-card__title">\s*(.*?)\s*</h3>', card, re.DOTALL)
    company_match = re.search(r'<h4 class="base-search-card__subtitle">.*?>\s*([^<]+?)\s*</a>', card, re.DOTALL)
    location_match = re.search(r'<span class="job-search-card__location">\s*(.*?)\s*</span>', card, re.DOTALL)
    date_match = re.search(r'<time[^>]*datetime="([^"]+)"', card)
    url_match = re.search(r'<a class="base-card__full-link[^"]*"[^>]*href="([^"]+)"', card)

    if not (id_match and title_match and url_match):
        return None

    return {
        "id": f"linkedin-{id_match.group(1)}",
        "company": html.unescape(company_match.group(1)).strip() if company_match else "Unknown",
        "title": html.unescape(title_match.group(1)).strip(),
        "location": html.unescape(location_match.group(1)).strip() if location_match else "Not specified",
        "url": html.unescape(url_match.group(1)).split("?")[0],
        "posted_on": "",
        "posted_at": date_match.group(1) if date_match else "",
    }


def linkedin_jobs(company):
    """LinkedIn has no public jobs API. This hits their unofficial, unauthenticated
    "guest" search endpoint used by the public job search page. It's not sanctioned
    for automated use, so we page shallowly (LINKEDIN_MAX_PAGES) with a delay between
    requests to stay low-volume, and treat any failure/block as a soft skip.
    """
    keywords = company.get("keywords", "")
    location = company.get("location", "India")
    company_label = company["name"]

    jobs = []
    seen_ids = set()

    for page in range(LINKEDIN_MAX_PAGES):
        params = {"keywords": keywords, "location": location, "start": page * LINKEDIN_PAGE_SIZE}
        try:
            response = requests.get(
                LINKEDIN_SEARCH_URL,
                params=params,
                headers={"User-Agent": WORKDAY_HEADERS["User-Agent"]},
                timeout=20,
            )
        except requests.RequestException as exc:
            print(f"[linkedin] {company_label}: request failed - {exc}")
            break

        if response.status_code != 200:
            print(f"[linkedin] {company_label}: search returned {response.status_code}")
            break

        cards = re.findall(r"<li>(.*?)</li>", response.text, re.DOTALL)
        if not cards:
            break

        for card in cards:
            job = _parse_linkedin_card(card)
            if job and job["id"] not in seen_ids:
                seen_ids.add(job["id"])
                jobs.append(job)

        if len(cards) < LINKEDIN_PAGE_SIZE:
            break
        if page < LINKEDIN_MAX_PAGES - 1:
            time.sleep(LINKEDIN_PAGE_DELAY_SECONDS)

    return jobs
