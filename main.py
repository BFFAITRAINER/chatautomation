
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os, httpx

# ---------- Environment ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OCOYA_API_KEY  = os.getenv("OCOYA_API_KEY", "")
SYSTEME_API_KEY = os.getenv("SYSTEME_API_KEY", "")
GMAIL_API_KEY = os.getenv("GMAIL_API_KEY", "")  # if you proxy Gmail via a service
REPORT_SENDER = os.getenv("REPORT_SENDER", "reports@bffaitrainer.com")

if not os.getenv("ALLOW_UNAUTH", "true").lower() in ("true","1","yes"):
    # Optionally require a secret in x-bff-key for every call
    REQUIRED_KEY = os.getenv("BFF_MIDDLEWARE_KEY","")
else:
    REQUIRED_KEY = ""

def require_key(x_bff_key: Optional[str]):
    if REQUIRED_KEY and x_bff_key != REQUIRED_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------- App ----------
app = FastAPI(title="BFF Middleware v24", version="1.0.0")

@app.get("/health")
async def health():
    return {"ok": True, "service": "BFF Middleware v24"}

# ---------- Models ----------
class PublishPost(BaseModel):
    channel: str = Field(..., description="ocoya channel key or account id (e.g., linkedin, facebook, instagram, youtube, tiktok)")
    text: str
    media_url: Optional[str] = None
    schedule_iso: Optional[str] = None
    tags: Optional[List[str]] = None
    utm: Optional[Dict[str,str]] = None

class EmailMessage(BaseModel):
    to: str
    subject: str
    html: str

class SystemeContact(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: Optional[List[str]] = []
    campaign_id: Optional[str] = None

class LeadQuery(BaseModel):
    niche: str
    geo: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

# ---------- Helpers (stubs) ----------
async def post_to_ocoya(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal Ocoya relay. Replace '...' with your Ocoya API endpoint once provided."""
    if not OCOYA_API_KEY:
        return {"status":"skipped","reason":"OCOYA_API_KEY not set","echo":payload}
    # Example stub (replace with real call)
    # async with httpx.AsyncClient(timeout=30) as client:
    #     r = await client.post("https://api.ocoya.com/v1/schedule", headers={"Authorization": f"Bearer {OCOYA_API_KEY}"}, json=payload)
    #     r.raise_for_status()
    #     return r.json()
    return {"status":"ok","posted_via":"ocoya_stub","echo":payload}

async def systeme_upsert_contact(c: SystemeContact) -> Dict[str, Any]:
    if not SYSTEME_API_KEY:
        return {"status":"skipped","reason":"SYSTEME_API_KEY not set","contact":c.dict()}
    # Example stub — replace with real Systeme Public API endpoint/paths
    # async with httpx.AsyncClient(timeout=30) as client:
    #     r = await client.post("https://api.systeme.io/api/contacts",
    #         headers={"X-API-Key": SYSTEME_API_KEY},
    #         json={"email":c.email,"firstName":c.first_name,"lastName":c.last_name})
    #     r.raise_for_status()
    #     contact = r.json()
    #     for t in c.tags or []:
    #         await client.post(f"https://api.systeme.io/api/contacts/{contact['id']}/tags",
    #             headers={"X-API-Key": SYSTEME_API_KEY}, json={"tagName":t})
    #     return {"status":"ok","contact":contact}
    return {"status":"ok","contact_stub":c.dict()}

async def gmail_send(m: EmailMessage) -> Dict[str,Any]:
    # In production, use OAuth or a relay such as SendGrid/AWS SES.
    if not GMAIL_API_KEY:
        return {"status":"skipped","reason":"GMAIL_API_KEY not set","echo":m.dict()}
    return {"status":"ok","sent_via":"gmail_stub","echo":m.dict()}

# ---------- Core Integrations ----------
@app.post("/social/publish-ocoya")
async def social_publish_ocoya(post: PublishPost, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    res = await post_to_ocoya(post.dict())
    return res

@app.post("/systeme/contact")
async def systeme_contact(c: SystemeContact, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    res = await systeme_upsert_contact(c)
    return res

@app.post("/gmail/send")
async def gmail_send_route(m: EmailMessage, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    res = await gmail_send(m)
    return res

# ---------- Daily report (stock-style windows) ----------
@app.post("/cron/daily-bff-report")
async def cron_daily_report(x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    # Compose report (stub). In production, aggregate metrics & trending.
    report = {
        "headline": "Daily BFF Report",
        "sections": [
            {"title":"Top of Funnel","metric":"Leads","value":42},
            {"title":"Revenue Forecast","value":"$7,500 next 7 days","notes":"Based on 5% conv."},
            {"title":"Content Plan","value":"12 posts scheduled (Ocoya)"},
            {"title":"Stock Windows","value":"7:45am, 11:55am, 3:35pm local"}
        ]
    }
    # Email to Vince
    if REPORT_SENDER:
        await gmail_send(EmailMessage(
            to=os.getenv("REPORT_TO","vince@bffaitrainer.com"),
            subject="Daily BFF Report",
            html=f"<h2>{report['headline']}</h2><pre>{report}</pre>"
        ))
    return {"status":"ok","report":report}

# ---------- 24 GPT Employee endpoints (thin controllers) ----------
# Each endpoint accepts a JSON payload and returns a routed response.
# CRIS (manager) can call these in sequence.
class TaskPayload(BaseModel):
    brand: str = "bff"
    partner: Optional[str] = None
    intent: str
    data: Dict[str, Any] = {}

def ok(name, payload, extra=None):
    out = {"agent": name, "received": payload.dict() if hasattr(payload,"dict") else payload}
    if extra: out.update(extra)
    return out

@app.post("/gpt/cris")
async def gpt_cris(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    return ok("CRIS", task, {"next":"route to appropriate agent based on task.intent"})

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
    # Example: write to Systeme
    if "lead" in task.data:
        await systeme_upsert_contact(SystemeContact(email=task.data["lead"]["email"], tags=["lead_generated"]))
    return ok("LEADAI", task)

@app.post("/gpt/convertai")
async def gpt_convertai(task: TaskPayload, x_bff_key: Optional[str] = Header(None)):
    require_key(x_bff_key)
    # Example: publish via Ocoya
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
    # Example: add stock workflow hint
    return ok("REVENUEAI", task, {"hint":"includes stock-window content cadence & KPI rollups"})

# 12–24 extended roles
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

# ---------- Run (for local debug) ----------
# uvicorn main:app --host 0.0.0.0 --port 8000
