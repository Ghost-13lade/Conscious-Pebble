import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:8080/v1")
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL", "your-model-name-here"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_KEY_HERE")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "")

# Shared service endpoints (for multi-bot architecture)
SENSES_BASE_URL = os.getenv("SENSES_BASE_URL", "http://localhost:8081")
SENSES_HEAR_PATH = os.getenv("SENSES_HEAR_PATH", "/hear")
SENSES_SPEAK_PATH = os.getenv("SENSES_SPEAK_PATH", "/speak")

# Model ids passed to the senses service
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo")
KOKORO_MODEL = os.getenv("KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16")
