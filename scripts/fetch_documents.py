"""Download the knowledge-base PDFs listed in data/sources.toml into data/raw/.

    python scripts/fetch_documents.py

Each file must match the SHA-256 in the manifest, so everyone (and the evaluation) works on
exactly the same documents. The logic lives in inspection_copilot.ingest.
"""

from inspection_copilot.ingest import fetch_documents

if __name__ == "__main__":
    fetch_documents()
