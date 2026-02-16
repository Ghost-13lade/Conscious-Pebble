import io
import json
from pathlib import Path
from typing import Any, Dict, List

import gradio as gr
import httpx
import numpy as np
import soundfile as sf


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "true_voices.json"
SPEAK_URL = "http://localhost:8081/speak"

VOICES = [
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_michael",
    "am_adam",
    "am_eric",
    "am_liam",
    "am_onyx",
]


def display_name_from_voice(voice_id: str) -> str:
    value = str(voice_id or "").strip().lower()
    if value == "af_heart":
        return "Pebble"
    if value == "af_sky":
        return "Emily"
    token = value.split("_")[-1] if "_" in value else value
    token = token.replace("-", " ").strip()
    return token.title() if token else "Voice"


def _default_configs() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Pebble",
            "voice": "af_heart",
            "speed": 1.0,
            "pitch_shift": 0,
        }
    ]


def load_configs() -> List[Dict[str, Any]]:
    if not CONFIG_FILE.exists():
        configs = _default_configs()
        save_configs(configs)
        return configs

    try:
        payload = json.loads(CONFIG_FILE.read_text())
        configs = payload if isinstance(payload, list) else []
    except Exception:
        configs = []

    normalized: List[Dict[str, Any]] = []
    by_voice: Dict[str, Dict[str, Any]] = {}
    for cfg in configs:
        voice = str(cfg.get("voice", "")).strip() or "af_heart"
        if voice == "af":
            # Legacy alias: Emily now maps to af_sky to avoid missing af.pt runtime failures.
            voice = "af_sky"
        by_voice[voice] = {
            "name": display_name_from_voice(voice),
            "voice": voice,
            "speed": float(cfg.get("speed", 1.0)),
            "pitch_shift": float(cfg.get("pitch_shift", 0)),
        }

    if "af_heart" not in by_voice:
        by_voice["af_heart"] = _default_configs()[0]

    # Keep VOICES order first, then extras
    for voice in VOICES:
        if voice in by_voice:
            normalized.append(by_voice.pop(voice))
    for _, cfg in by_voice.items():
        normalized.append(cfg)

    if normalized != configs:
        save_configs(normalized)
    return normalized


def save_configs(configs: List[Dict[str, Any]]) -> None:
    CONFIG_FILE.write_text(json.dumps(configs, indent=2))


def _to_audio_tuple(wav_bytes: bytes):
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    if isinstance(data, np.ndarray) and data.ndim > 1:
        data = np.mean(data, axis=1)
    return int(sr), data


BASE_SAMPLE_RATE = 24000
MIN_PLAYBACK_RATE = 19950
MAX_PLAYBACK_RATE = 28050


def _rate_from_pitch_shift_stored(pitch_shift_value: float) -> int:
    # Backward-compatible: previous `pitch_shift` field now stores rate offset from 24k.
    return int(max(MIN_PLAYBACK_RATE, min(MAX_PLAYBACK_RATE, BASE_SAMPLE_RATE + float(pitch_shift_value or 0))))


def _pitch_shift_stored_from_rate(rate_hz: float) -> float:
    return float(rate_hz) - float(BASE_SAMPLE_RATE)


