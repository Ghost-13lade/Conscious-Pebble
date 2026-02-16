import io
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import mlx_whisper
from mlx_audio.tts.generate import load_model


app = FastAPI(title="Pebble Senses Service", version="1.0.0")


WHISPER_MODEL_ID = "mlx-community/whisper-large-v3-turbo"
KOKORO_MODEL_ID = "mlx-community/Kokoro-82M-bf16"


# Keep models warm in memory
WHISPER_WARMED = False
KOKORO_MODEL = None


def _warm_models() -> None:
    global WHISPER_WARMED, KOKORO_MODEL
    if not WHISPER_WARMED:
        try:
            # Warm cache path for first-use latency reduction.
            _ = mlx_whisper.transcribe(
                np.zeros(1600, dtype=np.float32),
                path_or_hf_repo=WHISPER_MODEL_ID,
                verbose=False,
            )
            WHISPER_WARMED = True
        except Exception:
            # Will retry on real request.
            WHISPER_WARMED = False

    try:
        KOKORO_MODEL = load_model(KOKORO_MODEL_ID)
    except Exception:
        KOKORO_MODEL = None


@app.on_event("startup")
async def startup_event() -> None:
    _warm_models()


class SpeakRequest(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0
    model: str = KOKORO_MODEL_ID
    pitch: float = 0.0


@app.get("/")
async def root() -> dict:
    return {
        "service": "brook-senses",
        "whisper_model": WHISPER_MODEL_ID,
        "kokoro_model": KOKORO_MODEL_ID,
        "kokoro_available": KOKORO_MODEL is not None,
    }


@app.post("/hear")
async def hear(
    file: UploadFile = File(...),
    model: str = Form(WHISPER_MODEL_ID),
) -> dict:
    try:
        data = await file.read()
        suffix = Path(file.filename or "audio.wav").suffix or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        result = mlx_whisper.transcribe(
            tmp_path,
            path_or_hf_repo=model or WHISPER_MODEL_ID,
            verbose=False,
        )
        text = str(result.get("text", "")).strip() if isinstance(result, dict) else str(result).strip()
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"hear failed: {e}")


@app.post("/speak")
async def speak(payload: SpeakRequest):
    global KOKORO_MODEL

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    if KOKORO_MODEL is None:
        try:
            KOKORO_MODEL = load_model(payload.model or KOKORO_MODEL_ID)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"MLX Kokoro load failed: {e}")

    try:
        voice = (payload.voice or "").strip() or "af_heart"
        results = list(
            KOKORO_MODEL.generate(
                text=payload.text,
                voice=voice,
                speed=float(payload.speed or 1.0),
            )
        )
        if not results:
            raise RuntimeError("MLX Kokoro returned no audio frames")

        audio_chunks = [np.array(r.audio, dtype=np.float32) for r in results]
        audio_np = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
        sample_rate = int(getattr(results[0], "sample_rate", 24000))

        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_np, sample_rate, format="WAV")
        wav_buffer.seek(0)
        return Response(content=wav_buffer.read(), media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"speak failed: {e}")
