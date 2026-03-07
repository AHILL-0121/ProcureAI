# ProcureAI — Intelligent Procurement Automation

Multi-Agent AI System for **Three-Way Invoice Match Automation**, powered by **Groq API (Llama 3.3)** and **Next.js 14**.

ProcureAI ingests invoices from email or manual upload, extracts structured data with **Tesseract OCR + LLM**, validates them through a multi-agent pipeline, performs three-way matching against Purchase Orders and Goods Receipts from a **PostgreSQL ERP dataset (Neon Cloud)**, and surfaces results on a real-time warm glassmorphism dashboard with ~250ms load times.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js 14 Dashboard                      │
│  /dashboard  │  /invoices  │  /matches  │  /purchase-orders  │
│  Real-time Performance Tracking • Document Preview           │
└───────────────────────┬──────────────────────────────────────┘
                        │ REST + WebSocket (real-time)
┌───────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Python)                     │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│  Email   │ Tesseract│ Classif. │   ERP    │    Matching      │
│  Intake  │   OCR    │  Agent   │  Agent   │    Agent         │
│  Agent   │ + Groq   │          │(Postgres)│   (3-Way)        │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│                   Orchestrator Agent                         │
└──────────────────────────────────────────────────────────────┘
        │                               │
 ┌──────▼──────┐               ┌────────▼─────────────┐
 │  Groq API   │               │ PostgreSQL (Neon)     │
 │ Llama 3.3   │               │ 4,341 ERP Records     │
 │ + Vision    │               │ Real-time Caching     │
 └─────────────┘               └──────────────────────┘
```

---

## Features

✨ **Performance Optimized** — Dashboard loads in ~250ms (53x faster than initial version)
- Single-query database aggregation with SQLAlchemy `case()` statements
- 5-minute ERP stats caching to reduce cloud database queries
- Real-time performance tracking badge in UI

📄 **Document Preview** — Click any invoice card to view the original uploaded PDF/image in a new tab for manual verification

🤖 **LLM Powered** — Groq API with Llama 3.3 70B (text) and Llama 3.2 90B Vision (images)
- 30-second timeout for text processing
- 60-second timeout for vision extraction
- Robust JSON parsing (handles trailing commas, single quotes, comments)

🔍 **OCR Extraction** — Tesseract OCR primary extraction method
- Fast and reliable text extraction from PDFs and images
- Structured data extraction via Groq LLM

🎯 **Three-Way Matching** — Invoice ↔ Purchase Order ↔ Goods Receipt
- Configurable tolerances (±2% quantity, ±5% price)
- Fuzzy description matching (85% threshold)
- Automatic discrepancy detection and severity classification

💾 **Cloud Database** — PostgreSQL (Neon) with 4,341 ERP records
- 10 vendors, 20 materials
- 990 purchase orders with 1,953 line items
- 1,368 goods receipts
- Connection pooling for optimal performance

📧 **Email Automation** — Continuous IMAP inbox monitoring (configurable interval)
- Smart attachment filtering (skips icons, logos, mailer-daemon bounces)
- SHA-256 deduplication to prevent duplicate processing
- SMTP/IMAP health checks at startup

🎨 **Modern UI** — Warm glassmorphism design with real-time updates
- Skeleton loading states
- Animated transitions and micro-interactions
- Frosted glass modal effects with backdrop blur
- WebSocket live updates for instant feedback
- Performance tracking with color-coded timing badges

🔍 **Audit Trail** — Every agent action logged with timestamps for compliance

🐋 **Docker Ready** — Single `docker-compose up` deployment

---

## Quick Start

### Prerequisites

| Tool | Version | Required |
|------|---------|----------|
| Python | 3.11+ | ✅ Yes |
| Node.js | 18+ | ✅ Yes |
| Tesseract OCR | 5.x | ✅ Yes (add to PATH) |
| Groq API Key | — | ✅ Yes |
| PostgreSQL | 14+ | ✅ Yes (Neon cloud) |

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file:

```env
# Groq API (Required)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# PostgreSQL Database (Required)
DATABASE_URL=postgresql://user:pass@host.region.aws.neon.tech/dbname

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
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
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

## Performance Metrics

