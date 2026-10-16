# =================================================================================================
# 1_docs_scraping.py - Fetch GitHub READMEs (LangChain, Chroma, Ollama) into datasets/data_docs.txt
# =================================================================================================

import requests
import os
import json
import time

HEADERS = {
    "User-Agent": "Local-RAG-Bot/1.0 (educational project)"
}

os.makedirs("datasets", exist_ok=True)
output_file = "datasets/data_docs.txt"

SOURCES = [
    {
        "url": "https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md",
        "title": "LangChain README"
    },
    {
        "url": "https://raw.githubusercontent.com/chroma-core/chroma/main/README.md",
        "title": "Chroma README"
    },
    {
        "url": "https://raw.githubusercontent.com/ollama/ollama/main/README.md",
        "title": "Ollama README"
    },
]

all_data = []

for src in SOURCES:
    print(f"Fetching: {src['title']} from {src['url']}")
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"⚠️ Failed to fetch {src['title']} (status {r.status_code})")
            continue

        text = r.text
        if len(text) < 500:
            print(f"⚠️ Skipping {src['title']} – content too short")
            continue

        all_data.append({
            "url": src["url"],
            "title": src["title"],
            "raw_text": text
        })

        print(f"✅ Success: {src['title']} ({len(text)} characters)")
        time.sleep(1)

    except Exception as e:
        print(f"❌ Error fetching {src['title']}: {e}")

with open(output_file, "w", encoding="utf-8") as f:
    for item in all_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("\n✅ Docs scraping complete.")
print(f"✅ Total documents: {len(all_data)}")
print(f"✅ Output file: {output_file}")
