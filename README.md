# chatautomation
Social Chatbot

# BFF Middleware v24 (FastAPI)

**Deploy target:** Render (replace your existing service or create a new one).  
**Purpose:** Central "brain" for your GPT Employees. Posts via **Ocoya**, manages **Systeme.io** contacts/tags, sends **Gmail** digests, and exposes 24 GPT endpoints.

---

## 1) Local run (optional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill keys
uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000/docs
```

## 2) Render deployment (replace existing)

1. Zip this folder (or upload repo) to **Render → your existing service → Manual Deploy**.
2. In **Environment**, set the variables from `.env.example`.
3. Ensure **Start Command** = `uvicorn main:app --host 0.0.0.0 --port 10000` (or Render’s $PORT).
4. Deploy. Visit `/docs` to see all endpoints.

## 3) Secure calls from GPTs

- Set `ALLOW_UNAUTH=false` and a strong `BFF_MIDDLEWARE_KEY` in Render.
- In each GPT action (or during manual curl), include header: `x-bff-key: <your key>`.

## 4) Core endpoints

- `GET /health` – sanity check
- `POST /cron/daily-bff-report` – builds & emails the BFF morning digest
- `POST /social/publish-ocoya` – schedules content through Ocoya
- `POST /systeme/contact` – upsert contact + tags
- `POST /gmail/send` – relay email (stub by default)
- `POST /gpt/<agent>` – 24 GPT employee controllers

## 5) Postman

- Import `BFF_Middleware_v24.postman_collection.json`
- Set `{baseUrl}` to your Render URL
- Use the sample bodies to test each endpoint

## 6) Notes

- Ocoya & Systeme calls are **stubs**—replace with the real API URLs/fields when ready.
- Keep keys on the server only. GPTs call the middleware, **never** external APIs directly.
- CRIS orchestrates which `/gpt/*` to call per task.
