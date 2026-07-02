"""One-off utility: try candidate Greenhouse slugs / Workday configs and report which work."""
import concurrent.futures

import requests

from fetchers import WORKDAY_HEADERS
from filters import WORKDAY_SEARCH_TEXT

# Greenhouse candidate slugs to try for each failing company.
GREENHOUSE_CANDIDATES = {
    "Notion": ["notion", "notionhq", "notionlabs"],
    "Snowflake": ["snowflakecomputing", "snowflake"],
    "DoorDash": ["doordashusa", "doordash", "doordashcareers"],
    "Plaid": ["plaidinc", "plaid"],
    "Ramp": ["ramp", "rampcom", "rampnetwork"],
    "Rippling": ["rippling", "ripplingats", "ripplingcareers"],
    "HashiCorp": ["hashicorp", "hashicorpcareers"],
    "Confluent": ["confluent", "confluentcareers"],
    "Redis": ["redislabs", "redis", "rediscom"],
    "Retool": ["retool", "retoolcareers"],
    "CrowdStrike": ["crowdstrike", "crowdstrikecareers"],
    "Shopify": ["shopify", "shopifycareers"],
    "Wayfair": ["wayfair", "wayfaircareers"],
    "Zillow": ["zillow", "zillowgroup"],
    "Uber": ["uber", "ubercareers"],
    "Snap": ["snap", "snapinc", "snapchat"],
    "Snyk": ["snyk", "snykcareers"],
    "Linear": ["linear", "linearapp"],
    "Palantir": ["palantir", "palantirtechnologies"],
    "SentinelOne": ["sentinelone", "sentinelonecareers"],
    "Monday.com": ["mondaycom", "monday", "mondaydotcom"],
    "Grab": ["grabtaxi", "grab", "grabcareers"],
    "Redfin": ["redfin", "redfincareers"],
    "Rivian": ["rivian", "rivianautomotive"],
    "Unity": ["unity3d", "unity", "unitytechnologies"],
    "OpenAI": ["openai", "openaicareers"],
    "Cohere": ["cohere", "coherecareers"],
    "Hugging Face": ["huggingface", "huggingfaceinc"],
    "Replit": ["replit", "replitinc"],
    "Supabase": ["supabase", "supabaseinc"],
    "Canva": ["canva", "canvacareers"],
    "Grammarly": ["grammarly", "grammarlycareers"],
    "Deel": ["deel", "deelcareers"],
    "Spotify": ["spotify", "spotifyjobs"],
    "Kraken": ["kraken", "krakendigital", "krakenfx", "payward"],
    "Wise": ["wise", "transferwise", "wiseaccount"],
    "Revolut": ["revolut", "revolutcareers"],
    "Gong": ["gong", "gongio"],
    "Weights & Biases": ["weightsandbiases", "wandb", "wandbai"],
    "Mistral AI": ["mistralai", "mistral"],
    "Perplexity": ["perplexityai", "perplexity"],
    "Zoom": ["zoom", "zoomvideocommunications", "zoominc"],
    "Wix": ["wix", "wixcom"],
    "Freshworks": ["freshworks", "freshworksinc"],
    "Zendesk": ["zendesk", "zendeskcareers"],
    "Miro": ["miro", "mirohq", "realtimeboard"],
    "Loom": ["loom", "useloom"],
    "Benchling": ["benchling", "benchlingcareers"],
    "Klarna": ["klarna", "klarnacareers"],
    "Etsy": ["etsy", "etsycareers"],
    "eBay": ["ebay", "ebayinc"],
    "Expedia": ["expedia", "expediagroup"],
    "Booking.com": ["bookingcom", "booking", "bookingcomcareers"],
    "Opendoor": ["opendoor", "opendoortechnologies"],
    "Procore": ["procore", "procoretechnologies"],
    "Autodesk": ["autodesk", "autodeskcareers"],
    "Dynatrace": ["dynatrace", "dynatracecareers"],
    "Sourcegraph": ["sourcegraph", "sourcegraph91"],
    "1Password": ["1password", "agilebits"],
    "Docusign": ["docusign", "docusigninc"],
    "Box": ["box", "boxinc"],
    "Productboard": ["productboard", "productboardcareers"],
    "FullStory": ["fullstory", "fullstoryinc"],
    "Hinge": ["hinge", "hingeapp"],
    "Bumble": ["bumble", "bumbleinc", "bumblehq"],
    "Tesla": ["tesla", "teslamotors"],
    "Atlassian": ["atlassian", "atlassiancareers"],
    "GitHub": ["github", "githubinc"],
    "Runway": ["runwayml", "runway"],
    "Glean": ["glean", "gleanwork", "askscio"],
    "Faire": ["fairewholesale", "faire", "fairemarketplace"],
    "Aurora": ["aurora", "auroratech", "aurorainnovation"],
    "Cruise": ["getcruise", "cruise", "cruiseautomation"],
}


def try_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException:
        return False, 0
    if r.status_code == 200:
        try:
            return True, len(r.json().get("jobs", []))
        except ValueError:
            return False, 0
    return False, 0


def discover_greenhouse(item):
    name, candidates = item
    for slug in candidates:
        ok, count = try_greenhouse(slug)
        if ok:
            return name, slug, count
    return name, None, 0


def main():
    print("=== GREENHOUSE DISCOVERY ===\n")
    found = {}
    not_found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for name, slug, count in pool.map(discover_greenhouse, GREENHOUSE_CANDIDATES.items()):
            if slug:
                found[name] = slug
                print(f"  OK   {name}: '{slug}' ({count} jobs)")
            else:
                not_found.append(name)
                print(f"  MISS {name}: no working slug")

    print("\n--- FOUND (python dict) ---")
    for name, slug in found.items():
        print(f'    "{name}": "{slug}",')
    print("\n--- NOT FOUND ---")
    print(", ".join(not_found))


if __name__ == "__main__":
    main()
