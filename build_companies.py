"""Validate every company URL and regenerate companies.py with only working entries."""
import concurrent.futures
import json
from pathlib import Path

import requests

from build_candidates import GREENHOUSE_CANDIDATES, WORKDAY_CANDIDATES
from companies import companies as existing_companies
from fetchers import WORKDAY_HEADERS
from filters import WORKDAY_SEARCH_TEXT

OUTPUT = Path("companies.py")
REPORT = Path("company_validation_report.json")
MIN_COMPANIES = 383  # 183 existing + 200 new


def test_greenhouse(board):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException:
        return False, 0
    if r.status_code != 200:
        return False, 0
    try:
        return True, len(r.json().get("jobs", []))
    except ValueError:
        return False, 0


def test_workday(tenant, wd_server, site):
    base = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    headers = {**WORKDAY_HEADERS, "Referer": f"{base}/en-US/{site}"}
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": WORKDAY_SEARCH_TEXT}
    try:
        r = requests.post(api, json=payload, headers=headers, timeout=15)
    except requests.RequestException:
        return False, 0
    if r.status_code != 200:
        return False, 0
    try:
        return True, r.json().get("total", 0)
    except ValueError:
        return False, 0


def company_key(entry):
    return entry["name"].lower()


def entry_to_dict(entry):
    if entry["type"] == "greenhouse":
        return {"name": entry["name"], "type": "greenhouse", "board": entry["board"]}
    return {
        "name": entry["name"],
        "type": "workday",
        "tenant": entry["tenant"],
        "wd_server": entry["wd_server"],
        "site": entry["site"],
    }


def format_entry(entry):
    if entry["type"] == "greenhouse":
        return f'    {{"name": "{entry["name"]}", "type": "greenhouse", "board": "{entry["board"]}"}},'
    return (
        f'    {{"name": "{entry["name"]}", "type": "workday", '
        f'"tenant": "{entry["tenant"]}", "wd_server": "{entry["wd_server"]}", '
        f'"site": "{entry["site"]}"}},'
    )


def probe_existing(company):
    if company["type"] == "greenhouse":
        ok, count = test_greenhouse(company["board"])
        if ok:
            return entry_to_dict(company), None
        return None, {"name": company["name"], "type": "greenhouse", "board": company["board"]}
    ok, count = test_workday(company["tenant"], company.get("wd_server", "wd1"), company["site"])
    if ok:
        return entry_to_dict(company), None
    return None, company


def probe_greenhouse_candidate(item):
    name, board = item
    ok, count = test_greenhouse(board)
    if ok:
        return {"name": name, "type": "greenhouse", "board": board, "jobs": count}
    return None


def probe_workday_candidate(item):
    name, tenant, wd_server, site = item
    ok, count = test_workday(tenant, wd_server, site)
    if ok:
        return {
            "name": name,
            "type": "workday",
            "tenant": tenant,
            "wd_server": wd_server,
            "site": site,
            "jobs": count,
        }
    return None


def write_companies_file(entries):
    lines = ["companies = ["]
    current_section = None
    for entry in entries:
        section = entry["type"]
        if section != current_section:
            label = "Greenhouse" if section == "greenhouse" else "Workday"
            lines.append(f"    # {label}")
            current_section = section
        lines.append(format_entry(entry))
    lines.append("]")
    lines.append("")
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main():
    working = {}
    failed_existing = []

    print(f"Testing {len(existing_companies)} existing companies...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for ok_entry, fail_entry in pool.map(probe_existing, existing_companies):
            if ok_entry:
                working[company_key(ok_entry)] = ok_entry
            elif fail_entry:
                failed_existing.append(fail_entry)

    print(f"  Existing OK: {len(working)}, failed: {len(failed_existing)}")

    # Dedupe candidate lists by (name, board) or (name, tenant, site)
    gh_seen = set()
    gh_unique = []
    for name, board in GREENHOUSE_CANDIDATES:
        key = (name.lower(), board)
        if key not in gh_seen:
            gh_seen.add(key)
            gh_unique.append((name, board))

    wd_seen = set()
    wd_unique = []
    for name, tenant, wd, site in WORKDAY_CANDIDATES:
        key = (name.lower(), tenant, wd, site)
        if key not in wd_seen:
            wd_seen.add(key)
            wd_unique.append((name, tenant, wd, site))

    print(f"Probing {len(gh_unique)} Greenhouse + {len(wd_unique)} Workday candidates...")
    new_found = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        for result in pool.map(probe_greenhouse_candidate, gh_unique):
            if not result:
                continue
            key = company_key(result)
            if key not in working:
                working[key] = {k: v for k, v in result.items() if k != "jobs"}
                new_found += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for result in pool.map(probe_workday_candidate, wd_unique):
            if not result:
                continue
            key = company_key(result)
            if key not in working:
                working[key] = {k: v for k, v in result.items() if k != "jobs"}
                new_found += 1

    entries = sorted(working.values(), key=lambda e: (e["type"], e["name"].lower()))
    gh_count = sum(1 for e in entries if e["type"] == "greenhouse")
    wd_count = sum(1 for e in entries if e["type"] == "workday")

    report = {
        "total": len(entries),
        "greenhouse": gh_count,
        "workday": wd_count,
        "existing_kept": len(working) - new_found,
        "new_added": new_found,
        "existing_failed": len(failed_existing),
        "failed_existing": failed_existing,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_companies_file(entries)

    print(f"\n{'='*60}")
    print(f"VALIDATED COMPANIES: {len(entries)} total")
    print(f"  Greenhouse: {gh_count}")
    print(f"  Workday:    {wd_count}")
    print(f"  New added:  {new_found}")
    print(f"  Removed broken existing: {len(failed_existing)}")
    print(f"Written: {OUTPUT}")
    print(f"Report:  {REPORT}")
    print(f"{'='*60}")

    if len(entries) < MIN_COMPANIES:
        print(f"WARNING: {len(entries)} < target {MIN_COMPANIES}")


if __name__ == "__main__":
    main()
