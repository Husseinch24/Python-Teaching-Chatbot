#################################################################################################################################################################
# 2_chunking_embedding_ingestion.py - Combine all datasets, chunk, embed, and ingest into Chroma
#################################################################################################################################################################

from dotenv import load_dotenv
import os
import json
import glob
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from uuid import uuid4
import shutil
import time

load_dotenv()

###############################   INITIALIZE EMBEDDINGS MODEL  #################################################################################################

embeddings = OllamaEmbeddings(
    model=os.getenv("EMBEDDING_MODEL"),
)

###############################   DELETE CHROMA DB IF EXISTS AND INITIALIZE   ##################################################################################

db_path = os.getenv("DATABASE_LOCATION")
collection_name = os.getenv("COLLECTION_NAME")
dataset_folder = os.getenv("DATASET_STORAGE_FOLDER")

if os.path.exists(db_path):
    try:
        shutil.rmtree(db_path)
    except PermissionError:
        print("⚠️ Chroma DB is currently in use. Please stop Streamlit and try again.")
        exit(1)


vector_store = Chroma(
    collection_name=collection_name,
    embedding_function=embeddings,
    persist_directory=db_path,
)

###############################   INITIALIZE TEXT SPLITTER   ###################################################################################################

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

#################################################################################################################################################################
# Helper: read all JSONL files from datasets/
#################################################################################################################################################################

def process_json_lines(file_path):
    extracted = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            extracted.append(obj)
    return extracted

all_records = []

pattern = os.path.join(dataset_folder, "*.txt")
files = glob.glob(pattern)

print(f"✅ Found {len(files)} dataset file(s) in {dataset_folder}")

for file in files:
    print(f"📄 Loading {file}")
    try:
        records = process_json_lines(file)
        all_records.extend(records)
    except Exception as e:
        print(f"⚠️ Failed to load {file}: {e}")

print(f"✅ Total records loaded: {len(all_records)}")
print("➡️ Starting chunking and ingestion...")

#################################################################################################################################################################
# Chunking, embedding, and ingestion
#################################################################################################################################################################

count_docs = 0

for idx, line in enumerate(all_records, 1):
    url = line.get("url", "N/A")
    title = line.get("title", "")
    raw_text = line.get("raw_text", "")

    if not raw_text:
        continue

    print(f"[{idx}/{len(all_records)}] Ingesting from: {url}")

    texts = text_splitter.create_documents(
        [raw_text],
        metadatas=[{"source": url, "title": title}]
    )

    uuids = [str(uuid4()) for _ in range(len(texts))]
    vector_store.add_documents(documents=texts, ids=uuids)

    count_docs += len(texts)

    # optional throttling on huge corpora
    time.sleep(0.05)

print(f"\n✅ Ingestion complete. Total chunks stored: {count_docs}")
print(f"✅ Chroma DB path: {db_path}")
