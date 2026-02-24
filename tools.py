from __future__ import annotations

import json
import httpx
from pathlib import Path
from typing import Dict, List, Optional


VOICE_CONFIG_PATH = Path(__file__).resolve().parent / "voice_config.json"
BOTS_CONFIG_PATH = Path(__file__).resolve().parent / "bots_config.json"


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


# =============================================================================
# MULTI-BOT MANAGEMENT
# =============================================================================

def get_bots_config() -> Dict[str, dict]:
    """Get all bots configuration from bots_config.json.
    
    Returns:
        Dict mapping bot_name -> {token, user_id, voice_name, voice_mode, telegram_id}
    """
    try:
        if BOTS_CONFIG_PATH.exists():
            return json.loads(BOTS_CONFIG_PATH.read_text())
    except Exception:
        pass
    # Default fallback bot
    return {"Pebble": {
        "token": "",
        "user_id": "",
        "voice_name": "Pebble",
        "voice_mode": "Text Only",
        "telegram_id": None,
    }}


def save_bots_config(bots: Dict[str, dict]) -> None:
    """Save all bots configuration to bots_config.json."""
    BOTS_CONFIG_PATH.write_text(json.dumps(bots, indent=2))


def get_bot_names() -> List[str]:
    """Get list of all configured bot names."""
    return list(get_bots_config().keys())


def get_bot_config(bot_name: str) -> Optional[dict]:
    """Get configuration for a specific bot."""
    bots = get_bots_config()
    return bots.get(bot_name)


def add_bot(name: str, token: str = "", user_id: str = "", 
            voice_name: str = "Pebble", voice_mode: str = "Text Only",
            telegram_id: str = None) -> bool:
    """Add a new bot configuration.
    
    Returns:
        True if successful, False if bot name already exists.
    """
    bots = get_bots_config()
    if name in bots:
        return False
    bots[name] = {
        "token": token,
        "user_id": user_id,
        "voice_name": voice_name,
        "voice_mode": voice_mode,
        "telegram_id": telegram_id,
    }
    save_bots_config(bots)
    return True


def update_bot(name: str, token: str = None, user_id: str = None,
               voice_name: str = None, voice_mode: str = None,
               telegram_id: str = None) -> bool:
    """Update an existing bot configuration.
    
    Returns:
        True if successful, False if bot doesn't exist.
    """
    bots = get_bots_config()
    if name not in bots:
        return False
    if token is not None:
        bots[name]["token"] = token
    if user_id is not None:
        bots[name]["user_id"] = user_id
    if voice_name is not None:
        bots[name]["voice_name"] = voice_name
    if voice_mode is not None:
        bots[name]["voice_mode"] = voice_mode
    if telegram_id is not None:
        bots[name]["telegram_id"] = telegram_id
    save_bots_config(bots)
    return True


def delete_bot(name: str) -> bool:
    """Delete a bot configuration.
    
    Returns:
        True if successful, False if bot doesn't exist.
    """
    bots = get_bots_config()
    if name not in bots:
        return False
    del bots[name]
    save_bots_config(bots)
    return True


def rename_bot(old_name: str, new_name: str) -> bool:
    """Rename a bot.
    
    Returns:
        True if successful, False if old bot doesn't exist or new name already exists.
    """
    bots = get_bots_config()
    if old_name not in bots or new_name in bots:
        return False
    bots[new_name] = bots.pop(old_name)
    save_bots_config(bots)
    return True


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
