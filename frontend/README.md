# SignalForge — Frontend (React)

React dashboard for SignalForge competitive intelligence.

Deploy this folder to **[Vercel](https://vercel.com)**. Requires the **[backend](../backend/)** API (FastAPI Cloud).

![SignalForge cover](./public/signalforge-cover-16x9.png)

## Deploy (Vercel)

1. Import repo → **Root Directory:** `frontend`
2. Framework: **Vite** (`vercel.json` included)
3. Environment variable:
   - `VITE_API_URL` = `https://<your-api-host>/api/v1`

## Local dev

```bash
npm install
npm run dev
```

Open http://localhost:5173 (proxies `/api` to `http://127.0.0.1:8000` in dev).

For a remote API, create `.env.local`:

```
VITE_API_URL=https://your-api.fastapicloud.dev/api/v1
```

## Stack

React 19 · TypeScript · Vite · Recharts · React Markdown
