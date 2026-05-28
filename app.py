"""AI TTS Avatar — FastAPI backend.

Bridges browser WebSocket ↔ Azure Voice Live SDK via VoiceSessionHandler.
Supports two modes: avatar (WebRTC video) and voice-only (audio via WebSocket).

Authentication: DefaultAzureCredential (Azure CLI / managed identity).
Required roles: Cognitive Services User + Azure AI User.
"""

import asyncio
import json
import logging
import time
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from azure.identity.aio import DefaultAzureCredential

from voice_handler import VoiceSessionHandler
from config import settings

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Active session tracking ──────────────────────────────────────────────────
_sessions: Dict[str, VoiceSessionHandler] = {}
_tasks: Dict[str, asyncio.Task] = {}

# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(title="AI TTS Avatar")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def no_cache_static(request: StarletteRequest, call_next):
    """Prevent browser caching of static assets (development convenience)."""
    response: StarletteResponse = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ── HTML page ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "characters": settings.AVATAR_CHARACTERS,
            "photo_avatars": settings.PHOTO_AVATARS,
            "voices": settings.VOICES,
            "default_video_character": settings.DEFAULT_VIDEO_CHARACTER,
            "default_photo_character": settings.DEFAULT_PHOTO_CHARACTER,
            "default_voice": settings.DEFAULT_VOICE,
            "system_prompt": settings.SYSTEM_PROMPT,
            "cache_bust": str(int(time.time())),
        },
    )


# ── WebSocket endpoint ───────────────────────────────────────────────────────
#
# Custom message protocol between browser and backend:
#
#   Browser → Backend                Backend → Browser
#   ───────────────────              ──────────────────────
#   start_session                    session_started
#   stop_session                     ice_servers
#   audio_chunk                      avatar_sdp_answer
#   send_text                        transcript_delta / transcript_done
#   avatar_sdp_offer                 response_created / response_done
#   interrupt                        speech_started / speech_stopped
#                                    audio_data  (voice-only)
#                                    error / session_error


@app.websocket("/ws/voicelive")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    cid = str(id(ws))
    logger.info(f"Client {cid} connected")

    try:
        while True:
            msg = json.loads(await ws.receive_text())
            await _route_message(cid, msg, ws)
    except WebSocketDisconnect:
        logger.info(f"Client {cid} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {cid}: {e}")
    finally:
        await _cleanup(cid)


async def _route_message(cid: str, msg: dict, ws: WebSocket):
    """Dispatch a browser message to the appropriate handler method."""
    t = msg.get("type")
    handler = _sessions.get(cid)

    if t == "start_session":
        await _start_session(cid, msg.get("config", {}), ws)
    elif t == "stop_session":
        await _cleanup(cid)
    elif t == "audio_chunk" and handler:
        await handler.send_audio(msg.get("data", ""))
    elif t == "send_text" and handler:
        await handler.send_text_message(msg.get("text", ""))
    elif t == "avatar_sdp_offer" and handler:
        await handler.send_avatar_sdp_offer(msg.get("clientSdp", ""))
    elif t == "interrupt" and handler:
        await handler.interrupt()
    else:
        logger.warning(f"Unknown or unroutable message: {t}")


async def _start_session(cid: str, config: dict, ws: WebSocket):
    """Create a VoiceSessionHandler and run it as a background task."""
    await _cleanup(cid)

    credential = DefaultAzureCredential()

    async def _send(msg: dict):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception as e:
            logger.error(f"Send to {cid} failed: {e}")

    # BYOM: when enabled, the BYOM deployment name *replaces* the model query param,
    # and the BYOM profile + (optional) cross-resource override are added as query params.
    use_byom = settings.ENABLE_BYOM_MODE and bool(settings.VOICE_BYOM_MODEL)
    if settings.ENABLE_BYOM_MODE and not settings.VOICE_BYOM_MODEL:
        logger.warning("ENABLE_BYOM_MODE is true but VOICE_BYOM_MODEL is empty — falling back to VOICE_LIVE_MODEL.")

    handler = VoiceSessionHandler(
        client_id=cid,
        endpoint=settings.AZURE_AI_ENDPOINT,
        model=settings.VOICE_BYOM_MODEL if use_byom else settings.VOICE_LIVE_MODEL,
        byom_mode=settings.VOICE_BYOM_MODE if use_byom else None,
        foundry_resource_override=settings.VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE or None,
        credential=credential,
        send_message=_send,
        config=config,
    )
    _sessions[cid] = handler
    _tasks[cid] = asyncio.create_task(handler.start())
    logger.info(f"Session started for {cid}")


async def _cleanup(cid: str):
    """Tear down session and cancel its background task."""
    handler = _sessions.pop(cid, None)
    if handler:
        await handler.stop()

    task = _tasks.pop(cid, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


# ── Available avatars ────────────────────────────────────────────────────────
@app.get("/api/avatars")
async def list_avatars():
    """Return all configured avatar characters (video + photo)."""
    return {
        "video": [
            {**c, "type": "video"} for c in settings.AVATAR_CHARACTERS
        ],
        "photo": [
            {**p, "type": "photo", "model": "vasa-1"} for p in settings.PHOTO_AVATARS
        ],
    }


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    missing = settings.validate()
    return {"status": "ok" if not missing else "misconfigured", "missing_keys": missing}


# ── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    missing = settings.validate()
    if missing:
        print(f"WARNING: Missing env vars: {', '.join(missing)}")

    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=True)
