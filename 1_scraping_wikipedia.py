# =================================================================================================
# GUARANTEED FULL-TEXT WIKIPEDIA SCRAPER (OFFICIAL MEDIAWIKI API)
# =================================================================================================

import requests
import os
import json
import pandas as pd
import time

keywords = pd.read_excel("keywords.xlsx")
os.makedirs("datasets", exist_ok=True)

output_file = "datasets/data.txt"
all_data = []

HEADERS = {
    "User-Agent": "Local-RAG-Bot/1.0 (educational project)"
}

def search_wikipedia(query):
    """Find the best Wikipedia page title using official search API."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }

    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = r.json()

    if not data["query"]["search"]:
        return None

    return data["query"]["search"][0]["title"]


def fetch_full_article(title):
    """Fetch full article text using MediaWiki extracts API."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
        "titles": title
    }

    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = r.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None, None

    page = next(iter(pages.values()))
    extract = page.get("extract")

    if not extract:
        return None, None

    page_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return extract, page_url


for _, row in keywords.iterrows():
    query = str(row["Keyword"]).strip()
    if not query:
        continue

    print(f"Searching: {query}")

    try:
        title = search_wikipedia(query)
        if not title:
            print(f"❌ No Wikipedia result for: {query}")
            continue

        raw_text, page_url = fetch_full_article(title)

        if not raw_text or len(raw_text) < 300:
            print(f"⚠️ Article too short even in full text: {title}")
            continue

        all_data.append({
            "url": page_url,
            "title": title,
            "raw_text": raw_text
        })

        print(f"✅ Success: {title} | {len(raw_text)} characters")
        time.sleep(1)

    except Exception as e:
        print(f"❌ Error processing {query}: {e}")

# Write dataset in JSONL format
with open(output_file, "w", encoding="utf-8") as f:
    for item in all_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("\n✅ Wikipedia scraping complete.")
print(f"✅ Total valid articles: {len(all_data)}")
print(f"✅ Output file: {output_file}")
# =================================================================================================