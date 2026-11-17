# Insulator Inspection Copilot

> Work in progress. This README will be completed with the architecture, how to run it, and
> evaluation results once those exist. Every number here will come from an evaluation run
> recorded in this repository.

An assistant for powerline insulator inspection: YOLOv8 defect detection on images, a
knowledge base of inspection documents searched with hybrid retrieval (pgvector + PostgreSQL
full-text search), and an LLM that answers questions by calling tools over both.

## Run locally

```bash
docker compose up --build
```

Then open http://localhost:8000/docs.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
docker compose up -d db         # PostgreSQL + pgvector
alembic upgrade head
pytest
```

## Knowledge base and retrieval evaluation

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[ml]"
python scripts/fetch_documents.py                  # public-domain PDFs, SHA-256 verified
python -m inspection_copilot.ingest                # chunk, embed, store in PostgreSQL
python -m inspection_copilot.eval_retrieval --check
python -m inspection_copilot.eval_retrieval        # writes eval/results/retrieval.json
```

Documents (see [data/sources.toml](data/sources.toml)): US Army TM 5-684 *Electrical Exterior
Facilities* and US Bureau of Reclamation FIST volumes 3-18 to 3-28 and 4-1B. All are US federal
government works, which are in the public domain in the US. The PDFs are downloaded, not
stored in this repository.

The question set ([eval/retrieval_questions.jsonl](eval/retrieval_questions.jsonl)) has 53
questions drafted with an AI assistant (Claude) from the documents. Each question has a
verbatim evidence quote; `--check` verifies that every quote occurs in its document on the
stated page. Because questions are written from the text, they favour keyword search; the
`paraphrase` category (questions that avoid the source wording) measures this bias.
