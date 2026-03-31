import os

BASE_DIR = r"W:\Joseph\Spring 2026\RA MO\antitrust-project"


import requests
import pandas as pd

API_KEY = "r85l8Kr1EId7Jd9nfh7NyywycbIaQ7Hh6eQjvcoJ"

url = "https://api.ftc.gov/v0/hsr-early-termination-notices"

params = {
    "api_key": API_KEY,
    "page[limit]": 100
}

records = []
offset = 0

while True:
    params["page[offset]"] = offset
    res = requests.get(url, params=params)

    if res.status_code != 200:
        print("Error:", res.status_code)
        print(res.text)
        break

    json_data = res.json()
    data = json_data.get("data", [])

    if not data:
        break

    for item in data:
        attr = item.get("attributes", {})

        acquired_entities = attr.get("acquired-entities")

        # Convert acquired_entities into a clean string
        if isinstance(acquired_entities, list):
            acquired_entities = "; ".join(str(x) for x in acquired_entities)
        elif isinstance(acquired_entities, dict):
            acquired_entities = "; ".join(f"{k}: {v}" for k, v in acquired_entities.items())
        elif acquired_entities is None:
            acquired_entities = None
        else:
            acquired_entities = str(acquired_entities)

        records.append({
            "date": attr.get("date"),
            "transaction_number": attr.get("transaction-number"),
            "acquiring_party": attr.get("acquiring-party"),
            "acquired_party": attr.get("acquired-party"),
            "acquired_entities": acquired_entities,
            "title": attr.get("title")
        })

    print(f"Downloaded {len(records)} rows...")
    offset += 100

df = pd.DataFrame(records)

df.to_csv(os.path.join(BASE_DIR, "FTC Early Termination.csv"), index=False, encoding="utf-8-sig")

print("\nDone ✅")
print(df.head())




import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

#################################################
# FIXED PROJECT PATH
#################################################

BASE_DIR = r"W:\Joseph\Spring 2026\RA MO\antitrust-project"

DOJ_ALPHA_FILE = os.path.join(BASE_DIR, "DOJ Alpha Links.csv")
DOJ_CASES_FILE = os.path.join(BASE_DIR, "DOJ Cases.csv")

#################################################
# BLOCK 1: SCRAPE DOJ ALPHA LINKS
#################################################

url = "https://www.justice.gov/atr/antitrust-case-filings-alpha"
headers = {"User-Agent": "Mozilla/5.0"}

res = requests.get(url, headers=headers)
print("Status:", res.status_code)

soup = BeautifulSoup(res.text, "html.parser")

records = []

# collect all DOJ case links from the alphabetical listing
for a in soup.select('a[href^="/atr/case/"], a[href^="/atr/case-document/"]'):
    title = a.get_text(" ", strip=True)
    href = a.get("href")

    if title and href:
        full_link = "https://www.justice.gov" + href if href.startswith("/") else href
        records.append({
            "title": title,
            "link": full_link
        })

df_doj = pd.DataFrame(records).drop_duplicates()

# save block 1 output inside your antitrust project folder
df_doj.to_csv(DOJ_ALPHA_FILE, index=False, encoding="utf-8-sig")

print("Collected", len(df_doj), "cases")
print(df_doj.head(10))
print("Saved alpha links to:", DOJ_ALPHA_FILE)

#################################################
# BLOCK 2: READ DOJ ALPHA LINKS AND SCRAPE DETAILS
#################################################

df_links = pd.read_csv(DOJ_ALPHA_FILE)

records = []

for i, row in df_links.iterrows():
    page_url = row["link"]

    try:
        res = requests.get(page_url, headers=headers, timeout=20)

        if res.status_code != 200:
            print(f"Skip {i}: status {res.status_code}")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text("\n", strip=True)

        record = {
            "source_title": row.get("title", None),
            "link": page_url,
            "case_open_date": None,
            "case_name": None,
            "case_type": None,
            "case_violations": None,
            "industry_codes": None,
            "component": None,
            "case_documents": None,
            "updated_date": None
        }

        lines = [x.strip() for x in text.split("\n") if x.strip()]

        def get_value(label):
            for j, line in enumerate(lines):
                if line == label and j + 1 < len(lines):
                    return lines[j + 1]
            return None

        record["case_open_date"] = get_value("Case Open Date")
        record["case_name"] = get_value("Case Name")
        record["case_type"] = get_value("Case Type")
        record["industry_codes"] = get_value("Industry Code(s)")
        record["component"] = get_value("Component")

        # violations: may have multiple lines until next label
        if "Case Violation(s)" in lines:
            j = lines.index("Case Violation(s)") + 1
            vals = []
            stop_labels = {
                "Industry Code(s)", "Component", "Case Document",
                "Updated", "Case Open Date", "Case Name", "Case Type"
            }
            while j < len(lines) and lines[j] not in stop_labels:
                vals.append(lines[j])
                j += 1
            record["case_violations"] = " | ".join(vals) if vals else None

        # documents: may have multiple lines until next label
        if "Case Document" in lines:
            j = lines.index("Case Document") + 1
            vals = []
            stop_labels = {
                "Updated", "Case Open Date", "Case Name", "Case Type",
                "Case Violation(s)", "Industry Code(s)", "Component"
            }
            while j < len(lines) and lines[j] not in stop_labels:
                vals.append(lines[j])
                j += 1
            record["case_documents"] = " | ".join(vals) if vals else None

        # updated date
        for line in lines:
            if line.startswith("Updated "):
                record["updated_date"] = line.replace("Updated ", "").strip()
                break

        records.append(record)

        if (i + 1) % 25 == 0:
            print(f"Done {i+1} pages")

        time.sleep(0.5)

    except Exception as e:
        print(f"Error on row {i}: {page_url} -> {e}")

