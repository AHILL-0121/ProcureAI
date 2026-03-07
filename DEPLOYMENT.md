# ProcureAI Deployment Guide

## Architecture

**Frontend (Vercel):** https://sa-procure-ai.vercel.app/  
**Backend (Render):** https://procureai-p1i2.onrender.com/

---

## Backend Deployment (Render)

### 1. Render Service Configuration

**Service Type:** Web Service

**Build Settings:**
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Environment Variables in Render

Add these in Render Dashboard → Environment:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATABASE_URL=postgresql://user:pass@host.aws.neon.tech/dbname?sslmode=require
CORS_ORIGINS=https://sa-procure-ai.vercel.app,http://localhost:3000
APP_PORT=8000
```

**Optional (Email Polling):**
```env
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=your@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_USE_SSL=true
EMAIL_POLLING_ENABLED=true
EMAIL_POLL_INTERVAL=30
```

---

## Frontend Deployment (Vercel)

### 1. Vercel Project Settings

**Framework Preset:** Next.js  
**Root Directory:** `frontend`  
**Build Command:** `npm run build` (automatic)  
**Output Directory:** `.next` (automatic)

### 2. Environment Variables in Vercel

Add this in Vercel Dashboard → Settings → Environment Variables:

```env
NEXT_PUBLIC_API_URL=https://procureai-p1i2.onrender.com/api
```

**Important:** Must start with `NEXT_PUBLIC_` to be available in the browser.

### 3. Vercel Deployment

Every push to `main` branch automatically triggers a deployment.

Manual deploy:
```bash
cd frontend
npm install -g vercel
vercel --prod
```

---

## How Frontend Connects to Backend

### API Requests

All API calls go through `src/lib/utils.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';
```

- **Local Development:** Uses `http://localhost:8001/api`
- **Production (Vercel):** Uses `https://procureai-p1i2.onrender.com/api`

### WebSocket Connection

WebSocket URL is derived from the API URL:

```typescript
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';
const wsUrl = apiUrl.replace('http', 'ws').replace('/api', '/ws');
```

- **Local:** `ws://localhost:8001/ws`
- **Production:** `wss://procureai-p1i2.onrender.com/ws`

### Document Preview

Invoice documents are served from backend:

```typescript
const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';
window.open(`${apiBase}/documents/invoice/${match.invoice_id}`, '_blank');
```

Opens: `https://procureai-p1i2.onrender.com/api/documents/invoice/{id}`

---

## CORS Configuration

Backend allows requests from both local and production frontend:

**Backend `.env`:**
```env
CORS_ORIGINS=http://localhost:3000,https://sa-procure-ai.vercel.app
```

---

## Testing the Connection

### 1. Test Backend Health

```bash
curl https://procureai-p1i2.onrender.com/api/health
```

Should return system status with Groq API and database info.

### 2. Test Frontend

Visit: https://sa-procure-ai.vercel.app/

- Dashboard loads with stats
- Performance badge shows load time (~250-500ms)
- WebSocket connection indicator (green dot)

---

## Troubleshooting

### Frontend shows "Failed to fetch"

**Fix:**
1. Check Vercel env var: `NEXT_PUBLIC_API_URL=https://procureai-p1i2.onrender.com/api`
2. Redeploy frontend after adding env var
3. Verify backend CORS includes `https://sa-procure-ai.vercel.app`

### WebSocket not connecting

**Fix:**
1. Check browser console for WebSocket errors
2. Verify `NEXT_PUBLIC_API_URL` is set correctly
3. Check Render logs for WebSocket connection attempts

### Backend 404 errors

**Fix:**
1. Render → Settings → Build & Deploy
2. Set **Root Directory** to `backend`
3. Redeploy

---

## Cost Estimates (Free Tiers)

- **Render (Free):** 750 hours/month, 512MB RAM
- **Vercel (Hobby):** Unlimited deployments, 100GB bandwidth
- **Neon PostgreSQL (Free):** 512MB storage, connection pooling
- **Groq API (Free):** 14,400 requests/day

**Total Monthly Cost: $0** 🎉

---

## Support

- **GitHub Repository:** https://github.com/AHILL-0121/ProcureAI
- **Backend Logs:** Render Dashboard → Logs
- **Frontend Logs:** Vercel Dashboard → Deployments
