# AGENTS.md — Ordenes de Trabajo (EERSSA)

Personal project, used daily.

## Assumed running services

Kafka, 01 Producer, 02 Consumer, and 03 Batch writer are expected to already be up.
They continuously write to Delta Lake. Do not restart or modify them without asking.

## Active development

The focus is the Marimo notebook `05_HE_Delta_R2.py`. This is the file being worked on.

```bash
marimo edit 05_HE_Delta_R2.py
```

The notebook reads from Delta Lake (Cloudflare R2) and syncs to DuckDB (MotherDuck).

## Shared dependency: eerssa/utils.py

`eerssa/utils.py` is used by `03_concat_ot.py` (and transitively by 01/02 via `procesarActividades.py`).
Only 3 functions live here now: `load_r2_credentials`, `get_festivos`, `soloFecha_SinTimezone`.
Changes here must be backward-compatible, or coordinated with a restart of 03_concat_ot.

## Notebook helpers: eerssa/he_helpers.py

`eerssa/he_helpers.py` contains all HE/Excel/DuckDB logic used exclusively by `05_HE_Delta_R2.py`.
When modifying during notebook development, only the notebook is affected — the 01/02/03 pipeline
does not depend on this file.

## Setup

- **Package manager**: `uv`. `uv sync` to install.
- **Python**: 3.10 (`.python-version`).
- **Secrets** (never commit): `eerssa/secret.py` (MongoDB URI), `secrets/r2_credentials.json` (R2 keys + duckdb_he_token).
- **nltk**: may need `nltk.download()` on first run.

## Architecture overview

```
PDFs → 01_producer (Dask + watchdog) → Kafka(json_ot_v30)
       → 02_consumer → MongoDB(ot_v30) → Kafka(to_delta)
       → 03_concat_ot (15s window) → Delta Lake (R2) ← 05_HE_Delta_R2 (Marimo)
```

- Kafka: `docker-compose up` (Kafka + Zookeeper on `localhost:29092`).
- Delta Lake table: `s3://delta-v30/delta_v30` on Cloudflare R2.
- No CI/CD, no test framework — `tests/` is ad-hoc.