# Insulator Inspection Copilot

[![CI](https://github.com/tejachirravuri/insulator-inspection-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/tejachirravuri/insulator-inspection-copilot/actions/workflows/ci.yml)

An AI assistant for **powerline insulator inspection**. YOLOv8 models find insulators in drone
images, a vision LLM gives a second opinion on their condition and flags uncertain cases for a
human, and a tool-calling agent answers questions from the inspection database and from
maintenance manuals, with citations. Built with FastAPI, PostgreSQL + pgvector, Claude, Docker,
GitHub Actions and Azure.

The detectors are the YOLOv8n / YOLOv8s models from my master's thesis on dynamic model
switching for real-time UAV insulator inspection (TU Chemnitz).

![Agent answer with citations and tool trace](docs/images/agent_chat_answer.png)

*A real answer from the agent: it queried the inspection database (which detections are flagged
and why), searched the manuals, cited the passages `[S1]`, `[S4]`, and shows its tool calls,
tokens and cost (here 3 tool calls, 12.9k tokens, $0.069).*

## What it does

1. **Detect** insulators with YOLOv8. *Auto* mode runs the fast YOLOv8n first and switches to
   the accurate YOLOv8s only when the fast result is uncertain (the thesis idea in miniature).
2. **Second opinion:** Claude looks at the detected crops and returns, per insulator, a
   condition (glaze burn, broken shed, contamination, ...), a severity and a
   `needs_human_review` flag, as schema-validated JSON. Unclear crops are flagged, not guessed.
3. **Ask:** an agent with five tools (manual search, inspections, statistics, review) answers
   questions; numbers come from SQL, manual statements carry `[S#]` citations.
4. **Report:** generates a Markdown inspection report with findings, actions and citations.

## Architecture

```mermaid
flowchart LR
  UI[Web UI] -->|REST| API[FastAPI, async]
  API --> DET[YOLOv8n / YOLOv8s<br/>auto switching]
  API --> VIS[Claude vision<br/>second opinion]
  API --> AG[Agent loop<br/>Claude + 5 tools]
  AG --> RET[Hybrid retrieval<br/>vector + keyword, RRF]
  RET --> PG[(PostgreSQL<br/>pgvector + full-text)]
  API --> PG
  ING[Ingestion<br/>PDF → chunks → E5 embeddings] --> PG
```

One PostgreSQL database holds the manuals (text, `vector(384)` embeddings with an HNSW index,
a generated `tsvector` with a GIN index), the images, detections and reviews.
Design decisions and their reasons: [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).

## Results

All numbers below come from runs in this repository; single runs on one machine unless stated.

**Retrieval** (53 questions with verbatim evidence quotes, 931 chunks, top 10 per method;
[eval/results/retrieval.json](eval/results/retrieval.json)):

| Method | Hit@1 | Hit@3 | Hit@5 | MRR@10 |
|---|---|---|---|---|
| Keyword (PostgreSQL full-text) | 0.25 | 0.40 | 0.42 | 0.33 |
| Vector (pgvector, multilingual-e5-small) | 0.38 | 0.55 | 0.66 | 0.50 |
| Hybrid (Reciprocal Rank Fusion) | **0.42** | **0.57** | 0.64 | **0.51** |

Hybrid ranks the right passage first most often. Keyword search is weak because PostgreSQL's
`ts_rank_cd` has no inverse document frequency: common words ("test" occurs in 370 of 931
chunks) outrank rare, decisive ones ("stick": 29). Paraphrased questions are hardest for every
method (best Hit@5 0.47 on 17 questions).

**Detection latency** (CPU, Intel i5-10210U laptop, 10 images, auto mode): fast-only runs
135-218 ms; runs that escalated to the accurate model 488-583 ms; 3 of 10 images escalated.

**Cost and latency of LLM features** (Claude Opus 5.5):

| Action | Tool calls | Tokens | Cost |
|---|---|---|---|
| Vision review of 7 crops (one request, 7.2 s) | - | 1.5k | $0.015 |
| Question on flags + manuals (screenshot above) | 3 | 12.9k | $0.069 |
| Manual question on the Azure deployment (13 s end to end) | 2 | 8.2k | $0.048 |

## Run it

Requires Docker. Put a Claude API key in `.env` (`ANTHROPIC_API_KEY=...`, see `.env.example`).

```bash
docker compose up --build
```

Open http://localhost:8000. On the first start the container downloads the public-domain
manuals (SHA-256 verified), chunks and embeds them (931 chunks; about 5 minutes on a laptop
CPU, measured on a fresh stack).

The thesis YOLO weights are **not** in this repository (dataset licence and pending publication).
Without them the manual search and the agent work, and image upload returns a clear 503
message. With weights, place `*.pt` files in `models/` before building (names in
[detection.py](src/inspection_copilot/detection.py)).

### Development

```bash
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[ml,dev]"
docker compose up -d db
alembic upgrade head
pytest                                        # 34 tests; DB tests use a separate test database
python -m inspection_copilot.ingest           # manuals into the dev database
python -m inspection_copilot.eval_retrieval   # retrieval evaluation
uvicorn inspection_copilot.main:app --reload
```

## Evaluation method

* **Question set:** 53 questions drafted with an AI assistant (Claude) from the manuals, each
  with a short verbatim **evidence quote** and its page. `--check` verifies every quote occurs
  in its document on the stated page. A retrieved chunk counts as correct if it contains the
  quote (ignoring case and whitespace, because PDF extraction sometimes splits words).
  Labelling by quote instead of chunk id keeps the set valid when chunking changes.
* **Bias control:** questions written from the text favour keyword search, so 17 of them are
  `paraphrase` questions that avoid the source wording; results are reported per category.
* **Agent tests** use a scripted fake Claude client (no key, no cost): parallel tool results,
  unknown tools, step cap, refusals. CI runs lint, migrations and all tests against PostgreSQL
  with pgvector and builds the Docker image.

## Deployment (Azure)

Infrastructure as code in [infra/main.bicep](infra/main.bicep): private Container Registry,
managed identity (AcrPull, no registry password), PostgreSQL Flexible Server with pgvector,
Container Apps scaling to zero. Secrets are Container Apps secrets. A public URL is protected by
an access code and a daily Claude budget ($1/day) enforced from a usage table.
`infra/deploy.sh` creates the resources, `infra/release.sh` builds, pushes and switches the app.
The live demo runs in the EU (app: Sweden Central, database: France Central); access code on
request. What went wrong during deployment and how it was solved is in the
[walkthrough](docs/WALKTHROUGH.md#5-deployment-on-azure).

## Knowledge base

US Army TM 5-684 *Electrical Exterior Facilities* (1996) and US Bureau of Reclamation FIST
volumes 3-18 to 3-28 and 4-1B (2000-2005): US federal government works, public domain in the
US ([data/sources.toml](data/sources.toml)). The PDFs are downloaded, not stored here.

## Limitations

* The manuals are older US documents, not current European standards (DIN EN / IEC); the agent
  says so when it matters.
* The YOLO models localise insulators; they do not classify defects. Condition assessment comes
  from the vision LLM and is an AI second opinion that flags cases for a qualified person.
* On small or blurry aerial crops the vision review often answers "unclear" by design.
* The retrieval questions were drafted with an AI assistant; keyword ranking lacks IDF (BM25 is
  the planned fix, to be measured on a held-out question set).
* PDF extraction sometimes mixes two-column text, so a chunk's section label can be one
  paragraph off.
* Latency and cost figures are single runs, not benchmarks.

## Project layout

```
src/inspection_copilot/   detection, vision review, retrieval, agent, API, UI (static/)
migrations/               Alembic schema migrations
eval/                     question set and results
infra/                    Bicep and deployment scripts
tests/                    pytest suite (unit + PostgreSQL integration)
docs/WALKTHROUGH.md       design decisions, deployment notes, interview Q&A
```

## License

Code: MIT. Documents and images keep their own licences (see the files referenced above).
