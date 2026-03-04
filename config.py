"""Configuration management for AI TTS Avatar (Voice Live API)."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Azure AI / Microsoft Foundry resource (Voice Live API)
    AZURE_AI_ENDPOINT: str = os.getenv("AZURE_AI_ENDPOINT", "")
    VOICE_LIVE_MODEL: str = os.getenv("VOICE_LIVE_MODEL", "gpt-4o-realtime")

    PORT: int = int(os.getenv("PORT", "8000"))

    # Standard video avatar characters and their available styles
    # Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/standard-avatars
    # Note: lisa-graceful-sitting, lisa-graceful-standing, lisa-technical-sitting,
    # and lisa-technical-standing are NOT supported via the real-time API.
    # Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/standard-avatars
    AVATAR_CHARACTERS = [
        {"id": "harry", "name": "Harry", "styles": ["business", "casual", "youthful"]},
        {"id": "jeff", "name": "Jeff", "styles": ["business", "formal"]},
        {"id": "lisa", "name": "Lisa", "styles": ["casual-sitting"]},
        {"id": "lori", "name": "Lori", "styles": ["casual", "graceful", "formal"]},
        {"id": "max", "name": "Max", "styles": ["business", "casual", "formal"]},
        {"id": "meg", "name": "Meg", "styles": ["formal", "casual", "business"]},
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

    # Available TTS voices (Azure standard + HD voices for Voice Live)
    VOICES = [
        {"id": "en-US-Ava:DragonHDLatestNeural", "name": "Ava HD", "type": "azure-standard"},
        {"id": "en-US-AvaMultilingualNeural", "name": "Ava (Multilingual)", "type": "azure-standard"},
        {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew (Multilingual)", "type": "azure-standard"},
        {"id": "en-US-EmmaMultilingualNeural", "name": "Emma (Multilingual)", "type": "azure-standard"},
        {"id": "en-US-BrianMultilingualNeural", "name": "Brian (Multilingual)", "type": "azure-standard"},
        {"id": "en-US-JennyNeural", "name": "Jenny", "type": "azure-standard"},
        {"id": "en-US-GuyNeural", "name": "Guy", "type": "azure-standard"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "type": "azure-standard"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (UK)", "type": "azure-standard"},
    ]

    SYSTEM_PROMPT = (
        "You are a friendly, helpful AI assistant embodied as a lifelike avatar. "
        "Keep responses conversational and concise (2-3 sentences max) since they "
        "will be spoken aloud. Be warm and engaging."
    )

    def validate(self) -> list[str]:
        """Return a list of missing required configuration keys."""
        errors = []
        if not self.AZURE_AI_ENDPOINT:
            errors.append("AZURE_AI_ENDPOINT")
        return errors


settings = Settings()
