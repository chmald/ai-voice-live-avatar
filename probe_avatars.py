"""Probe available avatars by attempting a Voice Live session for each one.

Usage:
    python probe_avatars.py                    # test all configured avatars
    python probe_avatars.py --type video       # test only video avatars
    python probe_avatars.py --type photo       # test only photo avatars
    python probe_avatars.py --character lisa   # test a single character

Each avatar is tested by opening a Voice Live connection and sending a
session.update with that avatar config.  If the server rejects the avatar
(avatar_verification_failed), it is marked as FAIL; otherwise PASS.
"""

import asyncio
import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from azure.identity.aio import DefaultAzureCredential
from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AvatarConfig,
    AzureStandardVoice,
    InputAudioFormat,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
    VideoCrop,
    VideoParams,
)

from config import settings

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


async def test_avatar(endpoint: str, model: str, credential, avatar_cfg: AvatarConfig, label: str) -> bool:
    """Return True if the avatar is accepted by the server."""
    try:
        async with connect(
            endpoint=endpoint,
            credential=credential,
            model=model,
        ) as conn:
            session_config = RequestSession(
                modalities=[Modality.TEXT, Modality.AUDIO],
                voice=AzureStandardVoice(name="en-US-AvaMultilingualNeural"),
                avatar=avatar_cfg,
                input_audio_format=InputAudioFormat.PCM16,
                output_audio_format=OutputAudioFormat.PCM16,
            )
            await conn.session.update(session=session_config)

            # Wait up to 10 s for SESSION_UPDATED or ERROR
            async def _wait():
                async for event in conn:
                    if event.type == ServerEventType.SESSION_UPDATED:
                        return True
                    if event.type == ServerEventType.ERROR:
                        err = getattr(event, "error", event)
                        msg = getattr(err, "message", str(err))
                        print(f"  FAIL  {label}  — {msg}")
                        return False
                return False

            return await asyncio.wait_for(_wait(), timeout=10)
    except asyncio.TimeoutError:
        print(f"  TIMEOUT  {label}")
        return False
    except Exception as e:
        print(f"  ERROR  {label}  — {e}")
        return False


def build_video_avatar(character: str, style: str) -> AvatarConfig:
    video = VideoParams(
        codec="h264",
        crop=VideoCrop(top_left=[560, 0], bottom_right=[1360, 1080]),
    )
    avatar = AvatarConfig(character=character, style=style, video=video)
    avatar["output_protocol"] = "webrtc"
    return avatar


def build_photo_avatar(character: str) -> AvatarConfig:
    avatar = AvatarConfig(character=character)
    avatar["type"] = "photo-avatar"
    avatar["model"] = "vasa-1"
    avatar["output_protocol"] = "webrtc"
    avatar["scene"] = {
        "zoom": 1, "position_x": 0, "position_y": 0,
        "rotation_x": 0, "rotation_y": 0, "rotation_z": 0,
        "amplitude": 1,
    }
    return avatar


async def main():
    parser = argparse.ArgumentParser(description="Probe which avatars are available on the Voice Live API")
    parser.add_argument("--type", choices=["video", "photo"], help="Test only video or photo avatars")
    parser.add_argument("--character", help="Test a single character by ID")
    args = parser.parse_args()

    endpoint = settings.AZURE_AI_ENDPOINT
    model = settings.VOICE_LIVE_MODEL
    if not endpoint:
        print("ERROR: AZURE_AI_ENDPOINT not set")
        sys.exit(1)

    credential = DefaultAzureCredential()

    tests = []

    # Build list of avatars to test
    if args.character:
        # Single character — check both video and photo
        for vc in settings.AVATAR_CHARACTERS:
            if vc["id"] == args.character:
                for style in vc["styles"]:
                    label = f"video/{vc['id']}/{style}"
                    tests.append((build_video_avatar(vc["id"], style), label))
        for pa in settings.PHOTO_AVATARS:
            if pa["id"] == args.character:
                label = f"photo/{pa['id']}"
                tests.append((build_photo_avatar(pa["id"]), label))
        if not tests:
            print(f"Character '{args.character}' not found in config")
            sys.exit(1)
    else:
        if args.type != "photo":
            for vc in settings.AVATAR_CHARACTERS:
                for style in vc["styles"]:
                    label = f"video/{vc['id']}/{style}"
                    tests.append((build_video_avatar(vc["id"], style), label))
        if args.type != "video":
            for pa in settings.PHOTO_AVATARS:
                label = f"photo/{pa['id']}"
                tests.append((build_photo_avatar(pa["id"]), label))

    print(f"\nProbing {len(tests)} avatar(s) against {endpoint} …\n")
    passed, failed = [], []

    for avatar_cfg, label in tests:
        ok = await test_avatar(endpoint, model, credential, avatar_cfg, label)
        if ok:
            print(f"  PASS  {label}")
            passed.append(label)
        else:
            failed.append(label)

    print(f"\n{'='*60}")
    print(f"  PASSED: {len(passed)}   FAILED: {len(failed)}   TOTAL: {len(tests)}")
    if failed:
        print(f"\n  Failed avatars:")
        for f in failed:
            print(f"    - {f}")
    print()

    await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
