"""One-off utility: brute-force common Workday server/site combos for failing tenants."""
import concurrent.futures
import itertools

import requests

from fetchers import WORKDAY_HEADERS
from filters import WORKDAY_SEARCH_TEXT

# tenant candidates per company (some companies use a different tenant slug)
WORKDAY_TENANTS = {
    "ServiceNow": ["servicenow"],
    "Intuit": ["intuit"],
    "AMD": ["amd"],
    "IBM": ["ibm"],
    "Oracle": ["oracle"],
    "SAP": ["sap"],
    "Qualcomm": ["qualcomm"],
    "Texas Instruments": ["texasinstruments", "ti"],
    "Amazon": ["amazon"],
    "Synopsys": ["synopsys"],
    "Siemens": ["siemens"],
    "Honeywell": ["honeywell"],
    "GE": ["ge", "gevernova", "generalelectric"],
}

SERVERS = ["wd1", "wd3", "wd5", "wd103", "wd2", "wd12"]
SITES = [
    "External", "Careers", "External_Career_Site", "External_Careers",
    "ExternalCareerSite", "External_Site", "careers", "Global", "Professional",
    "ExternalSite", "External_Experienced", "jobs",
]


def try_workday(tenant, server, site):
    base = f"https://{tenant}.{server}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    headers = {**WORKDAY_HEADERS, "Referer": f"{base}/en-US/{site}"}
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": WORKDAY_SEARCH_TEXT}
    try:
        r = requests.post(api, json=payload, headers=headers, timeout=12)
    except requests.RequestException:
        return None
    if r.status_code == 200:
        try:
            total = r.json().get("total", 0)
        except ValueError:
            return None
        return (server, site, total)
    return None


def discover(item):
    name, tenants = item
    for tenant in tenants:
        for server, site in itertools.product(SERVERS, SITES):
            res = try_workday(tenant, server, site)
            if res:
                server, site, total = res
                return name, tenant, server, site, total
    return name, None, None, None, 0


def main():
    print("=== WORKDAY DISCOVERY ===\n")
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(discover, it): it[0] for it in WORKDAY_TENANTS.items()}
        for fut in concurrent.futures.as_completed(futures):
            name, tenant, server, site, total = fut.result()
            if tenant:
                found.append((name, tenant, server, site))
                print(f"  OK   {name}: tenant={tenant} {server} site={site} (total={total})")
            else:
                print(f"  MISS {name}")

    print("\n--- FOUND ---")
    for name, tenant, server, site in found:
        print(f'    {{"name": "{name}", "type": "workday", "tenant": "{tenant}", "wd_server": "{server}", "site": "{site}"}},')


if __name__ == "__main__":
    main()
