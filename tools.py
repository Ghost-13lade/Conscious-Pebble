from __future__ import annotations

import json
import httpx
from pathlib import Path


VOICE_CONFIG_PATH = Path(__file__).resolve().parent / "voice_config.json"


def get_voice_config() -> dict:
    """Get voice settings from voice_config.json"""
    try:
        if VOICE_CONFIG_PATH.exists():
            return json.loads(VOICE_CONFIG_PATH.read_text())
    except Exception:
        pass
    return {"voice_enabled": False, "voice_name": "Pebble"}


def set_voice_config(voice_enabled: bool = None, voice_name: str = None) -> None:
    """Update voice settings in voice_config.json"""
    config = get_voice_config()
    if voice_enabled is not None:
        config["voice_enabled"] = voice_enabled
    if voice_name is not None:
        config["voice_name"] = voice_name
    VOICE_CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_current_weather(city: str) -> str:
    """Get current weather using wttr.in API."""
    if not city.strip():
        return "unknown weather"

    safe_city = city.strip().replace(" ", "+")
    url = f"https://wttr.in/{safe_city}?format=j1"

    try:
        # Try httpx first
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        # Fallback to urllib if httpx fails
        try:
            import urllib.request
            import ssl
            # Create unverified SSL context for wttr.in
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                import json
                payload = json.load(resp)
        except Exception as e:
            print(f"[Weather Error] Failed to fetch weather: {e}")
            return "unknown weather"

    try:
        current = payload.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C")
        weather_desc_arr = current.get("weatherDesc", [])
        condition = weather_desc_arr[0].get("value") if weather_desc_arr else None

        temp_text = f"{temp_c}°C" if temp_c is not None else "Unknown"
        condition_text = condition or "Unknown"
        return f"{condition_text}, {temp_text}"
    except Exception as e:
        print(f"[Weather Parse Error] {e}")
        return "unknown weather"


# Alias for backwards compatibility
def get_weather(city: str) -> str:
    return get_current_weather(city)
