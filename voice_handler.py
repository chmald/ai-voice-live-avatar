"""Voice Live session handler.

Manages a single Azure Voice Live SDK session with optional avatar (WebRTC).
Acts as a bridge between a browser WebSocket and the Voice Live API.

Two modes:
  - Avatar:     session includes AvatarConfig; video/audio delivered via WebRTC.
  - Voice-only: no avatar; audio relayed to browser as base64 PCM16 over WS.
"""

import asyncio
import base64
import logging
from typing import Any, Callable, Optional

from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AvatarConfig,
    AzureSemanticVad,
    AzureStandardVoice,
    AudioInputTranscriptionOptions,
    ClientEventSessionAvatarConnect,
    InputAudioFormat,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    UserMessageItem,
    InputTextContentPart,
    VideoCrop,
    VideoParams,
)

logger = logging.getLogger(__name__)


class VoiceSessionHandler:
    """Manages a single Voice Live session.

    Lifecycle:
      1. start()          — connect to Voice Live, configure session, enter event loop
      2. _setup_session()  — send session.update, wait for session.updated, extract ICE
      3. _process_events() — recv loop forwarding events to browser
      4. stop()            — tear down
    """

    def __init__(
        self,
        client_id: str,
        endpoint: str,
        model: str,
        credential: Any,
        send_message: Callable,
        config: dict,
    ):
        self.client_id = client_id
        self.endpoint = endpoint
        self.model = model
        self.credential = credential
        self.send_message = send_message
        self.config = config

        self.connection = None
        self.is_running = False
        self._avatar_enabled = config.get("avatarEnabled", True)
        self._pending_proactive = False
        self._audio_chunk_count = 0

    # ── Session lifecycle ────────────────────────────────────────────────

    async def start(self):
        """Connect to Voice Live and run the event loop."""
        try:
            self.is_running = True
            logger.info(f"Connecting — endpoint={self.endpoint}, model={self.model}")

            async with connect(
                endpoint=self.endpoint,
                credential=self.credential,
                model=self.model,
            ) as connection:
                self.connection = connection
                await self._setup_session(connection)
                await self._process_events(connection)

        except asyncio.CancelledError:
            logger.info(f"Session cancelled for {self.client_id}")
        except Exception as e:
            logger.error(f"Session error for {self.client_id}: {e}", exc_info=True)
            await self.send_message({"type": "session_error", "error": str(e)})
        finally:
            self.is_running = False
            self.connection = None

    async def stop(self):
        """Signal the session to stop."""
        self.is_running = False
        self.connection = None

    # ── Session configuration ────────────────────────────────────────────

    async def _setup_session(self, connection):
        """Configure voice, avatar, and turn detection; then notify browser.

        Flow: session.update → wait session.updated → extract ICE → notify browser.
        """
        cfg = self.config

        # Voice
        voice_name = cfg.get("voiceName", "en-US-AvaMultilingualNeural")
        voice = AzureStandardVoice(
            name=voice_name,
            temperature=0.8 if "Dragon" in voice_name else None,
        )

        # Turn detection
        turn_detection = AzureSemanticVad(
            threshold=0.3,
            prefix_padding_ms=300,
            speech_duration_ms=80,
            silence_duration_ms=500,
            interrupt_response=True,
            auto_truncate=True,
        )

        # Transcription
        transcription = AudioInputTranscriptionOptions(model="azure-speech", language="en")

        # Avatar (None when disabled)
        avatar = self._build_avatar_config() if self._avatar_enabled else None

        # Build and send session.update
        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=cfg.get("instructions") or None,
            voice=voice,
            avatar=avatar,
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            input_audio_transcription=transcription,
            turn_detection=turn_detection,
            input_audio_noise_reduction={"type": "azure_deep_noise_suppression"},
            input_audio_echo_cancellation={"type": "server_echo_cancellation"},
        )
        logger.info(f"Sending session.update (avatar={self._avatar_enabled})")
        await connection.session.update(session=session_config)

        # Wait for confirmation
        updated = await self._wait_for_event(connection, {ServerEventType.SESSION_UPDATED})
        if updated is None:
            raise ValueError("SESSION_UPDATED not received within timeout")

        session_id = getattr(getattr(updated, "session", None), "id", None)
        logger.info(f"Session configured — id={session_id}")

        # Relay ICE servers (avatar mode only)
        if self._avatar_enabled:
            await self._relay_ice_servers(updated)

        # Notify browser
        await self.send_message({
            "type": "session_started",
            "status": "success",
            "sessionId": session_id,
            "avatarEnabled": self._avatar_enabled,
        })

        # Proactive greeting
        if self._avatar_enabled:
            self._pending_proactive = True  # deferred until avatar WebRTC connects
        else:
            await self._send_proactive_greeting(connection, "voice-only")

    def _build_avatar_config(self) -> AvatarConfig:
        """Build AvatarConfig with video params and output_protocol.

        Video avatars include a style and video crop settings.
        Photo avatars need type="photo-avatar" and model="vasa-1" set
        via bracket notation (not in SDK model).
        """
        cfg = self.config
        avatar_type = cfg.get("avatarType", "video")
        character = cfg.get("character", "lisa")

        if avatar_type == "photo":
            avatar = AvatarConfig(
                character=character,
            )
            # Required for photo avatars — not in SDK model, use bracket notation
            avatar["type"] = "photo-avatar"
            avatar["model"] = "vasa-1"
        else:
            video = VideoParams(
                codec="h264",
                crop=VideoCrop(top_left=[560, 0], bottom_right=[1360, 1080]),
            )
            avatar = AvatarConfig(
                character=character,
                style=cfg.get("style", "casual-sitting"),
                video=video,
            )
        avatar["output_protocol"] = "webrtc"  # not in SDK model — bracket notation
        if avatar_type == "photo":
            avatar["scene"] = {
                "zoom": 1,
                "position_x": 0,
                "position_y": 0,
                "rotation_x": 0,
                "rotation_y": 0,
                "rotation_z": 0,
                "amplitude": 1,
            }

        return avatar

    async def _relay_ice_servers(self, session_updated_event):
        """Extract ICE servers from session.updated and send to browser."""
        session = getattr(session_updated_event, "session", None)
        avatar_data = getattr(session, "avatar", None) if session else None
        raw_servers = getattr(avatar_data, "ice_servers", None) if avatar_data else None

        if not raw_servers:
            logger.warning("No ICE servers in session.updated response")
            return

        ice_servers = []
        for s in raw_servers:
            entry = {"urls": s.urls}
            if s.username:
                entry["username"] = s.username
            if s.credential:
                entry["credential"] = s.credential
            ice_servers.append(entry)

        await self.send_message({"type": "ice_servers", "iceServers": ice_servers})
        logger.info(f"Sent {len(ice_servers)} ICE server(s) to browser")

    async def _send_proactive_greeting(self, connection, context: str):
        """Trigger the model to speak a proactive greeting."""
        try:
            logger.info(f"Sending proactive greeting ({context})")
            await connection.response.create()
        except Exception as e:
            logger.error(f"Proactive greeting failed: {e}")

    # ── Event loop ───────────────────────────────────────────────────────

    async def _process_events(self, connection):
        """Receive events from Voice Live and relay to browser.

        Uses manual recv() so a single malformed event doesn't kill the loop.
        """
        while self.is_running:
            try:
                event = await connection.recv()
            except (ConnectionError, OSError) as e:
                logger.warning(f"Recv error (continuing): {type(e).__name__}: {e}")
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Connection error: {e}")
                break

            try:
                await self._handle_event(event, connection)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Event handler error ({getattr(event, 'type', '?')}): {e}")

    async def _handle_event(self, event, connection):
        """Dispatch a single Voice Live server event."""
        t = event.type

        # ── Audio ────────────────────────────────────────────────────────
        if t == ServerEventType.RESPONSE_AUDIO_DELTA:
            if not self._avatar_enabled and hasattr(event, "delta") and event.delta:
                await self.send_message({
                    "type": "audio_data",
                    "data": base64.b64encode(event.delta).decode(),
                    "format": "pcm16",
                    "sampleRate": 24000,
                })
            return  # skip logging for high-frequency audio events

        if t == ServerEventType.RESPONSE_AUDIO_DONE:
            await self.send_message({"type": "audio_done"})
            return

        # ── Transcript (assistant) ───────────────────────────────────────
        if t == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            if hasattr(event, "delta") and event.delta:
                await self.send_message({"type": "transcript_delta", "role": "assistant", "delta": event.delta})
            return  # skip logging for streaming deltas

        if t == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DONE:
            await self.send_message({"type": "transcript_done", "role": "assistant", "transcript": getattr(event, "transcript", "")})

        # ── Response lifecycle ───────────────────────────────────────────
        elif t == ServerEventType.RESPONSE_CREATED:
            rid = ""
            resp = getattr(event, "response", None)
            if resp and hasattr(resp, "id"):
                rid = resp.id
            await self.send_message({"type": "response_created", "responseId": rid})

        elif t == ServerEventType.RESPONSE_DONE:
            await self.send_message({"type": "response_done"})

        # ── Speech detection ─────────────────────────────────────────────
        elif t == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            item_id = getattr(event, "item_id", "") or getattr(event, "itemId", "")
            await self.send_message({"type": "speech_started", "itemId": item_id})

        elif t == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            await self.send_message({"type": "speech_stopped"})

        # ── User transcription ───────────────────────────────────────────
        elif t == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            transcript = getattr(event, "transcript", "")
            if transcript:
                item_id = getattr(event, "item_id", "") or getattr(event, "itemId", "")
                await self.send_message({"type": "transcript_done", "role": "user", "transcript": transcript, "itemId": item_id})

        # ── Avatar WebRTC signaling ──────────────────────────────────────
        elif t == ServerEventType.SESSION_AVATAR_CONNECTING:
            server_sdp = getattr(event, "server_sdp", "")
            if server_sdp:
                await self.send_message({"type": "avatar_sdp_answer", "serverSdp": server_sdp})
                logger.info("Relayed avatar SDP answer to browser")
                if self._pending_proactive:
                    self._pending_proactive = False
                    await self._send_proactive_greeting(connection, "after avatar connect")

        # ── Errors ───────────────────────────────────────────────────────
        elif t == ServerEventType.ERROR:
            logger.error(f"Voice Live error: {event}")
            await self.send_message({"type": "error", "error": str(event)})

        # ── Session updated (diagnostic) ─────────────────────────────────
        elif t == ServerEventType.SESSION_UPDATED:
            s = getattr(event, "session", None)
            if s:
                logger.info(
                    f"Session updated — audio_fmt={getattr(s, 'input_audio_format', '?')}/"
                    f"{getattr(s, 'output_audio_format', '?')}, "
                    f"vad={getattr(getattr(s, 'turn_detection', None), 'type', '?')}"
                )

        else:
            logger.debug(f"Unhandled event: {t}")

    # ── Public methods (called from app.py message router) ───────────────

    async def send_audio(self, audio_base64: str):
        """Forward mic audio from browser to Voice Live."""
        if not self.connection or not self.is_running:
            return
        try:
            self._audio_chunk_count += 1
            if self._audio_chunk_count <= 3 or self._audio_chunk_count % 200 == 0:
                logger.info(f"Audio chunk #{self._audio_chunk_count} (len={len(audio_base64)})")
            await self.connection.input_audio_buffer.append(audio=audio_base64)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    async def send_text_message(self, text: str):
        """Send a text message and trigger a response."""
        if not self.connection:
            return
        try:
            item = UserMessageItem(content=[InputTextContentPart(text=text)])
            await self.connection.conversation.item.create(item=item)
            await self.connection.response.create()
        except Exception as e:
            logger.error(f"Error sending text: {e}")

    async def send_avatar_sdp_offer(self, client_sdp: str):
        """Forward browser's SDP offer (base64-encoded JSON) to Voice Live.

        Expected format from JS: btoa(JSON.stringify(RTCSessionDescription))
        """
        if not self.connection:
            return
        try:
            if client_sdp.startswith("v="):
                logger.error("Received raw SDP — expected base64. Browser cache may be stale.")
            avatar_connect = ClientEventSessionAvatarConnect(client_sdp=client_sdp)
            await self.connection.send(avatar_connect)
            logger.info(f"Sent avatar SDP offer ({len(client_sdp)} chars)")
        except Exception as e:
            logger.error(f"Error sending avatar SDP: {e}")

    async def interrupt(self):
        """Cancel the current response (barge-in)."""
        if not self.connection:
            return
        try:
            await self.connection.response.cancel()
            await self.send_message({"type": "stop_playback", "reason": "manual_interrupt"})
        except Exception as e:
            logger.error(f"Error interrupting: {e}")

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _wait_for_event(self, connection, wanted: set, timeout: float = 15.0):
        """Block until one of the wanted event types arrives."""
        async def _recv():
            async for event in connection:
                if event.type in wanted:
                    return event
                await self._handle_event(event, connection)
            return None

        try:
            return await asyncio.wait_for(_recv(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for {wanted}")
            raise
