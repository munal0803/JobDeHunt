"""
Test every company URL, discover fixes for failures, and regenerate companies.py.
Run: python build_validated_companies.py
"""
import concurrent.futures
import json
import re
from pathlib import Path

import requests

from fetchers import WORKDAY_HEADERS

# ── Current list (with known slug fixes) ──────────────────────────────────────
CURRENT = [
    {"name": "Anthropic", "type": "greenhouse", "board": "anthropic"},
    {"name": "Stripe", "type": "greenhouse", "board": "stripe"},
    {"name": "Figma", "type": "greenhouse", "board": "figma"},
    {"name": "Netflix", "type": "workday", "tenant": "netflix", "wd_server": "wd1", "site": "Netflix"},
    {"name": "Microsoft", "type": "workday", "tenant": "microsoft", "wd_server": "wd1", "site": "Careers"},
    {"name": "Citi", "type": "workday", "tenant": "citi", "wd_server": "wd5", "site": "2"},
    {"name": "Visa", "type": "workday", "tenant": "visa", "wd_server": "wd5", "site": "Visa"},
    {"name": "Mastercard", "type": "workday", "tenant": "mastercard", "wd_server": "wd1", "site": "CorporateCareers"},
    {"name": "PayPal", "type": "workday", "tenant": "paypal", "wd_server": "wd1", "site": "jobs"},
    {"name": "Nasdaq", "type": "workday", "tenant": "nasdaq", "wd_server": "wd1", "site": "Global_External_Site"},
    {"name": "BlackRock", "type": "workday", "tenant": "blackrock", "wd_server": "wd1", "site": "BlackRock_Professional"},
    {"name": "Adobe", "type": "workday", "tenant": "adobe", "wd_server": "wd5", "site": "external_experienced"},
    {"name": "Robinhood", "type": "greenhouse", "board": "robinhood"},
    {"name": "Coinbase", "type": "greenhouse", "board": "coinbase"},
    {"name": "Brex", "type": "greenhouse", "board": "brex"},
    {"name": "Affirm", "type": "greenhouse", "board": "affirm"},
    {"name": "Chime", "type": "greenhouse", "board": "chime"},
    {"name": "Airbnb", "type": "greenhouse", "board": "airbnb"},
    {"name": "Dropbox", "type": "greenhouse", "board": "dropbox"},
    {"name": "Discord", "type": "greenhouse", "board": "discord"},
    {"name": "MongoDB", "type": "greenhouse", "board": "mongodb"},
    {"name": "Databricks", "type": "greenhouse", "board": "databricks"},
    {"name": "Twilio", "type": "greenhouse", "board": "twilio"},
    {"name": "Okta", "type": "greenhouse", "board": "okta"},
    {"name": "HubSpot", "type": "greenhouse", "board": "hubspot"},
    {"name": "Pinterest", "type": "greenhouse", "board": "pinterest"},
    {"name": "Reddit", "type": "greenhouse", "board": "reddit"},
    {"name": "Lyft", "type": "greenhouse", "board": "lyft"},
    {"name": "DoorDash", "type": "greenhouse", "board": "doordashusa"},
    {"name": "Instacart", "type": "greenhouse", "board": "instacart"},
    {"name": "Block", "type": "greenhouse", "board": "block"},
    {"name": "Ramp", "type": "greenhouse", "board": "rampnetwork"},
    {"name": "Gusto", "type": "greenhouse", "board": "gusto"},
    {"name": "Asana", "type": "greenhouse", "board": "asana"},
    {"name": "Airtable", "type": "greenhouse", "board": "airtable"},
    {"name": "Cloudflare", "type": "greenhouse", "board": "cloudflare"},
    {"name": "Datadog", "type": "greenhouse", "board": "datadog"},
    {"name": "Elastic", "type": "greenhouse", "board": "elastic"},
    {"name": "Vercel", "type": "greenhouse", "board": "vercel"},
    {"name": "Scale AI", "type": "greenhouse", "board": "scaleai"},
    {"name": "Rubrik", "type": "greenhouse", "board": "rubrik"},
    {"name": "Klaviyo", "type": "greenhouse", "board": "klaviyo"},
    {"name": "Toast", "type": "greenhouse", "board": "toast"},
    {"name": "Duolingo", "type": "greenhouse", "board": "duolingo"},
    {"name": "Roblox", "type": "greenhouse", "board": "roblox"},
    {"name": "Roku", "type": "greenhouse", "board": "roku"},
    {"name": "GitLab", "type": "greenhouse", "board": "gitlab"},
    {"name": "Grafana Labs", "type": "greenhouse", "board": "grafanalabs"},
    {"name": "dbt Labs", "type": "greenhouse", "board": "dbtlabsinc"},
    {"name": "Mercury", "type": "greenhouse", "board": "mercury"},
    {"name": "Anduril", "type": "greenhouse", "board": "andurilindustries"},
    {"name": "Zscaler", "type": "greenhouse", "board": "zscaler"},
    {"name": "Epic Games", "type": "greenhouse", "board": "epicgames"},
    {"name": "Riot Games", "type": "greenhouse", "board": "riotgames"},
    {"name": "Lucid Motors", "type": "greenhouse", "board": "lucidmotors"},
    {"name": "Unity", "type": "greenhouse", "board": "unity3d"},
    {"name": "Postman", "type": "greenhouse", "board": "postman"},
    {"name": "Calendly", "type": "greenhouse", "board": "calendly"},
    {"name": "Webflow", "type": "greenhouse", "board": "webflow"},
    {"name": "Flexport", "type": "greenhouse", "board": "flexport"},
    {"name": "Braze", "type": "greenhouse", "board": "braze"},
    {"name": "Amplitude", "type": "greenhouse", "board": "amplitude"},
    {"name": "Mixpanel", "type": "greenhouse", "board": "mixpanel"},
    {"name": "LaunchDarkly", "type": "greenhouse", "board": "launchdarkly"},
    {"name": "PagerDuty", "type": "greenhouse", "board": "pagerduty"},
    {"name": "Fastly", "type": "greenhouse", "board": "fastly"},
    {"name": "Contentful", "type": "greenhouse", "board": "contentful"},
    {"name": "Squarespace", "type": "greenhouse", "board": "squarespace"},
    {"name": "SoFi", "type": "greenhouse", "board": "sofi"},
    {"name": "Nubank", "type": "greenhouse", "board": "nubank"},
    {"name": "Navan", "type": "greenhouse", "board": "tripactions"},
    {"name": "Gong", "type": "greenhouse", "board": "gongio"},
    {"name": "Sourcegraph", "type": "greenhouse", "board": "sourcegraph91"},
    {"name": "Box", "type": "greenhouse", "board": "boxinc"},
    {"name": "Glean", "type": "greenhouse", "board": "gleanwork"},
    {"name": "Faire", "type": "greenhouse", "board": "faire"},
    {"name": "Aurora", "type": "greenhouse", "board": "aurorainnovation"},
    {"name": "Salesforce", "type": "workday", "tenant": "salesforce", "wd_server": "wd12", "site": "External_Career_Site"},
    {"name": "Cisco", "type": "workday", "tenant": "cisco", "wd_server": "wd5", "site": "Cisco_Careers"},
    {"name": "NVIDIA", "type": "workday", "tenant": "nvidia", "wd_server": "wd5", "site": "NVIDIAExternalCareerSite"},
    {"name": "Dell", "type": "workday", "tenant": "dell", "wd_server": "wd1", "site": "External"},
    {"name": "HP", "type": "workday", "tenant": "hp", "wd_server": "wd5", "site": "ExternalCareerSite"},
    {"name": "Broadcom", "type": "workday", "tenant": "broadcom", "wd_server": "wd1", "site": "External_Career"},
    {"name": "Nike", "type": "workday", "tenant": "nike", "wd_server": "wd1", "site": "nke"},
    {"name": "Fivetran", "type": "greenhouse", "board": "fivetran"},
    {"name": "Intercom", "type": "greenhouse", "board": "intercom"},
    {"name": "Carta", "type": "greenhouse", "board": "carta"},
    {"name": "Checkr", "type": "greenhouse", "board": "checkr"},
    {"name": "Marqeta", "type": "greenhouse", "board": "marqeta"},
    {"name": "New Relic", "type": "greenhouse", "board": "newrelic"},
    {"name": "Wiz", "type": "greenhouse", "board": "wizinc"},
    {"name": "JFrog", "type": "greenhouse", "board": "jfrog"},
    {"name": "Tailscale", "type": "greenhouse", "board": "tailscale"},
    {"name": "Smartsheet", "type": "greenhouse", "board": "smartsheet"},
    {"name": "Pendo", "type": "greenhouse", "board": "pendo"},
    {"name": "Waymo", "type": "greenhouse", "board": "waymo"},
    {"name": "SpaceX", "type": "greenhouse", "board": "spacex"},
    {"name": "Stability AI", "type": "greenhouse", "board": "stabilityai"},
    {"name": "Remote", "type": "greenhouse", "board": "remotecom"},
    {"name": "Verkada", "type": "greenhouse", "board": "verkada"},
    {"name": "Samsara", "type": "greenhouse", "board": "samsara"},
    {"name": "Intel", "type": "workday", "tenant": "intel", "wd_server": "wd1", "site": "External"},
    {"name": "Micron", "type": "workday", "tenant": "micron", "wd_server": "wd1", "site": "External"},
    {"name": "Applied Materials", "type": "workday", "tenant": "amat", "wd_server": "wd1", "site": "External"},
    {"name": "Cadence", "type": "workday", "tenant": "cadence", "wd_server": "wd1", "site": "External_Careers"},
    {"name": "Marvell", "type": "workday", "tenant": "marvell", "wd_server": "wd1", "site": "MarvellCareers"},
]