def test_voice(text: str, voice: str, speed: float, playback_rate_hz: float):
    if not text.strip():
        return None, "Error: text is required"

    try:
        payload = {
            "text": text,
            "voice": voice,
            "speed": float(speed),
            "pitch": 0,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(SPEAK_URL, json=payload)
        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = str(body.get("detail", "")).strip()
            except Exception:
                detail = response.text.strip()
            detail = detail or f"HTTP {response.status_code}"
            return None, f"Test failed ({response.status_code}): {detail}"

        _, data = _to_audio_tuple(response.content)
        out_rate = int(max(MIN_PLAYBACK_RATE, min(MAX_PLAYBACK_RATE, float(playback_rate_hz or BASE_SAMPLE_RATE))))
        return (out_rate, np.asarray(data, dtype=np.float32)), "OK"
    except Exception as e:
        return None, f"Test failed: {e}"


def load_config(selected_name: str):
    configs = load_configs()
    for cfg in configs:
        if str(cfg.get("name", "")).strip() == str(selected_name).strip():
            return (
                str(cfg.get("voice", "af_heart")),
                float(cfg.get("speed", 1.0)),
                _rate_from_pitch_shift_stored(float(cfg.get("pitch_shift", 0))),
            )
    return "af_heart", 1.0, BASE_SAMPLE_RATE


def save_new_config(name: str, voice: str, speed: float, playback_rate_hz: float):
    clean_voice = str(voice or "").strip()
    if not clean_voice:
        return "Error: Voice required"
    clean_name = display_name_from_voice(clean_voice)

    stored_pitch_shift = _pitch_shift_stored_from_rate(playback_rate_hz)

    configs = load_configs()
    for cfg in configs:
        if str(cfg.get("voice", "")).strip() == clean_voice:
            cfg.update(
                {
                    "name": clean_name,
                    "voice": clean_voice,
                    "speed": float(speed),
                    "pitch_shift": float(stored_pitch_shift),
                }
            )
            save_configs(configs)
            return f"Updated {clean_name} ({clean_voice})"

    configs.append(
        {
            "name": clean_name,
            "voice": clean_voice,
            "speed": float(speed),
            "pitch_shift": float(stored_pitch_shift),
        }
    )
    save_configs(configs)
    return f"Saved {clean_name} ({clean_voice})"


def refresh_choices():
    names = [str(c.get("name", "")).strip() for c in load_configs() if str(c.get("name", "")).strip()]
    if not names:
        names = ["Pebble"]
    return gr.Dropdown(choices=names, value=names[0])


with gr.Blocks(title="Pebble Voice Audition (Senses Thin Client)") as demo:
    gr.Markdown("# Pebble Voice Audition\nTune presets and save selectable voice configs.")

    initial_configs = load_configs()
    initial_names = [str(c.get("name", "")).strip() for c in initial_configs if str(c.get("name", "")).strip()]
    if not initial_names:
        initial_names = ["Pebble"]

    with gr.Row():
        load_dropdown = gr.Dropdown(
            label="Load Saved Config",
            choices=initial_names,
            value=initial_names[0],
        )
        refresh_btn = gr.Button("Refresh List")

    text = gr.Textbox(
        label="Test Text",
        value="Hey love, this is Pebble. How are you feeling today?",
        lines=4,
    )

    with gr.Row():
        voice_dropdown = gr.Dropdown(label="Kokoro Voice", choices=VOICES, value="af_heart")
        speed_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.01, label="Base Speed")
        pitch_slider = gr.Slider(MIN_PLAYBACK_RATE, MAX_PLAYBACK_RATE, value=BASE_SAMPLE_RATE, step=50, label="Playback Rate (Hz)")

    test_btn = gr.Button("Test via Senses Server")
    audio_out = gr.Audio(label="Preview")
    test_status = gr.Textbox(label="Test Status")

    with gr.Row():
        auto_name_box = gr.Textbox(label="Auto Name", interactive=False)
        save_btn = gr.Button("Save/Update Config")
        save_status = gr.Textbox(label="Save Status")

    voice_dropdown.change(lambda v: display_name_from_voice(v), inputs=voice_dropdown, outputs=auto_name_box)
    demo.load(lambda: display_name_from_voice("af_heart"), outputs=auto_name_box)

    test_btn.click(
        test_voice,
        inputs=[text, voice_dropdown, speed_slider, pitch_slider],
        outputs=[audio_out, test_status],
    )
    load_dropdown.change(load_config, inputs=load_dropdown, outputs=[voice_dropdown, speed_slider, pitch_slider])
    refresh_btn.click(refresh_choices, outputs=load_dropdown)
    save_btn.click(
        save_new_config,
        inputs=[auto_name_box, voice_dropdown, speed_slider, pitch_slider],
        outputs=save_status,
    )

demo.launch()
