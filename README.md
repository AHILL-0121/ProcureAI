# ProcureAI

Three-way invoice matching for accounts payable. ProcureAI reads supplier invoices (upload or email),
checks them line by line against the purchase order and the goods receipt, clears the ones that agree,
and puts the rest in a human **In-tray** with the reason circled.

```
 upload / IMAP ─► Received ─► Read ─► Check ─► Look up ─► Match ─► MATCHED (cleared)
                   (intake)   (OCR +  (fields,  (PO, GRN,  (line   └► DISCREPANCY / ON_HOLD ─► In-tray ─► approve · hold · reject
                              Groq)   vendor,   billed      level)                                       (with audit trail and undo)
                                      dupes)    qty)
```

## What it checks

| Check | Rule | Severity |
|---|---|---|
| Unit price vs PO | within ±5 % or 0.05 absolute (configurable per vendor) | HIGH if over |
| Quantity vs goods received | invoiced ≤ received − already billed, ±2 % | HIGH |
| Cumulative billing vs PO | billed so far + this invoice ≤ ordered, ±2 % | HIGH |
| Goods not received | billing a PO line with no receipt → **ON HOLD**, re-checked automatically | HIGH |
| Vendor | tax ID or name must match the PO vendor | HIGH |
| Currency | must match the PO currency | HIGH |
| PO | must exist and be open | HIGH |
| Line not on PO | unauthorised extra lines | HIGH |
| Unitemised charges | invoice net must equal the sum of its lines | HIGH |
| Unit of measure | must match the PO line | MEDIUM |
| Duplicates | same file (SHA-256) or same vendor + invoice number → **DUPLICATE**, never matched | — |

PO lines the supplier did not bill are informational only, so partial invoices and partial deliveries match
correctly. Thirteen sample invoices built from real POs in the dataset cover every rule
(`backend/samples/`, regenerate with `python -m app.generate_samples`).

## Stack

- **API**: FastAPI, SQLAlchemy 2 (typed models), Alembic, PostgreSQL on Neon (the only database; no local DB), PyJWT
- **Reading**: PyMuPDF for PDF text and page rendering, Tesseract OCR for scans and images, Groq
  (`llama-3.3-70b-versatile`, JSON mode) to fill a strict, type-coerced schema; optional Groq vision
  fallback for poor scans
- **Processing**: in-process job queue with worker threads; WebSocket progress events
- **Dashboard**: Next.js 15, React 19, TanStack Query, Motion, cmdk, Radix Dialog, Phosphor icons,
  hand-written CSS on design tokens ("Triplicate": a light, paper-and-ink theme)

## Run it locally