# ── 300+ extra candidates to test (name, board slug) ────────────────────────
EXTRA_GREENHOUSE = [
    ("Abnormal Security", "abnormalsecurity"), ("Acorns", "acorns"), ("Addepar", "addepar"),
    ("Adyen", "adyen"), ("Airbyte", "airbyte"), ("Aircall", "aircall"),
    ("Alchemy", "alchemy"), ("Allbirds", "allbirds"), ("Alloy", "alloy"),
    ("AlphaSense", "alphasense"), ("Altana", "altana"), ("Amperity", "amperity"),
    ("Anchorage Digital", "anchorage"), ("Andela", "andela"), ("Anaplan", "anaplan"),
    ("Angi", "angi"), ("AppFolio", "appfolio"), ("Appian", "appian"),
    ("AppLovin", "applovin"), ("Arcadia", "arcadia"), ("Arctic Wolf", "arcticwolf"),
    ("Assembled", "assembled"), ("Attentive", "attentive"), ("Aurora Solar", "aurorasolar"),
    ("Automattic", "automattic"), ("Axon", "axon"), ("Axonius", "axonius"),
    ("BambooHR", "bamboohr"), ("Better", "better"), ("BetterUp", "betterup"),
    ("BigCommerce", "bigcommerce"), ("Bill.com", "billcom"), ("Bird", "bird"),
    ("BitGo", "bitgo"), ("Blend", "blend"), ("Blockdaemon", "blockdaemon"),
    ("Bluevine", "bluevine"), ("Bolt", "bolt"), ("Boomi", "boomi"),
    ("Branch", "branch"), ("Bright Machines", "brightmachines"), ("Bumble", "bumble"),
    ("Calm", "calm"), ("Candid", "candid"), ("Capillary", "capillarytech"),
    ("Carbon Health", "carbonhealth"), ("CarGurus", "cargurus"), ("Carvana", "carvana"),
    ("Cedar", "cedar"), ("Celonis", "celonis"), ("Chainalysis", "chainalysis"),
    ("Chainguard", "chainguard"), ("Checkr", "checkr"), ("Chronosphere", "chronosphere"),
    ("Circle", "circle"), ("Clear", "clear"), ("Clearbit", "clearbit"),
    ("ClickUp", "clickup"), ("Cloudera", "cloudera"), ("Cockroach Labs", "cockroachlabs"),
    ("Codecademy", "codecademy"), ("Cohere", "cohere"), ("Collibra", "collibra"),
    ("Color", "color"), ("Commure", "commure"), ("ConductorOne", "conductorone"),
    ("Convoy", "convoy"), ("CoreWeave", "coreweave"), ("Coursera", "coursera"),
    ("Credit Karma", "creditkarma"), ("Crossbeam", "crossbeam"), ("Crunchyroll", "crunchyroll"),
    ("Culture Amp", "cultureamp"), ("Current", "current"), ("Cyera", "cyera"),
    ("Dandy", "dandy"), ("Dashlane", "dashlane"), ("Dataiku", "dataiku"),
    ("DataRobot", "datarobot"), ("Dave", "dave"), ("DeepMind", "deepmind"),
    ("Deliveroo", "deliveroo"), ("Dialpad", "dialpad"), ("Discord", "discord"),
    ("Divvy", "divvy"), ("DocuSign", "docusign"), ("Domo", "domo"),
    ("DraftKings", "draftkings"), ("Drata", "drata"), ("DriveWealth", "drivewealth"),
    ("Dropbox", "dropbox"), ("Duolingo", "duolingo"), ("EarnIn", "earnin"),
    ("Eco", "eco"), ("Edward Jones", "edwardjones"), ("Eightfold", "eightfold"),
    ("Elastic", "elastic"), ("Element Biosciences", "elementbiosciences"),
    ("Embark Trucks", "embarktrucks"), ("Enfusion", "enfusion"), ("Envoy", "envoy"),
    ("Epic Games", "epicgames"), ("Equinix", "equinix"), ("Ethos", "ethos"),
    ("Eventbrite", "eventbrite"), ("Everlaw", "everlaw"), ("Exabeam", "exabeam"),
    ("Expel", "expel"), ("Extend", "extend"), ("F5", "f5"),
    ("Fanatics", "fanatics"), ("Farfetch", "farfetch"), ("Fivetran", "fivetran"),
    ("Flatiron Health", "flatironhealth"), ("Flexport", "flexport"), ("Flipkart", "flipkart"),
    ("FloQast", "floqast"), ("Flywire", "flywire"), ("Formlabs", "formlabs"),
    ("Fortinet", "fortinet"), ("Forward", "forward"), ("Found", "found"),
    ("FreshBooks", "freshbooks"), ("Front", "front"), ("FullStory", "fullstory"),
    ("G2", "g2"), ("Galaxy Digital", "galaxydigital"), ("Gem", "gem"),
    ("Genesys", "genesys"), ("GetYourGuide", "getyourguide"), ("GitLab", "gitlab"),
    ("Glossier", "glossier"), ("GoFundMe", "gofundme"), ("Gopuff", "gopuff"),
    ("Grammarly", "grammarly"), ("Greenhouse", "greenhouse"), ("Gusto", "gusto"),
    ("HackerOne", "hackerone"), ("Handshake", "handshake"), ("Harness", "harness"),
    ("HashiCorp", "hashicorp"), ("Hazel", "hazel"), ("Headspace", "headspace"),
    ("Helion Energy", "helionenergy"), ("Hinge Health", "hingehealth"), ("Hippo", "hippo"),
    ("Honeycomb", "honeycomb"), ("Hopper", "hopper"), ("Housecall Pro", "housecallpro"),
    ("HubSpot", "hubspot"), ("Human Interest", "humaninterest"), ("Huntress", "huntress"),
    ("Imply", "imply"), ("Impossible Foods", "impossiblefoods"), ("InVision", "invision"),
    ("Incorta", "incorta"), ("Indigo", "indigo"), ("InfluxData", "influxdata"),
    ("Instabase", "instabase"), ("Instacart", "instacart"), ("Instawork", "instawork"),
    ("Intercom", "intercom"), ("Invitae", "invitae"), ("Iterable", "iterable"),
    ("Ivanti", "ivanti"), ("Jerry", "jerry"), ("JetBrains", "jetbrains"),
    ("Justworks", "justworks"), ("Kajabi", "kajabi"), ("Kandji", "kandji"),
    ("Klaviyo", "klaviyo"), ("Kong", "kong"), ("Kraken", "kraken"),
    ("Lacework", "lacework"), ("Ladder", "ladder"), ("Lambda", "lambda"),
    ("Lattice", "lattice"), ("Lemonade", "lemonade"), ("LendingClub", "lendingclub"),
    ("Lime", "lime"), ("LinkedIn", "linkedin"), ("Livongo", "livongo"),
    ("LogicMonitor", "logicmonitor"), ("Lucid", "lucid"), ("Luminar", "luminar"),
    ("Lyra Health", "lyrahealth"), ("M1 Finance", "m1finance"), ("Magic Leap", "magicleap"),
    ("Malwarebytes", "malwarebytes"), ("Mapbox", "mapbox"), ("Marqeta", "marqeta"),
    ("MasterClass", "masterclass"), ("Material Security", "materialsecurity"),
    ("Matterport", "matterport"), ("Maven Clinic", "mavenclinic"), ("Medallia", "medallia"),
    ("Medium", "medium"), ("MemSQL", "memsql"), ("Mercury", "mercury"),
    ("Mesh", "mesh"), ("Metabase", "metabase"), ("Miro", "miro"),
    ("Modern Health", "modernhealth"), ("Modern Treasury", "moderntreasury"),
    ("Moloco", "moloco"), ("Monzo", "monzo"), ("Motive", "motive"),
    ("Moveworks", "moveworks"), ("Mural", "mural"), ("Mutiny", "mutiny"),
    ("N26", "n26"), ("NerdWallet", "nerdwallet"), ("Netlify", "netlify"),
    ("New Relic", "newrelic"), ("Nextdoor", "nextdoor"), ("Niantic", "niantic"),
    ("Notion", "notion"), ("Noom", "noom"), ("Nuro", "nuro"),
    ("Nutanix", "nutanix"), ("Observe", "observeinc"), ("Ocrolus", "ocrolus"),
    ("Olive AI", "oliveai"), ("One Medical", "onemedical"), ("OneTrust", "onetrust"),
    ("OpenSea", "opensea"), ("Opendoor", "opendoor"), ("Opendoor", "opendoorlabs"),
    ("Orca Security", "orcasecurity"), ("Oscar Health", "oscar"), ("Outreach", "outreach"),
    ("Overjet", "overjet"), ("Pacaso", "pacaso"), ("Palantir", "palantir"),
    ("Patreon", "patreon"), ("PayJoy", "payjoy"), ("Pearson", "pearson"),
    ("Persona", "persona"), ("Petco", "petco"), ("Pilot", "pilot"),
    ("Pinterest", "pinterest"), ("Plaid", "plaid"), ("Planet Labs", "planetlabs"),
    ("Plaid", "plaidinc"), ("PlayStation", "playstation"), ("Podium", "podium"),
    ("Postman", "postman"), ("Primer", "primer"), ("Procore", "procore"),
    ("Productboard", "productboard"), ("Proofpoint", "proofpoint"), ("PubMatic", "pubmatic"),
    ("Pure Storage", "purestorage"), ("Qualtrics", "qualtrics"), ("Quizlet", "quizlet"),
    ("Ramp", "rampnetwork"), ("Rapid7", "rapid7"), ("Recorded Future", "recordedfuture"),
    ("Reddit", "reddit"), ("Redfin", "redfin"), ("Relativity", "relativity"),
    ("Remitly", "remitly"), ("Render", "render"), ("Rippling", "rippling"),
    ("Rippling", "ripplingcareers"), ("Robinhood", "robinhood"), ("Ro", "ro"),
    ("Roblox", "roblox"), ("Rocket Lab", "rocketlab"), ("Roofstock", "roofstock"),
    ("Rubrik", "rubrik"), ("Runway", "runwayml"), ("Samsara", "samsara"),
    ("Scale AI", "scaleai"), ("SeatGeek", "seatgeek"), ("Segment", "segment"),
    ("SentinelOne", "sentinelone"), ("Sentry", "sentry"), ("ServiceTitan", "servicetitan"),
    ("Shield AI", "shieldai"), ("Shopify", "shopify"), ("Sift", "sift"),
    ("Sigma Computing", "sigmacomputing"), ("SingleStore", "singlestore"),
    ("Skydio", "skydio"), ("Slack", "slack"), ("SmartAsset", "smartasset"),
    ("Smartsheet", "smartsheet"), ("Snap", "snap"), ("Snap", "snapchat"),
    ("Snorkel AI", "snorkelai"), ("Snowflake", "snowflake"), ("Snyk", "snyk"),
    ("Sofi", "sofi"), ("Sonos", "sonos"), ("Sonder", "sonder"),
    ("Spreedly", "spreedly"), ("Sprinklr", "sprinklr"), ("Square", "square"),
    ("Stack Overflow", "stackoverflow"), ("Starburst", "starburstdata"),
    ("Stitch Fix", "stitchfix"), ("StockX", "stockx"), ("Stripe", "stripe"),
    ("StubHub", "stubhub"), ("Sumo Logic", "sumologic"), ("Superhuman", "superhuman"),
    ("SurveyMonkey", "surveymonkey"), ("Synthesia", "synthesia"), ("Taboola", "taboola"),
    ("Tanium", "tanium"), ("TaskRabbit", "taskrabbit"), ("Tenable", "tenable"),
    ("Thumbtack", "thumbtack"), ("Tidal", "tidal"), ("TikTok", "tiktok"),
    ("Tinder", "tinder"), ("Toast", "toast"), ("Tonal", "tonal"),
    ("Trade Desk", "tradedesk"), ("Tradesy", "tradesy"), ("Transfix", "transfix"),
    ("TripActions", "tripactions"), ("Trumid", "trumid"), ("Trunk Club", "trunkclub"),
    ("Turo", "turo"), ("Twilio", "twilio"), ("Twitter", "twitter"),
    ("Udemy", "udemy"), ("UiPath", "uipath"), ("Uniswap", "uniswap"),
    ("Upstart", "upstart"), ("Upwork", "upwork"), ("Valon", "valon"),
    ("Vanta", "vanta"), ("Veeva", "veeva"), ("Vercel", "vercel"),
    ("Verkada", "verkada"), ("Vimeo", "vimeo"), ("Viz", "viz"),
    ("VSCO", "vsco"), ("Watershed", "watershed"), ("Wayfair", "wayfair"),
    ("Wealthfront", "wealthfront"), ("Webflow", "webflow"), ("Weights & Biases", "wandb"),
    ("Wellhub", "wellhub"), ("Whatnot", "whatnot"), ("Whoop", "whoop"),
    ("Wikimedia", "wikimedia"), ("Windsurf", "windsurf"), ("Wish", "wish"),
    ("Wolt", "wolt"), ("Workato", "workato"), ("Workrise", "workrise"),
    ("Writer", "writer"), ("X", "x"), ("Yext", "yext"),
    ("Yieldstreet", "yieldstreet"), ("Yotpo", "yotpo"), ("Zapier", "zapier"),
    ("Zenefits", "zenefits"), ("ZeroFox", "zerofox"), ("Zip", "zip"),
    ("ZipRecruiter", "ziprecruiter"), ("Zocdoc", "zocdoc"), ("Zoox", "zoox"),
    ("Zuora", "zuora"), ("Zynga", "zynga"),
]

