"""One-off utility: test every company endpoint and report which ones fail."""
import concurrent.futures

import requests

from companies import companies
from fetchers import WORKDAY_HEADERS
from filters import WORKDAY_SEARCH_TEXT


def check_greenhouse(company):
    board = company["board"]
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    try:
        r = requests.get(url, timeout=20)
    except requests.RequestException as exc:
        return company["name"], "greenhouse", "ERR", str(exc)[:60]
    if r.status_code != 200:
        return company["name"], "greenhouse", r.status_code, board
    count = len(r.json().get("jobs", []))
    return company["name"], "greenhouse", "OK", f"{count} jobs"


def check_workday(company):
    tenant = company["tenant"]
    wd = company.get("wd_server", "wd1")
    site = company["site"]
    base = f"https://{tenant}.{wd}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    headers = {**WORKDAY_HEADERS, "Referer": f"{base}/en-US/{site}"}
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": WORKDAY_SEARCH_TEXT}
    try:
        r = requests.post(api, json=payload, headers=headers, timeout=25)
    except requests.RequestException as exc:
        return company["name"], "workday", "ERR", str(exc)[:60]
    if r.status_code != 200:
        return company["name"], "workday", r.status_code, f"{tenant}/{wd}/{site}"
    try:
        total = r.json().get("total", "?")
    except ValueError:
        return company["name"], "workday", "BADJSON", f"{tenant}/{wd}/{site}"
    return company["name"], "workday", "OK", f"total={total}"


def check(company):
    if company["type"] == "greenhouse":
        return check_greenhouse(company)
    return check_workday(company)


def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for res in pool.map(check, companies):
            results.append(res)

    failures = [r for r in results if r[2] != "OK"]
    print(f"\n{'='*60}")
    print(f"Tested {len(results)} companies — {len(failures)} FAILED\n")
    for name, kind, status, detail in failures:
        print(f"  [{status}] {name} ({kind}) -> {detail}")
    print(f"{'='*60}\n")

    print("FAILED_NAMES=" + ",".join(r[0] for r in failures))


if __name__ == "__main__":
    main()
