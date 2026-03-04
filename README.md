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

### Supported regions for avatar

eastus2, northeurope, southcentralus, southeastasia, swedencentral, westeurope, westus2

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

Edit `.env`:

```env
AZURE_AI_ENDPOINT=https://your-resource.services.ai.azure.com
VOICE_LIVE_MODEL=gpt-4o-realtime
PORT=8000
```

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

## License

MIT