Requirements: Python 3.11+, Node 22+, [Tesseract](https://github.com/tesseract-ocr/tesseract) on `PATH`
(only needed for scanned documents), a [Groq API key](https://console.groq.com/keys), and a
[Neon](https://neon.tech) PostgreSQL database. The backend always uses Neon; there is no local database.
For development, point `DATABASE_URL` at a separate Neon **branch** (e.g. `dev`, created from production in the
Neon console), so local runs, migrations and test uploads never touch production data.

```bash
# API
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env.local                           # set DATABASE_URL (Neon), GROQ_API_KEY, JWT_SECRET, ADMIN_*
uvicorn app.main:app --port 8001 --reload            # migrates Neon and loads the ERP dataset on first start
```

```bash
# Dashboard
cd frontend
npm install
cp .env.example .env.local
npm run dev                                          # http://localhost:3000
```

The first start creates the admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD` when the database has no users
(in development without them it falls back to `admin@procureai.local` / `procureai-admin`). Sign in, open **Settings → Demo invoices** to process the
samples, then work the **In-tray**.

Without signing in, the landing page's **Try a sample invoice** section replays recorded runs of the matching
engine over eight of the samples. The landing and sign-in pages also ping the API on load, so a sleeping
free-tier backend starts booting early; while it boots, the dashboard shows a "waking up" note.

### Docker

```bash
cp backend/.env.example backend/.env.local   # set DATABASE_URL (Neon) and the rest
docker compose up --build                    # API (:8001) + dashboard (:3000); the database stays on Neon
```

## Roles

| Role | Can |
|---|---|
| viewer | read everything |
| ap_clerk | upload, correct extracted fields, re-match, hold, undo own decisions |
| approver | everything a clerk can, plus approve and reject (override notes required for high-severity issues) |
| admin | everything, plus tolerances, email intake, people, demo data |

## API

Interactive docs at `/docs`. Main endpoints (all require a bearer token except `/api/ping`, `/api/health` and `/api/auth/login`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/ping` | cheap liveness check (one `SELECT 1`, no LLM call); use it for health checks and wake-ups |
| GET | `/api/health` | full pipeline status: database, ERP, Groq models (calls the LLM, so don't poll it) |
| POST | `/api/auth/login` | email + password → token |
| POST | `/api/invoices/upload` | multipart `files` (PDF/PNG/JPEG ≤ 15 MB) → `202`, processed in the background |
| GET | `/api/invoices?queue=review` | the In-tray (`queue`: review, processing, cleared, failed; `issue`, `search`, `sort`, pagination) |
| GET | `/api/invoices/{id}` | detail incl. match checks, PO/GRN snapshot, extraction metadata |
| PATCH | `/api/invoices/{id}` | correct fields (logged) |
| POST | `/api/invoices/{id}/rematch` · `/approve` · `/reject` · `/hold` · `/reopen` · `/retry` | review actions |
| GET | `/api/invoices/{id}/document-link` | short-lived signed URL for the original file |
| GET | `/api/purchase-orders` · `/api/purchase-orders/{po}` | ERP POs with fulfilment (ordered / received / invoiced) |
| GET | `/api/erp/status` | ERP record counts, last import, CSV layouts |
| POST | `/api/erp/import?mode=merge\|replace&dry_run=` | ERP Connect: check or load CSV exports (admin, all-or-nothing) |
| GET/PUT | `/api/settings/tolerances` | global and per-vendor tolerances |
| GET | `/api/dashboard/stats` | overview figures (per-currency totals list INR first, then by amount) |
| WS | `/ws?token=…` | `status_update`, `match_complete`, `processing_error`, `review_update` |

## Deploying

- **API** (e.g. Render): build `backend/Dockerfile`. On start the app migrates the Neon database named
  in `DATABASE_URL`: it upgrades the schema (an existing v1 database is detected and stamped automatically; the v2 migration
  rebuilds the ERP tables and reloads them from `data/erp`). Required env: `APP_ENV=production`,
  `DATABASE_URL`, `GROQ_API_KEY`, `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CORS_ORIGINS`.
  Run a **single** process: the job queue and email poller live in-process. Set the platform's health check
  path to `/api/ping`. On a free tier that sleeps when idle, `LLM_STARTUP_CHECK=false` shortens cold starts.
- **Dashboard** (e.g. Vercel): set `NEXT_PUBLIC_API_URL` (and `NEXT_PUBLIC_WS_URL` if the WebSocket
  host differs) at build time.

## Development

```bash
cd backend && ruff check app tests && mypy app && pytest -q      # 99 tests on a throwaway SQLite file; never touches Neon
cd frontend && npm run check:colors && npm run typecheck && npm run lint && npm run build
```

`npm run check:colors` enforces the design rules: no violet/purple hues, no glassmorphism or gradient text.

## Data

`backend/data/erp/` holds the Oracle ERP migration dataset (10 vendors, 20 materials, 1,000 POs, 1,983 PO
lines, 1,388 goods receipts, 1,189 historical invoices, purchase requisitions). By default only invoices
processed by ProcureAI count toward already-billed quantities; set `MATCH_INCLUDE_ERP_INVOICE_HISTORY=true`
to include the dataset's invoice history.

**Your own ERP data (ERP Connect).** Set `ERP_SAMPLE_DATA=false` before the first start so a new database
begins empty. Then, as an admin, open **Settings → ERP connection**, drop your CSV exports (same layouts as
`data/erp`; templates are downloadable there) and click **Check files**. Every row is validated first: required
columns, numbers, dates, currencies, duplicate ids and references. Nothing is written unless all files pass.
**Add & update** upserts by ERP id; **Replace all** swaps the whole dataset. After an import, invoices waiting in the
in-tray or on hold are re-matched against the new data.
