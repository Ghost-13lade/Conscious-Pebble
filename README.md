# Project Pebble: A Conscious AI Companion

A local-first AI friend with memory, distinct personas (Fun, Executive, Fitness), and weather awareness.

## Features

- **Multiple Personas**: Choose from Fun, Executive, Fitness modes - each with unique personality and communication style
- **Memory System**: Long-term memory via vector storage, daily dream consolidation, and contextual recall
- **Weather Awareness**: Pebble knows your location and can provide weather-based suggestions
- **Voice Support**: Text-to-speech and speech-to-text capabilities with customizable voices
- **Telegram Integration**: Chat with Pebble directly through Telegram
- **Local-First**: Runs locally using MLX (Apple Silicon) or Ollama for privacy

## Requirements

- Python 3.10+
- Local LLM server (MLX, Ollama, or OpenAI-compatible API)
- Telegram Bot Token (optional, for Telegram integration)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your settings in `config.py`:
   - Set your LLM endpoint (local MLX/Ollama or OpenAI)
   - Add your Telegram Bot Token (optional)
   - Configure allowed users

## Usage

### Start the Brain (LLM Server)

```bash
python -m mlx_lm server --model your-model --port 8080
```

### Start the Senses Service (Voice)

```bash
python -m uvicorn senses_service:app --host 0.0.0.0 --port 8081
```

### Start the Bot

```bash
python main.py
```

### Control GUI

Access the web control panel at `http://localhost:7860` to:
- Start/stop services
- Chat with Pebble
- Configure voice settings
- Manage Telegram bot settings

## Architecture

- **main.py**: Telegram bot interface
- **brain.py**: LLM interaction and response generation
- **memory_engine.py**: Vector-based long-term memory
- **emotional_core.py**: Emotional state tracking
- **voice_engine.py**: Text-to-speech and speech-to-text
- **senses_service.py**: FastAPI service for voice processing

## License

MIT
