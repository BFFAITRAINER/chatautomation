from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------- Environment ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OCOYA_API_KEY = os.getenv("OCOYA_API_KEY", "")
SYSTEME_API_KEY = os.getenv("SYSTEME_API_KEY", "")

# Google OAuth keys
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# Middleware key & secret
BFF_MIDDLEWARE_KEY = os.getenv("BFF_MIDDLEWARE_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALLOW_UNAUTH = os.getenv("ALLOW_UNAUTH", "false").lower() == "true"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
VIDEO_AI_API_KEY = os.getenv("VIDEO_AI_API_KEY", "")
VIDEO_AI_ENDPOINT = os.getenv("VIDEO_AI_ENDPOINT", "")

# ---------- Security helper ----------
def require_key(x_bff_key: Optional[str]):
    if not ALLOW_UNAUTH and BFF_MIDDLEWARE_KEY:
        if x_bff_key != BFF_MIDDLEWARE_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized - Invalid BFF key")

# ---------- App ----------
app = FastAPI(title="BFF Middleware v24", version="1.0.0")

# ---------- Models ----------
class PublishPost(BaseModel):
    channel: str = Field(..., description="Ocoya channel key or account id (e.g., linkedin, facebook, instagram, youtube, tiktok)")
    text: str
    media_url: Optional[str] = None
    schedule_iso: Optional[str] = None
    tags: Optional[List[str]] = None
    utm: Optional[Dict[str,str]] = None

class SystemeContact(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: Optional[List[str]] = []
    campaign_id: Optional[str] = None

class TaskPayload(BaseModel):
    brand: str = "bff"
    partner: Optional[str] = None
    intent: str
    data: Dict[str, Any] = {}

# ---------- Middleware to verify BFF key ----------
@app.middleware("http")
async def verify_internal_key(request: Request, call_next):
    # Allow unauthenticated access to docs, health, openapi.json
    if request.url.path in ["/docs", "/openapi.json", "/health", "/auth/callback"]:
        return await call_next(request)

    if ALLOW_UNAUTH:
        return await call_next(request)

    key = request.headers.get("x-bff-key")
    if key != BFF_MIDDLEWARE_KEY:
        return JSONResponse(status_code=403, content={"detail": "Unauthorized - Invalid BFF key"})
    return await call_next(request)

# ---------- Health endpoint ----------
@app.get("/health")
async def health():
    return {"status": "OK", "service": "BFF Middleware v24"}

# ---------- OAuth callback ----------
@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)
        response.raise_for_status()
        return response.json()

# ---------- Ocoya Post ----------
async def post_to_ocoya(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not OCOYA_API_KEY:
        return {"status": "skipped", "reason": "OCOYA_API_KEY not set", "echo": payload}
    # Replace with your real Ocoya API call here
    # Example:
    # async with httpx.AsyncClient() as client:
    #     r = await client.post("https://api.ocoya.com/v1/schedule", headers={"Authorization": f"Bearer {OCOYA_API_KEY}"}, json=payload)
    #     r.raise_for_status()
    #     return r.json()
    return {"status": "ok", "posted_via": "ocoya_stub", "echo": payload}

@app.post("/social/publish-ocoya")
async def social_publish_ocoya(post: PublishPost, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    res = await post_to_ocoya(post.dict())
    return res

# ---------- Systeme Contact ----------
async def systeme_upsert_contact(c: SystemeContact) -> Dict[str, Any]:
    if not SYSTEME_API_KEY:
        return {"status": "skipped", "reason": "SYSTEME_API_KEY not set", "contact": c.dict()}
    # Replace with your real Systeme API call here
    return {"status": "ok", "contact_stub": c.dict()}

@app.post("/systeme/contact")
async def systeme_contact(c: SystemeContact, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    res = await systeme_upsert_contact(c)
    return res

# ---------- YouTube Search ----------
@app.get("/youtube/search")
async def search_youtube(q: str, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=400, detail="YOUTUBE_API_KEY not set")
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&key={YOUTUBE_API_KEY}&maxResults=5"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        res.raise_for_status()
        return res.json()

# ---------- Video AI Generation ----------
@app.post("/videoai/generate")
async def generate_video(request: Request, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    if not VIDEO_AI_API_KEY or not VIDEO_AI_ENDPOINT:
        raise HTTPException(status_code=400, detail="VIDEO_AI_API_KEY or VIDEO_AI_ENDPOINT not set")

    data = await request.json()
    headers = {
        "Authorization": f"Bearer {VIDEO_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(VIDEO_AI_ENDPOINT, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

# ---------- Helper to build GPT response ----------
def ok(name, payload, extra=None):
    out = {"agent": name, "received": payload.dict() if hasattr(payload, "dict") else payload}
    if extra:
        out.update(extra)
    return out

# ---------- 24 GPT Endpoints ----------
@app.post("/gpt/cris")
async def gpt_cris(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("CRIS", task, {"next": "route to appropriate agent based on task.intent"})

@app.post("/gpt/ava")
async def gpt_ava(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("AVA", task)

@app.post("/gpt/vinceassist")
async def gpt_vinceassist(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("VINCEASSIST", task)

@app.post("/gpt/leadai")
async def gpt_leadai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    if "lead" in task.data:
        await systeme_upsert_contact(SystemeContact(email=task.data["lead"]["email"], tags=["lead_generated"]))
    return ok("LEADAI", task)

@app.post("/gpt/convertai")
async def gpt_convertai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    if "post" in task.data:
        await post_to_ocoya(task.data["post"])
    return ok("CONVERTAI", task)

@app.post("/gpt/demandai")
async def gpt_demandai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("DEMANDAI", task)

@app.post("/gpt/scheduleai")
async def gpt_scheduleai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("SCHEDULEAI", task)

@app.post("/gpt/verifyai")
async def gpt_verifyai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("VERIFYAI", task)

@app.post("/gpt/fundingai")
async def gpt_fundingai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("FUNDINGAI", task)

@app.post("/gpt/docbot")
async def gpt_docbot(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("DOCBOT", task)

@app.post("/gpt/revenueai")
async def gpt_revenueai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("REVENUEAI", task, {"hint": "includes stock-window content cadence & KPI rollups"})

@app.post("/gpt/ytscribe")
async def gpt_ytscribe(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("YTSCRIBE", task)

@app.post("/gpt/qa")
async def gpt_qa(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("QA", task)

@app.post("/gpt/compliance")
async def gpt_compliance(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("COMPLIANCE", task)

@app.post("/gpt/adsai")
async def gpt_adsai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("ADSAI", task)

@app.post("/gpt/opsai")
async def gpt_opsai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("OPSAI", task)

@app.post("/gpt/csai")
async def gpt_csai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("CSAI", task)

@app.post("/gpt/pricingai")
async def gpt_pricingai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("PRICINGAI", task)

@app.post("/gpt/partnerai")
async def gpt_partnerai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("PARTNERAI", task)

@app.post("/gpt/hiringai")
async def gpt_hiringai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("HIRINGAI", task)

@app.post("/gpt/financeai")
async def gpt_financeai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("FINANCEAI", task)

@app.post("/gpt/auditai")
async def gpt_auditai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("AUDITAI", task)

@app.post("/gpt/labsai")
async def gpt_labsai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("LABSAI", task)

# ---------- Daily report endpoint ----------
@app.post("/cron/daily-bff-report")
async def cron_daily_report(x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    report = {
        "headline": "Daily BFF Report",
        "sections": [
            {"title": "Top of Funnel", "metric": "Leads", "value": 42},
            {"title": "Revenue Forecast", "value": "$7,500 next 7 days", "notes": "Based on 5% conv."},
            {"title": "Content Plan", "value": "12 posts scheduled (Ocoya)"},
            {"title": "Stock Windows", "value": "7:45am, 11:55am, 3:35pm local"}
        ]
    }
    # Optionally email report - implement if desired with OAuth or email provider
    return {"status": "ok", "report": report}

# ---------- Run locally ----------
# To run:
# uvicorn main:app --host 0.0.0.0 --port 8000
