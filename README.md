# AI TTS Avatar

Real-time AI voice assistant with an optional lifelike avatar, powered by [Azure Voice Live API](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live-how-to).

![Python](https://img.shields.io/badge/Python-FastAPI-009688?logo=fastapi&logoColor=white)
![Azure](https://img.shields.io/badge/Azure-Voice%20Live-0078D4?logo=microsoftazure&logoColor=white)

## Features

- **Avatar mode** — WebRTC-streamed photorealistic avatar (Lisa, Harry, Max, Lori)
- **Voice-only mode** — Same AI conversation without the avatar video
- **Voice input** — Mic capture at 24 kHz via AudioWorklet, noise/echo cancellation server-side
- **Text input** — Type messages for the AI to respond to
- **Multiple voices** — Azure standard + HD (Dragon) voices
- **Proactive greeting** — The assistant speaks first when a session starts
- **BYOM (Bring Your Own Model)** — Point at a custom Foundry deployment (Azure OpenAI realtime / chat completion / Anthropic Claude)
- **Optional weather tool** — Function-calling demo using browser geolocation
- **DefaultAzureCredential** — Keyless auth via Azure CLI or managed identity

## Architecture

```
Browser ←WebSocket→ FastAPI backend ←SDK→ Azure Voice Live API
                                              ↕ (avatar mode)
Browser ←─── WebRTC video/audio ───── Azure Avatar Service
```

| File | Purpose |
|---|---|
| `app.py` | FastAPI server, WebSocket message router, session management |
| `voice_handler.py` | `VoiceSessionHandler` — Voice Live SDK session, event relay |
| `config.py` | Settings from environment variables |
| `static/js/app.js` | Browser client — WebRTC, mic capture, audio playback, UI |
| `static/js/audio-processor.js` | AudioWorklet for 24 kHz PCM16 mic capture |
| `templates/index.html` | Single-page UI (Jinja2 template) |
| `static/css/style.css` | Dark-theme application styles |

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.10+ |
| Azure subscription | [Free account](https://azure.microsoft.com/free/) |
| Microsoft Foundry resource | In a [supported region](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar) |
| Azure CLI | For `az login` authentication |
| RBAC roles | **Cognitive Services User** + **Azure AI User** on your Foundry resource |

## Support matrix

This project depends on three Azure capabilities, each with its own regional footprint. **Your Foundry resource must be created in a region that supports every feature you plan to use.** Pick a region from the recommendations below based on which features you enable.

### Feature → requirement

| Feature in this app | Azure capability | Required? |
|---|---|---|
| Voice-only conversation | Voice Live API (built-in `gpt-realtime`) | Always |
| Avatar video (Lisa, Harry, Max, Lori, Meg, etc.) | TTS Real-time Avatar | When **Enable Avatar** is on |
| HD (Dragon) voices — e.g. `en-US-Ava:DragonHDLatestNeural` | Azure Neural HD voices | When selecting an `HD` voice |
| Standard / Multilingual voices | Azure Neural TTS (broad coverage) | When selecting a non-HD voice |
| BYOM (`byom-azure-openai-realtime`, `…-chat-completion`) | Azure OpenAI deployment in your Foundry resource | When `ENABLE_BYOM_MODE=true` |
| BYOM (`byom-foundry-anthropic-messages`) | Anthropic model on Foundry (preview) | When using Claude via BYOM |
| Weather tool | Open-Meteo (keyless, no region) | When `ENABLE_WEATHER_TOOL=true` |

### Region × feature matrix

✅ = supported · ❌ = not supported · ⚠️ = check docs (changes frequently)

| Region | Voice Live API | TTS Avatar (real-time) | HD (Dragon) voices | Standard / Multilingual TTS |
|---|:---:|:---:|:---:|:---:|
| `eastus`           | ⚠️ | ❌ | ✅ | ✅ |
| `eastus2`          | ✅ | ✅ | ✅ | ✅ |
| `westus2`          | ✅ | ✅ | ✅ | ✅ |
| `southcentralus`   | ⚠️ | ✅ | ❌ | ✅ |
| `northeurope`      | ⚠️ | ✅ | ❌ | ✅ |
| `westeurope`       | ✅ | ✅ | ✅ | ✅ |
| `swedencentral`    | ✅ | ✅ | ✅ | ✅ |
| `southeastasia`    | ✅ | ✅ | ✅ | ✅ |
| `centralindia`     | ✅ | ❌ | ✅ | ✅ |
| All other Speech regions | ❌ | ❌ | ❌ | ✅ |

Sources (authoritative — verify before deploying):
- [Azure Speech regions — Voice Live tab](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=voicelive)
- [Azure Speech regions — TTS Avatar tab](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar)
- [HD voice region availability](https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts)
- [Voice Live overview & supported models](https://learn.microsoft.com/azure/ai-services/speech-service/voice-live)

### Recommended deployments

| Scenario | Recommended regions | Why |
|---|---|---|
| **Full featured** (avatar + HD voices + Voice Live) | `eastus2`, `westus2`, `westeurope`, `swedencentral`, `southeastasia` | Only regions that support all three at once |
| **Voice-only, HD voices** | Any of the above, plus `eastus`, `centralindia` | HD voices without avatar |
| **Voice-only, no HD** | Any Voice Live region | Lowest cost / broadest availability |
| **EU data residency** | `westeurope`, `swedencentral`, `northeurope` | Data stays in EU geography |
| **APAC** | `southeastasia` | Only APAC region with full feature parity |

> Data residency: Azure Speech doesn't process or store your audio outside the region of your Foundry resource — pick a region that matches your compliance needs.

## Quick Start

```bash
# Clone and install
git clone <your-repo-url>
cd ai-tts-avatar
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your endpoint

# Authenticate
az login

# Run
python app.py
```

Open **http://localhost:8000** in Chrome or Edge.

## Configuration

Edit `.env` (copy from `.env.example`):

```env
# Required
AZURE_AI_ENDPOINT=https://your-resource.services.ai.azure.com

# Model served by Voice Live (default: gpt-realtime)
VOICE_LIVE_MODEL=gpt-realtime

# Server port (default: 8000)
PORT=8000
```

### Optional: Bring Your Own Model (BYOM)

Use a custom model deployment from your Foundry resource instead of the built-in `VOICE_LIVE_MODEL`.
See the [BYOM docs](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-bring-your-own-model) for full details.

```env
ENABLE_BYOM_MODE=true
# Profile — pick one to match your deployment type:
#   byom-azure-openai-realtime         (e.g. gpt-realtime, gpt-realtime-mini)
#   byom-azure-openai-chat-completion  (e.g. gpt-5, gpt-4.1, model router)
#   byom-foundry-anthropic-messages    (e.g. claude-sonnet-4.6) — preview
VOICE_BYOM_MODE=byom-azure-openai-realtime

# Deployment NAME from the Foundry portal (not the underlying model id)
VOICE_BYOM_MODEL=my-gpt-realtime-deployment

# Optional: target a deployment in a DIFFERENT Foundry resource.
# Resource name only — no domain. e.g. "my-other-foundry"
VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE=
```

When BYOM is enabled, `VOICE_BYOM_MODEL` becomes the `model` query param and `VOICE_LIVE_MODEL` is ignored. The connection URL gets `profile=<VOICE_BYOM_MODE>` (and optionally `foundry-resource-override=<...>`) appended.

**Cross-resource note:** if you set `VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE`, the Voice Live Foundry resource needs its system-assigned managed identity granted the **Foundry User** role on the *model's* Foundry resource. See the docs above for the exact `az` commands.

### Optional: Weather tool

Set `ENABLE_WEATHER_TOOL=true` to expose a `get_weather` function the model can call. Uses the browser's geolocation when the user says "near me".

## Usage

1. Select avatar character, style, and voice in the sidebar
2. Toggle **Enable Avatar** on/off (off = voice-only mode for faster testing)
3. Click **Start Avatar** to connect
4. Type a message or click the mic to speak
5. The AI responds through the avatar (or audio only)

## Troubleshooting

| Issue | Solution |
|---|---|
| Session error on connect | Check `AZURE_AI_ENDPOINT` in `.env`; run `az login` |
| Avatar fails, voice works | Ensure region supports TTS avatar; try voice-only first |
| No audio/video | Allow mic/camera in browser; use Chrome or Edge |
| Stale JS behavior | Hard refresh (Ctrl+Shift+R) — no-cache middleware should handle this |
| BYOM connect fails | Verify `VOICE_BYOM_MODEL` matches a real **deployment name** in the Foundry portal, and that the deployment's profile matches `VOICE_BYOM_MODE` |
| BYOM 401/403 with override | When using `VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE`, grant the Voice Live resource's managed identity **Foundry User** on the model resource |

## License

MIT