df_out = pd.DataFrame(records)

# save final DOJ output inside the same project folder
df_out.to_csv(DOJ_CASES_FILE, index=False, encoding="utf-8-sig")

print("Done")
print(df_out.head())
print("Saved DOJ details to:", DOJ_CASES_FILE)









import requests

import pandas as pd
from bs4 import BeautifulSoup
import time
import os

# FIXED PATH
BASE_DIR = r"W:\Joseph\Spring 2026\RA MO\antitrust-project"

# Base URL
base_url = "https://www.ftc.gov/legal-library/browse/cases-proceedings"

# Query parameters
params = {
    "sort_by": "field_date",
    "items_per_page": 20,
    "field_mission[30]": 30,
    "field_mission[29]": 29,
    "field_mission[31]": 31,
    "search": "",
    "field_competition_topics": 708,
    "field_consumer_protection_topics": "All",
    "field_federal_court": "All",
    "field_industry": "All",
    "field_case_status": "All",
    "field_enforcement_type": "All",
    "search_matter_number": "",
    "search_civil_action_number": "",
    "start_date": "",
    "end_date": "",
    "page": 0
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

base = "https://www.ftc.gov"

invalid_titles = {
    "Cases and Proceedings",
    "Adjudicative Proceedings",
    "Commissioner Statements"
}

invalid_slug_endings = {
    "/adjudicative-proceedings",
    "/commissioner-statements",
    "/banned-debt-collectors",
    "/banned-debt-and-mortgage-relief-providers"
}

records = []
seen_links = set()

page_num = 0

while True:
    params["page"] = page_num
    print(f"Scraping page {page_num + 1}...")

    response = requests.get(base_url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("div.views-row")

    if not rows:
        print("No more rows found. Stopping.")
        break

    previous_count = len(records)

    for row in rows:
        links = row.select("a[href]")

        case_link = None
        case_title = None

        for a in links:
            title = a.get_text(" ", strip=True)
            href = a.get("href", "").strip()

            if not title or not href:
                continue

            full_link = base + href if href.startswith("/") else href

            if "/legal-library/browse/cases-proceedings/" not in full_link:
                continue
            if "/public-statements/" in full_link:
                continue
            if any(full_link.endswith(x) for x in invalid_slug_endings):
                continue
            if title in invalid_titles:
                continue

            case_link = full_link
            case_title = title
            break

        if not case_link or not case_title:
            continue

        if case_link in seen_links:
            continue
        seen_links.add(case_link)

        texts = [t.strip() for t in row.stripped_strings if t.strip()]

        metadata_labels = [
            "Type of Action",
            "Last Updated",
            "FTC Matter/File Number",
            "Docket Number",
            "Case Status"
        ]

        summary_parts = []

        try:
            title_index = texts.index(case_title)
        except ValueError:
            title_index = -1

        if title_index != -1:
            for t in texts[title_index + 1:]:
                if t in invalid_titles:
                    continue
                if t in metadata_labels:
                    break
                summary_parts.append(t)

        summary = " ".join(summary_parts).strip() if summary_parts else None

        meta = {
            "type_of_action": None,
            "last_updated": None,
            "ftc_matter_file_number": None,
            "docket_number": None,
            "case_status": None
        }

        label_map = {
            "Type of Action": "type_of_action",
            "Last Updated": "last_updated",
            "FTC Matter/File Number": "ftc_matter_file_number",
            "Docket Number": "docket_number",
            "Case Status": "case_status"
        }

        for i, t in enumerate(texts):
            if t in label_map and i + 1 < len(texts):
                meta[label_map[t]] = texts[i + 1]

        records.append({
            "title": case_title,
            "link": case_link,
            "summary": summary,
            "type_of_action": meta["type_of_action"],
            "last_updated": meta["last_updated"],
            "ftc_matter_file_number": meta["ftc_matter_file_number"],
            "docket_number": meta["docket_number"],
            "case_status": meta["case_status"]
        })

    if len(records) == previous_count:
        print("No new case records found. Stopping.")
        break

    page_num += 1
    time.sleep(1)

df = pd.DataFrame(records)
df["last_updated_local"] = pd.Timestamp.now()

# SAVE IN YOUR PROJECT FOLDER WITH YOUR EXACT NAME
df.to_csv(os.path.join(BASE_DIR, "FTC Cases and Proceedings.csv"),
          index=False,
          encoding="utf-8-sig")

print("\nDone ✅")
print(df.head(20))


print(f"\nTotal cases scraped: {len(df)}")