EXTRA_WORKDAY = [
    ("JPMorgan Chase", "jpmorganchase", "wd1", "External"),
    ("Goldman Sachs", "goldmansachs", "wd1", "External"),
    ("Morgan Stanley", "morganstanley", "wd1", "External"),
    ("Wells Fargo", "wellsfargo", "wd1", "External"),
    ("Bank of America", "bankofamerica", "wd1", "External"),
    ("Capital One", "capitalone", "wd1", "External"),
    ("American Express", "aexp", "wd1", "External"),
    ("Discover", "discover", "wd1", "External"),
    ("TD Bank", "td", "wd1", "External"),
    ("Barclays", "barclays", "wd3", "External"),
    ("HSBC", "hsbc", "wd3", "External"),
    ("Deutsche Bank", "db", "wd3", "External"),
    ("UBS", "ubs", "wd1", "External"),
    ("BNY Mellon", "bnymellon", "wd1", "External"),
    ("State Street", "statestreet", "wd1", "External"),
    ("Fidelity", "fmr", "wd1", "External"),
    ("Schwab", "schwab", "wd1", "External"),
    ("Workday", "workday", "wd5", "Workday"),
    ("ServiceNow", "servicenow", "wd1", "External"),
    ("Intuit", "intuit", "wd1", "External_Career_Site"),
    ("AMD", "amd", "wd1", "External"),
    ("IBM", "ibm", "wd1", "External"),
    ("Oracle", "oracle", "wd1", "External"),
    ("SAP", "sap", "wd3", "External"),
    ("Qualcomm", "qualcomm", "wd1", "External"),
    ("Texas Instruments", "texasinstruments", "wd1", "External"),
    ("Amazon", "amazon", "wd5", "External"),
    ("Synopsys", "synopsys", "wd1", "External"),
    ("Honeywell", "honeywell", "wd5", "External"),
    ("GE", "ge", "wd5", "External"),
    ("Johnson & Johnson", "jnj", "wd1", "External"),
    ("Pfizer", "pfizer", "wd1", "External"),
    ("Merck", "merck", "wd1", "External"),
    ("Abbott", "abbott", "wd1", "External"),
    ("Medtronic", "medtronic", "wd1", "External"),
    ("Thermo Fisher", "thermofisher", "wd1", "External"),
    ("Boston Scientific", "bostonscientific", "wd1", "External"),
    ("Stryker", "stryker", "wd1", "External"),
    ("Procter & Gamble", "pg", "wd5", "External"),
    ("Unilever", "unilever", "wd3", "External"),
    ("PepsiCo", "pepsico", "wd5", "External"),
    ("Coca-Cola", "cocacola", "wd1", "External"),
    ("General Mills", "generalmills", "wd1", "External"),
    ("Kellogg", "kellogg", "wd1", "External"),
    ("Mondelez", "mondelez", "wd1", "External"),
    ("Nike", "nike", "wd1", "External"),
    ("Adidas", "adidas", "wd1", "External"),
    ("Lululemon", "lululemon", "wd1", "External"),
    ("Under Armour", "underarmour", "wd1", "External"),
    ("Gap", "gapinc", "wd1", "External"),
    ("Target", "target", "wd1", "External"),
    ("Walmart", "walmart", "wd1", "External"),
    ("Costco", "costco", "wd1", "External"),
    ("Home Depot", "homedepot", "wd1", "External"),
    ("Lowe's", "lowes", "wd1", "External"),
    ("Best Buy", "bestbuy", "wd1", "External"),
    ("Marriott", "marriott", "wd1", "External"),
    ("Hilton", "hilton", "wd1", "External"),
    ("Hyatt", "hyatt", "wd1", "External"),
    ("Delta", "delta", "wd1", "External"),
    ("United Airlines", "united", "wd1", "External"),
    ("American Airlines", "aa", "wd1", "External"),
    ("FedEx", "fedex", "wd1", "External"),
    ("UPS", "ups", "wd1", "External"),
    ("Comcast", "comcast", "wd1", "External"),
    ("Verizon", "verizon", "wd1", "External"),
    ("AT&T", "att", "wd1", "External"),
    ("T-Mobile", "tmobile", "wd1", "External"),
    ("Ericsson", "ericsson", "wd1", "External"),
    ("Nokia", "nokia", "wd1", "External"),
    ("Motorola", "motorola", "wd1", "External"),
    ("Lenovo", "lenovo", "wd1", "External"),
    ("Western Digital", "wdc", "wd1", "External"),
    ("Seagate", "seagate", "wd1", "External"),
    ("KLA", "kla", "wd1", "External"),
    ("Lam Research", "lamresearch", "wd1", "External"),
    ("Applied Materials", "amat", "wd1", "External"),
    ("ASML", "asml", "wd1", "External"),
    ("Analog Devices", "analogdevices", "wd1", "External"),
    ("Microchip", "microchip", "wd1", "External"),
    ("NXP", "nxp", "wd1", "External"),
    ("Onsemi", "onsemi", "wd1", "External"),
    ("Skyworks", "skyworks", "wd1", "External"),
    ("Qorvo", "qorvo", "wd1", "External"),
    ("Netflix", "netflix", "wd1", "External"),
    ("Microsoft", "microsoft", "wd1", "External"),
    ("ServiceNow", "servicenow", "wd1", "External"),
    ("Siemens", "siemens", "wd3", "External"),
]

