"""Configuration management for AI TTS Avatar (Voice Live API)."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Azure AI / Microsoft Foundry resource (Voice Live API)
    AZURE_AI_ENDPOINT: str = os.getenv("AZURE_AI_ENDPOINT", "")
    VOICE_LIVE_MODEL: str = os.getenv("VOICE_LIVE_MODEL", "gpt-realtime")

    # Optional BYOM (Bring Your Own Model) configuration.
    # See: https://learn.microsoft.com/azure/ai-services/speech-service/how-to-bring-your-own-model
    #   VOICE_BYOM_MODE  — profile: byom-azure-openai-realtime |
    #                       byom-azure-openai-chat-completion |
    #                       byom-foundry-anthropic-messages
    #   VOICE_BYOM_MODEL — your Foundry *deployment name* (overrides VOICE_LIVE_MODEL when BYOM is on)
    #   VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE — optional cross-resource override (resource name only, no domain)
    VOICE_BYOM_MODE: str = os.getenv("VOICE_BYOM_MODE", "byom-azure-openai-realtime")
    VOICE_BYOM_MODEL: str = os.getenv("VOICE_BYOM_MODEL", "")
    VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE: str = os.getenv("VOICE_BYOM_FOUNDRY_RESOURCE_OVERRIDE", "")

    PORT: int = int(os.getenv("PORT", "8000"))

    # UI defaults (must match an entry in AVATAR_CHARACTERS / PHOTO_AVATARS / VOICES below)
    DEFAULT_VIDEO_CHARACTER: str = os.getenv("DEFAULT_VIDEO_CHARACTER", "lisa")
    DEFAULT_PHOTO_CHARACTER: str = os.getenv("DEFAULT_PHOTO_CHARACTER", "isabella")
    DEFAULT_VOICE: str = os.getenv("DEFAULT_VOICE", "en-US-Ava:DragonHDLatestNeural")

    # Feature flags
    ENABLE_WEATHER_TOOL: bool = os.getenv("ENABLE_WEATHER_TOOL", "false").lower() in ("1", "true", "yes")
    ENABLE_BYOM_MODE: bool = os.getenv("ENABLE_BYOM_MODE", "false").lower() in ("1", "true", "yes")

    # Standard video avatar characters and their available styles.
    # Source: https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/standard-avatars
    #
    # Notes:
    #   - Rowan, Celine, Nia, Malik have no style variants (single appearance).
    #   - Lisa's other styles (graceful-sitting/standing, technical-sitting/standing)
    #     are NOT supported via the real-time API — only `casual-sitting` is listed.
    #   - Jeff is being retired (Dec 2026) and is omitted.
    AVATAR_CHARACTERS = [
        {"id": "rowan", "name": "Rowan", "styles": []},
        {"id": "celine", "name": "Celine", "styles": []},
        {"id": "nia", "name": "Nia", "styles": []},
        {"id": "malik", "name": "Malik", "styles": []},
        {"id": "harry", "name": "Harry", "styles": ["business", "casual", "youthful"]},
        {"id": "lisa", "name": "Lisa", "styles": ["casual-sitting"]},
        {"id": "lori", "name": "Lori", "styles": ["casual", "graceful", "formal"]},
        {"id": "max", "name": "Max", "styles": ["business", "casual", "formal"]},
        {"id": "meg", "name": "Meg", "styles": ["business", "casual", "formal"]},
    ]

    # Standard photo avatars (no styles — single appearance per character)
    # Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/standard-avatars
    PHOTO_AVATARS = [
        {"id": "adrian", "name": "Adrian"},
        {"id": "amara", "name": "Amara"},
        {"id": "amira", "name": "Amira"},
        {"id": "anika", "name": "Anika"},
        {"id": "bianca", "name": "Bianca"},
        {"id": "camila", "name": "Camila"},
        {"id": "carlos", "name": "Carlos"},
        {"id": "clara", "name": "Clara"},
        {"id": "darius", "name": "Darius"},
        {"id": "diego", "name": "Diego"},
        {"id": "elise", "name": "Elise"},
        {"id": "farhan", "name": "Farhan"},
        {"id": "faris", "name": "Faris"},
        {"id": "gabrielle", "name": "Gabrielle"},
        {"id": "hyejin", "name": "Hyejin"},
        {"id": "imran", "name": "Imran"},
        {"id": "isabella", "name": "Isabella"},
        {"id": "layla", "name": "Layla"},
        {"id": "liwei", "name": "Liwei"},
        {"id": "ling", "name": "Ling"},
        {"id": "marcus", "name": "Marcus"},
        {"id": "matteo", "name": "Matteo"},
        {"id": "rahul", "name": "Rahul"},
        {"id": "rana", "name": "Rana"},
        {"id": "ren", "name": "Ren"},
        {"id": "riya", "name": "Riya"},
        {"id": "sakura", "name": "Sakura"},
        {"id": "simone", "name": "Simone"},
        {"id": "zayd", "name": "Zayd"},
        {"id": "zoe", "name": "Zoe"},
    ]

    # English-only TTS voices for Voice Live.
    # Source: https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts
    #
    # Tiers (all use voice.type = "azure-standard" per Voice Live spec):
    #   - HD (Dragon) — highest quality, most natural. Limited to regions:
    #       eastus, eastus2, westus2, westeurope, swedencentral, centralindia, southeastasia
    #   - Multilingual — can speak many languages with the same voice persona.
    #   - Standard — classic neural voices, broad regional coverage.
    VOICES = [
        # ── US English — HD (Dragon) ──
        {"id": "en-US-Ava:DragonHDLatestNeural",     "name": "Ava HD (US, F)",     "type": "azure-standard"},
        {"id": "en-US-Andrew:DragonHDLatestNeural",  "name": "Andrew HD (US, M)",  "type": "azure-standard"},
        {"id": "en-US-Brian:DragonHDLatestNeural",   "name": "Brian HD (US, M)",   "type": "azure-standard"},
        {"id": "en-US-Davis:DragonHDLatestNeural",   "name": "Davis HD (US, M)",   "type": "azure-standard"},
        {"id": "en-US-Emma:DragonHDLatestNeural",    "name": "Emma HD (US, F)",    "type": "azure-standard"},
        {"id": "en-US-Aria:DragonHDLatestNeural",    "name": "Aria HD (US, F)",    "type": "azure-standard"},
        {"id": "en-US-Jenny:DragonHDLatestNeural",   "name": "Jenny HD (US, F)",   "type": "azure-standard"},
        {"id": "en-US-Nova:DragonHDLatestNeural",    "name": "Nova HD (US, F)",    "type": "azure-standard"},
        {"id": "en-US-Steffan:DragonHDLatestNeural", "name": "Steffan HD (US, M)", "type": "azure-standard"},
        # ── UK English — HD (Dragon) ──
        {"id": "en-GB-Ada:DragonHDLatestNeural",     "name": "Ada HD (UK, F)",     "type": "azure-standard"},
        {"id": "en-GB-Ollie:DragonHDLatestNeural",   "name": "Ollie HD (UK, M)",   "type": "azure-standard"},
        # ── Multilingual (can switch languages mid-utterance) ──
        {"id": "en-US-AvaMultilingualNeural",        "name": "Ava (US, F, Multilingual)",     "type": "azure-standard"},
        {"id": "en-US-AndrewMultilingualNeural",    "name": "Andrew (US, M, Multilingual)",  "type": "azure-standard"},
        {"id": "en-US-EmmaMultilingualNeural",      "name": "Emma (US, F, Multilingual)",    "type": "azure-standard"},
        {"id": "en-US-BrianMultilingualNeural",     "name": "Brian (US, M, Multilingual)",   "type": "azure-standard"},
        {"id": "en-GB-AdaMultilingualNeural",       "name": "Ada (UK, F, Multilingual)",     "type": "azure-standard"},
        {"id": "en-GB-OllieMultilingualNeural",     "name": "Ollie (UK, M, Multilingual)",   "type": "azure-standard"},
        # ── Standard regional ──
        {"id": "en-US-JennyNeural",                  "name": "Jenny (US, F)",      "type": "azure-standard"},
        {"id": "en-US-GuyNeural",                   "name": "Guy (US, M)",        "type": "azure-standard"},
        {"id": "en-GB-SoniaNeural",                 "name": "Sonia (UK, F)",      "type": "azure-standard"},
        {"id": "en-GB-RyanNeural",                  "name": "Ryan (UK, M)",       "type": "azure-standard"},
        {"id": "en-AU-NatashaNeural",               "name": "Natasha (AU, F)",    "type": "azure-standard"},
        {"id": "en-AU-WilliamNeural",               "name": "William (AU, M)",    "type": "azure-standard"},
        {"id": "en-IE-EmilyNeural",                 "name": "Emily (IE, F)",      "type": "azure-standard"},
        {"id": "en-IE-ConnorNeural",                "name": "Connor (IE, M)",     "type": "azure-standard"},
        {"id": "en-CA-ClaraNeural",                 "name": "Clara (CA, F)",      "type": "azure-standard"},
        {"id": "en-CA-LiamNeural",                  "name": "Liam (CA, M)",       "type": "azure-standard"},
    ]

    SYSTEM_PROMPT = (
        "You are a friendly, helpful AI assistant embodied as a lifelike avatar. "
        "Keep responses conversational and concise (2-3 sentences max) since they "
        "will be spoken aloud. Be warm and engaging. "
        "Always begin the conversation in English (en-US). If the user later "
        "speaks or asks you to switch to another language, you may follow their "
        "lead \u2014 but the initial greeting and any unsolicited response must be in English. "
    )

    if ENABLE_WEATHER_TOOL:
        SYSTEM_PROMPT += (
            "You can look up current weather conditions for any location using the "
            "get_weather tool — use it whenever the user asks about weather, "
            "temperature, or conditions in a place."
        )

    def validate(self) -> list[str]:
        """Return a list of missing required configuration keys."""
        errors = []
        if not self.AZURE_AI_ENDPOINT:
            errors.append("AZURE_AI_ENDPOINT")
        return errors


settings = Settings()
