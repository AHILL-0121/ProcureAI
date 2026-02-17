# ProcureAI — Intelligent Procurement Automation

Multi-Agent AI System for **Three-Way Invoice Match Automation**, powered by **Local Llama 3.1** (via Ollama) and **Next.js 14**.

ProcureAI ingests invoices from email or manual upload, extracts structured data with OCR + LLM, validates them through a 6-agent pipeline, performs three-way matching against Purchase Orders and Goods Receipts from an ERP dataset, and surfaces results on a real-time glassmorphism dashboard.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js 14 Dashboard                      │
│  /dashboard  │  /invoices  │  /matches  │  /purchase-orders  │
└───────────────────────┬──────────────────────────────────────┘
                        │ REST + WebSocket (real-time)
┌───────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Python)                     │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│  Email   │  Vision  │ Classif. │   ERP    │    Matching      │
│  Intake  │  OCR     │  Agent   │  Agent   │    Agent         │
│  Agent   │ (Llama)  │          │ (CSV)    │   (3-Way)        │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│                   Orchestrator Agent                         │
└──────────────────────────────────────────────────────────────┘
        │                               │
 ┌──────▼──────┐               ┌────────▼─────────┐
 │   Ollama    │               │   SQLite DB       │
 │  Llama 3.1  │               │ + Oracle ERP CSVs │
 └─────────────┘               └──────────────────┘
```

---

## Features

- **Continuous Email Polling** — IMAP inbox monitoring every 30 s with smart attachment filtering (skips icons, logos, mailer-daemon bounce emails)
- **SMTP/IMAP Health Check** — connection verified at server startup
- **OCR + LLM Extraction** — Tesseract OCR → Llama 3.1 structured extraction with robust JSON parsing (tolerates trailing commas, single quotes, comments)
- **Three-Way Matching** — Invoice ↔ Purchase Order ↔ Goods Receipt with configurable tolerances
- **Real-time Dashboard** — glassmorphism UI with skeleton loading, animated transitions, WebSocket live updates
- **Oracle ERP Dataset** — 1,000 POs, 1,983 PO lines, 1,388 GRNs, 10 vendors, 20 materials loaded from CSV
- **16 Test Invoices** — 8 scenario-based + 8 diverse edge cases (duplicates, currency mismatches, zero amounts, unauthorized charges)
- **Audit Trail** — every agent action logged with timestamps
- **Docker Support** — single `docker-compose up` deployment

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Ollama | Latest, with `llama3.1:latest` pulled |
| Tesseract OCR | 5.x (added to PATH) |

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest

# Email polling (optional — leave blank to disable)
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_USE_SSL=true
EMAIL_POLLING_ENABLED=true
EMAIL_POLL_INTERVAL=30
```

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open Dashboard

Navigate to **http://localhost:3000**

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System health + Ollama status |
| `POST` | `/api/invoices/upload` | Upload & process an invoice |
| `POST` | `/api/invoices/process-demo` | Process all sample invoices |
| `GET` | `/api/invoices` | List invoices (paginated, filterable) |
| `GET` | `/api/invoices/{id}` | Invoice detail |
| `GET` | `/api/matches` | List match results |
| `GET` | `/api/dashboard/stats` | Dashboard KPIs |
| `GET` | `/api/purchase-orders` | List POs from ERP dataset |
| `GET` | `/api/purchase-orders/{po}` | PO detail + GRN |
| `GET` | `/api/audit-logs` | Agent audit trail |
| `WS` | `/ws` | Real-time WebSocket updates |

### Email Polling

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/email/poll-status` | Polling state, stats, last error |
| `POST` | `/api/email/poll-now` | Trigger an immediate one-off poll |
| `POST` | `/api/email/poll-start` | Start background polling loop |
| `POST` | `/api/email/poll-stop` | Stop background polling loop |

---

## Agents

| # | Agent | Role |
|---|-------|------|
| 1 | **Email Intake** | Continuously polls IMAP inbox, filters attachments, SHA-256 deduplication |
| 2 | **Vision / OCR** | Tesseract + Llama 3.1 structured extraction with robust JSON parsing |
| 3 | **Classification** | Validates fields, classifies invoice type, detects duplicates |
| 4 | **ERP Integration** | Fetches POs + GRNs from Oracle Migration Dataset (1,000 POs) |
| 5 | **Matching** | Three-way match with quantity / price / description tolerances |
| 6 | **Orchestrator** | Coordinates full pipeline, manages state, WebSocket broadcasts |

---

## Three-Way Matching Rules

| Check | Tolerance | Severity |
|-------|-----------|----------|
| Quantity | ±2 % | MEDIUM |
| Price | ±5 % | HIGH |
| Description | 85 % fuzzy match | MEDIUM |
| Missing PO | — | HIGH |
| **Results** | `FULL_MATCH` · `PARTIAL_MATCH` · `NO_MATCH` | |

---

## Sample Invoice Test Scenarios

| File | Scenario |
|------|----------|
| `scenario_1_full_match_PO-000001.txt` | Full match |
| `scenario_2_partial_match_PO-000020.txt` | Partial match (minor qty diff) |
| `scenario_3_price_mismatch_PO-000041.txt` | Price discrepancy |
| `scenario_4_qty_overbill_PO-000056.txt` | Quantity overbilling |
| `scenario_5_fake_po_PO-999999.txt` | Non-existent PO reference |
| `scenario_6_full_match_multiline_PO-000020.txt` | Multi-line full match |
| `scenario_7_extra_items_PO-000104.txt` | Unauthorized extra line items |
| `scenario_8_minor_qty_diff_PO-000127.txt` | Within-tolerance qty difference |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts |
| **AI / LLM** | Llama 3.1 8B via Ollama (100 % local, zero API cost) |
| **OCR** | Tesseract 5.x + llama3.2-vision fallback |
| **Database** | SQLite (MVP) / PostgreSQL (production) |
| **ERP Data** | Oracle Migration Dataset — 8 CSVs |
| **Real-time** | WebSocket via FastAPI ConnectionManager |
| **Container** | Docker + docker-compose |

---

## Docker

```bash
docker-compose up --build
```

> Requires Ollama running on the host machine (accessed via `host.docker.internal`).

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/          # 6 AI agents
│   │   ├── config.py        # Pydantic settings (.env)
│   │   ├── database.py      # SQLAlchemy + SQLite
│   │   ├── main.py          # FastAPI app + email polling loop
│   │   ├── models.py        # ORM models
│   │   └── schemas.py       # Pydantic response schemas
│   ├── data/erp/            # Oracle ERP CSV dataset
│   ├── uploads/samples/     # 8 test invoice scenarios
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/app/             # Next.js 14 pages + components
│   ├── tailwind.config.js   # Emerald/teal glassmorphism theme
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── ProcureAI_MVP_SRS_Llama_NextJS.md   # Full SRS document
├── presentation.md                      # 10-slide pitch deck
└── process.md                           # Development process log
```