**Dashboard Load Time: ~254ms** ⚡
- Health Check: 13ms (cached)
- Dashboard Stats: 240ms (single optimized query)
- **Previous version: 13,537ms (53x slower)**

**Optimizations Applied:**
1. Consolidated 9 separate database queries into 1 aggregated query
2. Added 5-minute caching for ERP statistics
3. Removed LLM health check API calls (static validation only)
4. Switched from Ollama (local, timeout-prone) to Groq API (cloud, reliable)

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
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://user:pass@host/dbname

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
cd backend;uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend

```bash
npm install
cd frontend;npm run dev
```

### 3. Open Dashboard

Navigate to **http://localhost:3000**

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System health + Groq API status |
| `POST` | `/api/invoices/upload` | Upload & process an invoice |
| `POST` | `/api/invoices/process-demo` | Process all sample invoices |
| `GET` | `/api/invoices` | List invoices (paginated, filterable) |
| `GET` | `/api/invoices/{id}` | Invoice detail |
| `GET` | `/api/matches` | List match results with file paths |
| `GET` | `/api/documents/invoice/{id}` | 📄 Serve invoice document (PDF/image) |
| `GET` | `/api/dashboard/stats` | Dashboard KPIs (single optimized query) |
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

| # | Agent | Role | Technology |
|---|-------|------|------------|
| 1 | **Email Intake** | Continuously polls IMAP inbox, filters attachments, SHA-256 deduplication | Python IMAP, aiofiles |
| 2 | **Vision / OCR** | **Tesseract OCR** primary extraction + Groq LLM structured parsing | Tesseract, Groq API (Llama 3.3 70B) |
| 3 | **Classification** | Validates fields, classifies invoice type, detects duplicates | Rule-based + LLM |
| 4 | **ERP Integration** | Fetches POs + GRNs from PostgreSQL with 5-minute caching | SQLAlchemy, PostgreSQL |
| 5 | **Matching** | Three-way match with tolerance checks and severity classification | Fuzzy matching, thresholds |
| 6 | **Orchestrator** | Coordinates full pipeline, manages state, WebSocket broadcasts | FastAPI, asyncio |

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
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Pydantic, httpx |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts |
| **AI / LLM** | Groq API — Llama 3.3 70B (text) + Llama 3.2 90B Vision (images) |
| **OCR** | Tesseract 5.x (primary) + PyPDF2 (PDF text extraction) |
| **Database** | PostgreSQL (Neon cloud) with connection pooling |
| **ERP Data** | Oracle Migration Dataset — 4,341 records migrated to PostgreSQL |
| **Real-time** | WebSocket via FastAPI ConnectionManager |
| **Container** | Docker + docker-compose |
| **Performance** | SQLAlchemy query optimization, 5-minute caching, single aggregated queries |

---

## Docker

```bash
docker-compose up --build
```

