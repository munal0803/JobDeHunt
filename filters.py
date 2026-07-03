import re
from datetime import datetime, timezone

# Server-side search term sent to Workday so it only returns India jobs
# (drastically reduces how many pages we download per company).
WORKDAY_SEARCH_TEXT = "India"

# Only include jobs posted within this many days (inclusive).
MAX_POSTED_DAYS = 5

# After date filter, keep only this many most-recent jobs before title/location filters.
TOP_JOBS_LIMIT = 100

TITLE_KEYWORDS = [
    "software",
    "associate",
    "engineer",
    "python",
    "c++",
    "data",
    "AI",
    "ML",
    "GenAI",
    "Generative AI",
    "Generative AI Engineer",
]

TITLE_EXCLUDE_KEYWORDS = [
    "manager",
    "lead",
]

LOCATION_KEYWORDS = [
    "india",
    "bangalore",
    "bengaluru",
    "mumbai",
    "delhi",
    "hyderabad",
    "chennai",
    "pune",
    "kolkata",
    "gurgaon",
    "gurugram",
    "noida",
]


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def days_since_posted(job):
    posted_at = job.get("posted_at")
    if posted_at:
        posted_dt = _parse_iso_datetime(posted_at)
        if posted_dt:
            now = datetime.now(posted_dt.tzinfo or timezone.utc)
            if posted_dt.tzinfo is None:
                posted_dt = posted_dt.replace(tzinfo=timezone.utc)
            return (now - posted_dt).days

    posted_on = job.get("posted_on", "")
    if not posted_on:
        return None

    text = posted_on.lower().strip()

    if "today" in text:
        return 0
    if "yesterday" in text:
        return 1

    match = re.search(r"(\d+)\s*days?\s*ago", text)
    if match:
        return int(match.group(1))

    match = re.search(r"posted on\s+(.+)", text, re.IGNORECASE)
    if match:
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                posted_dt = datetime.strptime(match.group(1).strip(), fmt)
                return (datetime.now() - posted_dt).days
            except ValueError:
                continue

    return None


def is_recently_posted(job):
    days_ago = days_since_posted(job)
    if days_ago is None:
        return False
    return days_ago <= MAX_POSTED_DAYS


def _posted_sort_key(job):
    days = days_since_posted(job)
    if days is not None:
        return days

    posted_at = job.get("posted_at")
    if posted_at:
        posted_dt = _parse_iso_datetime(posted_at)
        if posted_dt:
            return days if days is not None else 0

    return 9999


def has_excluded_title(job):
    title = job.get("title", "").lower()
    return any(keyword in title for keyword in TITLE_EXCLUDE_KEYWORDS)


def matches_title_and_location(job):
    if has_excluded_title(job):
        return False

    title = job.get("title", "").lower()
    location = job.get("location", "").lower()

    title_match = any(keyword.lower() in title for keyword in TITLE_KEYWORDS)
    location_match = any(keyword in location for keyword in LOCATION_KEYWORDS)

    return title_match and location_match


def apply_job_pipeline(jobs):
    """Date filter → top N by recency → title/location filter."""
    recent = [job for job in jobs if is_recently_posted(job)]
    recent.sort(key=_posted_sort_key)
    top_recent = recent[:TOP_JOBS_LIMIT]
    return [job for job in top_recent if matches_title_and_location(job)]


def posted_sort_key(job):
    """Lower = more recently posted. Used by dashboard sorting."""
    return _posted_sort_key(job)


def job_matches_filters(job):
    return is_recently_posted(job) and matches_title_and_location(job)