WORKDAY_ALT_SITES = [
    "External", "Careers", "External_Career_Site", "External_Careers",
    "ExternalCareerSite", "jobs", "Global_External_Site", "Professional",
    "External_Site", "en-US/External", "ExternalSite", "Global",
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"})


def test_greenhouse(board):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    try:
        r = SESSION.get(url, timeout=15)
    except requests.RequestException:
        return False, 0
    if r.status_code != 200:
        return False, 0
    try:
        return True, len(r.json().get("jobs", []))
    except ValueError:
        return False, 0


def test_workday(tenant, wd_server, site, search=""):
    base = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    headers = {**WORKDAY_HEADERS, "Referer": f"{base}/en-US/{site}"}
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": search}
    try:
        r = SESSION.post(api, json=payload, headers=headers, timeout=15)
    except requests.RequestException:
        return False
    return r.status_code == 200


def discover_workday(name, tenant, wd_server, site):
    if test_workday(tenant, wd_server, site, ""):
        return {"name": name, "type": "workday", "tenant": tenant, "wd_server": wd_server, "site": site}
    if test_workday(tenant, wd_server, site, "India"):
        return {"name": name, "type": "workday", "tenant": tenant, "wd_server": wd_server, "site": site}
    for alt in WORKDAY_ALT_SITES:
        if alt == site:
            continue
        if test_workday(tenant, wd_server, alt, ""):
            return {"name": name, "type": "workday", "tenant": tenant, "wd_server": wd_server, "site": alt}
    for wd in ["wd1", "wd3", "wd5", "wd12"]:
        if wd == wd_server:
            continue
        for alt in WORKDAY_ALT_SITES[:6]:
            if test_workday(tenant, wd, alt, ""):
                return {"name": name, "type": "workday", "tenant": tenant, "wd_server": wd, "site": alt}
    return None


def validate_entry(entry):
    if entry["type"] == "greenhouse":
        ok, count = test_greenhouse(entry["board"])
        if ok:
            return entry, True, count
        return entry, False, 0
    result = discover_workday(entry["name"], entry["tenant"], entry.get("wd_server", "wd1"), entry["site"])
    if result:
        return result, True, 1
    return entry, False, 0


def company_key(c):
    return c["name"].lower()


def format_entry(c):
    if c["type"] == "greenhouse":
        return f'    {{"name": "{c["name"]}", "type": "greenhouse", "board": "{c["board"]}"}},'
    return (
        f'    {{"name": "{c["name"]}", "type": "workday", '
        f'"tenant": "{c["tenant"]}", "wd_server": "{c["wd_server"]}", "site": "{c["site"]}"}},'
    )


def main():
    candidates = list(CURRENT)
    seen_names = {company_key(c) for c in CURRENT}

    for name, board in EXTRA_GREENHOUSE:
        key = name.lower()
        if key not in seen_names:
            candidates.append({"name": name, "type": "greenhouse", "board": board})
            seen_names.add(key)

    for name, tenant, wd, site in EXTRA_WORKDAY:
        key = name.lower()
        if key not in seen_names:
            candidates.append({"name": name, "type": "workday", "tenant": tenant, "wd_server": wd, "site": site})
            seen_names.add(key)

    print(f"Testing {len(candidates)} candidates...\n")
    validated = []
    failed = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(validate_entry, c): c for c in candidates}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            done += 1
            entry, ok, count = fut.result()
            if ok:
                validated.append(entry)
                print(f"  OK  [{done}/{len(candidates)}] {entry['name']} ({count})")
            else:
                failed.append(entry)
                print(f"  FAIL [{done}/{len(candidates)}] {entry['name']}")
            if done % 50 == 0:
                print(f"  ... progress {done}/{len(candidates)}")

    # Deduplicate by name (keep first validated)
    unique = {}
    for c in validated:
        key = company_key(c)
        if key not in unique:
            unique[key] = c
    final = list(unique.values())
    final.sort(key=lambda c: c["name"].lower())

    print(f"\n{'='*60}")
    print(f"Validated: {len(final)}  |  Failed: {len(failed)}")
    print(f"{'='*60}\n")

    lines = ["companies = ["]
    gh = [c for c in final if c["type"] == "greenhouse"]
    wd = [c for c in final if c["type"] == "workday"]
    if gh:
        lines.append("    # Greenhouse (URL-tested)")
        lines.extend(format_entry(c) for c in gh)
    if wd:
        lines.append("    # Workday (URL-tested)")
        lines.extend(format_entry(c) for c in wd)
    lines.append("]")
    content = "\n".join(lines) + "\n"

    Path("companies.py").write_text(content, encoding="utf-8")
    Path("validation_report.json").write_text(
        json.dumps({"validated": len(final), "failed": len(failed), "failed_names": [f["name"] for f in failed]}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote companies.py with {len(final)} tested companies")
    print(f"Wrote validation_report.json")


if __name__ == "__main__":
    main()
