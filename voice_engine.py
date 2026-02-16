import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import librosa
import numpy as np

from config import (
    KOKORO_MODEL,
    SENSES_BASE_URL,
    SENSES_HEAR_PATH,
    SENSES_SPEAK_PATH,
    WHISPER_MODEL,
)


BASE_DIR = Path(__file__).resolve().parent
VOICE_CONFIG_FILE = BASE_DIR / "true_voices.json"


def load_voice_configs() -> List[Dict[str, Any]]:
    if not VOICE_CONFIG_FILE.exists():
        return []
    try:
        payload = json.loads(VOICE_CONFIG_FILE.read_text())
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def default_voice_name() -> str:
    configs = load_voice_configs()
    if configs:
        name = str(configs[0].get("name", "")).strip()
        if name:
            return name
    return "Pebble"


def resolve_voice_preset(active_voice_name: str) -> Dict[str, Any]:
    fallback = {
        "name": active_voice_name or default_voice_name(),
        "voice": "af_heart",
        "speed": 1.0,
        "pitch_shift": 0,
    }
    for cfg in load_voice_configs():
        if str(cfg.get("name", "")).strip() == active_voice_name:
            return {
                "name": str(cfg.get("name", fallback["name"])),
                "voice": str(cfg.get("voice", fallback["voice"])),
                "speed": float(cfg.get("speed", fallback["speed"])),
                "pitch_shift": float(cfg.get("pitch_shift", fallback["pitch_shift"])),
            }
    return fallback


def _build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def transcribe_audio_file(audio_path: str) -> Optional[str]:
    try:
        endpoint = _build_url(SENSES_BASE_URL, SENSES_HEAR_PATH)
        with open(audio_path, "rb") as f:
            files = {
                "file": (
                    Path(audio_path).name,
                    f.read(),
                    "application/octet-stream",
                )
            }
        data = {"model": WHISPER_MODEL}

        with httpx.Client(timeout=180.0) as client:
            response = client.post(endpoint, files=files, data=data)
            response.raise_for_status()
            payload = response.json()

        text = str(payload.get("text", "")).strip()
        return text or None
    except Exception as e:
        print(f"[Voice Engine] Transcription server call failed: {e}")
        return None


def extract_emotion_tag(audio_path: str) -> str:
    """Lightweight acoustic heuristic tag for prompt enrichment."""
    try:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        if y.size == 0:
            return "neutral"
        rms = float(np.mean(librosa.feature.rms(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        duration = float(len(y) / sr)

        if rms < 0.02:
            return "soft, low-energy"
        if rms > 0.08 and zcr > 0.09:
            return "energetic, excited"
        if duration > 8 and rms < 0.05:
            return "reflective, calm"
        return "warm, neutral"
    except Exception:
        return "neutral"


def _emotion_speed_multiplier(emotion: str) -> float:
    value = str(emotion or "neutral").strip().lower()
    if value in {"excited", "happy", "angry"}:
        return 1.15
    if value in {"sad", "tired", "thoughtful"}:
        return 0.85
    return 1.0


def synthesize_voice_bytes(
    text: str,
    active_voice_name: str,
    detected_emotion: str = "neutral",
) -> Optional[io.BytesIO]:
    if not text.strip():
        return None

    cfg = resolve_voice_preset(active_voice_name)
    voice = str(cfg.get("voice", "af_heart"))
    base_speed = float(cfg.get("speed", 1.0))
    pitch_shift = float(cfg.get("pitch_shift", 0))
    multiplier = _emotion_speed_multiplier(detected_emotion)
    speed = max(0.5, min(1.5, base_speed * multiplier))

    try:
        endpoint = _build_url(SENSES_BASE_URL, SENSES_SPEAK_PATH)
        payload = {
            "model": KOKORO_MODEL,
            "text": text,
            "voice": voice,
            "speed": speed,
            "pitch": pitch_shift,
        }

        with httpx.Client(timeout=180.0) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = response.json()
            # Support {"audio_base64":"..."} style APIs if used.
            b64 = body.get("audio_base64")
            if isinstance(b64, str) and b64:
                import base64

                return io.BytesIO(base64.b64decode(b64))
            print("[Voice Engine] Kokoro server returned JSON without audio bytes")
            return None

        return io.BytesIO(response.content)
    except Exception as e:
        print(f"[Voice Engine] TTS server call failed: {e}")
        return None