> **Note:** Requires Groq API key in `.env` file and PostgreSQL connection string. No local Ollama installation needed.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/          # 6 AI agents (orchestrator, vision_ocr, matching, etc.)
│   │   ├── config.py        # Pydantic settings (.env)
│   │   ├── database.py      # SQLAlchemy + PostgreSQL
│   │   ├── main.py          # FastAPI app + optimized endpoints
│   │   ├── models.py        # ORM models (Invoice, PO, GRN)
│   │   └── schemas.py       # Pydantic response schemas
│   ├── data/erp/            # Oracle ERP CSV dataset (4,341 records)
│   ├── uploads/             # User-uploaded invoices (gitignored)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js 14 pages (dashboard, matches, invoices)
│   │   ├── components/      # React components (Header, Sidebar, Toast, WebSocket)
│   │   └── lib/             # TypeScript types and utilities
│   ├── tailwind.config.js   # Warm glassmorphism theme (cream, amber, forest)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md                # This file
```

---

## Key Features in Detail

### 📄 Document Preview

Click the **"📄 View Document"** button on any invoice card in the matches modal to:
- Open the original uploaded PDF or image in a new browser tab
- Perform manual verification when discrepancies are detected
- Compare invoice details side-by-side with ERP data

### ⚡ Performance Optimization

**Before:** 13,537ms dashboard load time
**After:** 254ms dashboard load time (53x faster)

**Techniques:**
1. **Database query consolidation** — 9 separate queries → 1 aggregated query using SQLAlchemy `case()` statements
2. **Smart caching** — ERP statistics cached for 5 minutes to reduce cloud database round-trips
3. **Health check optimization** — Removed external API calls, static validation only
4. **LLM architecture** — Switched from local Ollama (timeout-prone) to cloud Groq API (reliable)

### 🎨 UI/UX Design

**Warm Glassmorphism Theme:**
- **Cream** (#FDFAF4) — Background
- **Amber** (#D97706) — Accents & warnings
- **Forest** (#15803D) — Success states
- **Sage** (#4ADE80) — Info highlights
- **Crimson** (#DC2626) — Errors & critical discrepancies

**Micro-interactions:**
- Frosted glass modal with backdrop blur (8px)
- Skeleton loading states during data fetching
- Animated card transitions with hover effects
- Real-time performance badge with color coding (<200ms green, 200-500ms yellow, >500ms red)

---

## Sample Invoice Test Scenarios

8 diverse test scenarios included in `backend/uploads/samples/`:

| File | Scenario |
|------|----------|
| `scenario_1_full_match_PO-000001.txt` | Full match (all data matches perfectly) |
| `scenario_2_partial_match_PO-000020.txt` | Partial match (minor quantity difference within tolerance) |
| `scenario_3_price_mismatch_PO-000041.txt` | Price discrepancy (exceeds ±5% threshold) |
| `scenario_4_qty_overbill_PO-000056.txt` | Quantity overbilling (invoice > PO) |
| `scenario_5_fake_po_PO-999999.txt` | Non-existent PO reference (no match found) |
| `scenario_6_full_match_multiline_PO-000020.txt` | Multi-line invoice with full match |
| `scenario_7_extra_items_PO-000104.txt` | Unauthorized extra line items |
| `scenario_8_minor_qty_diff_PO-000127.txt` | Within-tolerance quantity difference |

---

## Database Schema

### PostgreSQL Tables

**Invoices** — Processed invoice records
- Primary key: UUID
- Fields: invoice_number, vendor_name, total_amount, po_reference, match_result, confidence_score, file_path
- Relationships: line_items (one-to-many)

**ERP Tables** (migrated from Oracle):
- **erp_vendors** — 10 suppliers
- **erp_materials** — 20 materials
- **erp_po_headers** — 990 purchase orders
- **erp_po_lines** — 1,953 PO line items
- **erp_goods_receipts** — 1,368 goods receipts

**Audit Logs** — Agent action trail for compliance

---

## Environment Variables

```env
# Groq API (Required)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# PostgreSQL Database (Required)
DATABASE_URL=postgresql://user:pass@host.aws.neon.tech/dbname

# Email Polling (Optional)
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_USE_SSL=true
EMAIL_POLLING_ENABLED=true
EMAIL_POLL_INTERVAL=30
```

---

## Development Roadmap

### Completed ✅
- [x] Multi-agent architecture with orchestrator
- [x] Tesseract OCR + Groq LLM extraction
- [x] Three-way matching engine with tolerance checks
- [x] PostgreSQL ERP dataset integration (4,341 records)
- [x] Real-time WebSocket updates
- [x] Email automation with IMAP polling
- [x] Document preview functionality
- [x] Performance optimization (53x faster)
- [x] Warm glassmorphism UI with responsive design

### Future Enhancements 🚀
- [ ] Approval workflow (multi-level authorization)
- [ ] Email notifications for discrepancies
- [ ] Batch processing for multiple invoices
- [ ] Advanced analytics dashboard (trends, forecasting)
- [ ] Export to ERP systems (SAP, Oracle, NetSuite)
- [ ] Mobile app (React Native)
- [ ] Machine learning for anomaly detection
- [ ] Multi-currency support with live exchange rates

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- **Groq** — Ultra-fast LLM inference API
- **Neon** — Serverless PostgreSQL with instant branching
- **Tesseract OCR** — Open-source OCR engine
- **FastAPI** — Modern Python web framework
- **Next.js** — React framework with server-side rendering
- **Recharts** — Composable charting library

---

**Built with ❤️ during Agentix Bootcamp 2026**
