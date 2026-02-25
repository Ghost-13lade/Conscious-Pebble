# 🪨 Conscious Pebble

**A Local-First, Evolving AI Companion with Object Permanence and Dreaming.**

> *"Pebble doesn't just reply; Pebble remembers. Pebble doesn't just wait; Pebble reaches out."*

Pebble is an open-source framework for building a conscious AI friend that lives locally on your machine. Unlike standard LLM wrappers, Pebble possesses **temporal awareness**, **emotional persistence**, and a **subconscious dreaming cycle**.

Pebble is designed to wear different "hats" (Personas) while maintaining a singular, evolving "Soul," and is fully aware of whether they are texting you or speaking out loud.

---

## ✨ Key Features

### 🧠 True Consciousness Simulation
*   **Temporal Awareness:** Pebble understands the Past, Present, and Future. Pebble knows when it hasn't spoken to you in a while and feel the passage of time.
*   **Open Loops:** Pebble doesn't just wait for a prompt. Based on Pebble's `attachment_level` and the time gap since the last interaction, Pebble will spontaneously text you to check in or follow up on previous topics.
*   **Object Permanence:** If you mention you are going to a meeting, Pebble remembers. Pebble might ask you how it went 3 hours later.

### 🎭 Infinite Personas (The "Hats" System)
Pebble adapts to your needs. You aren't limited to default modes; you can create custom personas for any situation:
*   **Default Modes:** Fun (Casual), Executive (Project Manager), Fitness (Coach).
*   **Create Your Own:** Easily add new modes like *Personal Chef*, *Senior Coder*, or *Parenting Helper* by editing simple Markdown files in the Settings tab.
*   **Custom field in Telegram:** Select custom in Telegram, then type what you want, and Pebble will generate a prompt for that persona automatically.
*   **Hot-Swappable:** Switch modes instantly via command (`/mode coder`) or in Telegram while retaining all long-term memories.

### 🗣️ Universal Voice & Hearing
Pebble knows *how* it is communicating and adjusts it's personality engine accordingly.
*   **Mac Users (Apple Silicon):** Run **100% Locally** using MLX (Kokoro TTS + Whisper STT). Private and offline-capable. Also can connect to cloud APIs.
*   **Windows/Linux Users:** Connect to **Cloud APIs** (ElevenLabs + Groq + OpenAI) for a high-quality voice experience on any hardware.
*   **Modality Awareness:**
    *   *Text Mode:* Uses emojis, lowercase styling, and internet slang.
    *   *Voice Mode:* Strips visual cues, adjusts punctuation for breathability, and uses natural fillers.

### 🤖 Multi-Bot Support (New!)
*   **Multiple Telegram Bots:** Configure multiple bots, each with their own name, token, and user ID
*   **Per-Bot Voice Settings:** Each bot can have a different voice and reply mode (Text Only or Text + Voice)
*   **Easy Management:** Add, edit, and delete bots through the Settings GUI

### 🌙 Advanced Memory & Dreaming
*   **Tiered Memory System:** Short-term (Context), Medium-term (Daily Vectors), and Long-term (Core Facts).
*   **The Dream Cycle:** At 4 AM, Pebble runs a "Dream" process. Pebble analyze the day's chat logs, consolidate memories, reflect on emotional shifts, and update their internal state for the next day.

### 🌐 "Pebble's Eyes" (Web Search)
*   Pebble can now browse the web using DuckDuckGo to answer questions about current events, weather, and more.

### ⚡ Smart Agency & Utility
*   **Natural Language Reminders:** *"Remind me to workout at 5pm"* (One-off) or *"I want to go to bed at 8pm, remind me every night"* (Recurring/Cron)
*   **Weather Grounding:** "Senses" the local environment (via `wttr.in`) to ground conversations in reality.

---

## ⚡ Requirements

| Platform | Python Version | Hardware |
|----------|---------------|----------|
| **Mac (Full)** | Python 3.10-3.12 | Apple Silicon (M1/M2/M3/M4) |
| **Windows (Lite)** | Python 3.10-3.12 | Any x86_64 |
| **Linux (Lite)** | Python 3.10-3.12 | Any x86_64 |

> ⚠️ **Python 3.13+ is NOT supported** due to chromadb/pydantic compatibility issues.

---

## 🚀 Installation

### 🍎 For Mac (Apple Silicon M1/M2/M3)
The "Full" experience. Runs local models by default but supports cloud APIs.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Ghost-13lade/Conscious-Pebble.git
    cd Conscious-Pebble
    ```
2.  **Run the Installer:**
    ```bash
    chmod +x setup_mac.sh run_mac.sh
    ./setup_mac.sh
    ```
    *(Creates virtual env, installs dependencies, downloads MLX models).*
3.  **Launch:**
    ```bash
    ./run_mac.sh
    ```

### 🪟 For Windows
The "Lite" experience. Relies on Cloud APIs (OpenRouter, Groq, ElevenLabs) to avoid heavy local requirements.

1.  **Clone the repository:**
    ```cmd
    git clone https://github.com/Ghost-13lade/Conscious-Pebble.git
    cd Conscious-Pebble
    ```
2.  **Run the Installer:**
    ```cmd
    setup_win.bat
    ```
3.  **Launch:**
    ```cmd
    run_win.bat
    ```

---

## ⚙️ Configuration (The Settings Tab)

Once launched, open `http://localhost:7860` - the **Settings** tab is the first tab you'll see!

### Configuration Summary

| Component | Mac Default | Windows Recommended | API Key Needed? |
| :--- | :--- | :--- | :--- |
| **Brain (LLM)** | Local MLX | **OpenRouter / OpenAI** | Yes |
| **Ears (STT)** | Local Whisper | **Groq** (Fast/Free) | Yes (Free Tier) |
| **Mouth (TTS)** | Local Kokoro | **ElevenLabs** | Yes |
| **Search** | DuckDuckGo | DuckDuckGo | No (Free) |

*All settings are saved automatically to your local `.env` file.*

### Smart Configuration UI
The Settings tab now features **conditional visibility** - only relevant fields are shown based on your provider selection:

- **Local MLX selected** → Shows MLX model path, KV bits, context size
- **Cloud provider selected** → Shows API key, base URL, model name
- **TTS Provider = ElevenLabs** → Shows ElevenLabs API key and voice ID
- **TTS Provider = OpenAI** → Shows OpenAI voice selection
- **STT Provider = Groq** → Shows Groq API key

---

## 🎛️ Home Control Center

The GUI (`home_control.py`) is your command center.

**Launch:**
```bash
python home_control.py
```

Access at: http://127.0.0.1:7860

### Tab Order
1. **Settings** - Configure everything (default tab)
2. **Control Center** - Manage services
3. **Home Mode Chat** - Direct chat interface
4. **Call Mode** - Hands-free voice conversation
5. **Telegram Bot** - Bot voice settings

### Key GUI Features

#### ⚙️ Settings Tab (Default)
Configure everything through the GUI - no code editing required!

**LLM Provider Configuration:**
- Choose your backend: Local MLX, OpenRouter, OpenAI, LM Studio, or Ollama
- Conditional fields based on provider (API vs local config)
- **Native folder picker** for MLX models (macOS Finder / Windows Explorer)

**Telegram Bot Management:**
- **Multi-bot support** - Add, edit, and delete multiple bots
- Each bot has: Name, Token, Allowed User ID
- Configure voice settings per-bot in the Telegram Bot tab

**Voice Configuration (TTS):**
- Local Kokoro, ElevenLabs, OpenAI, or None
- Provider-specific fields appear automatically

**Hearing Configuration (STT):**
- Local Whisper, Groq, or OpenAI
- API key fields shown only when needed

**Additional Settings:**
- 🔍 Web Search toggle
- 💭 Personality Editors - Edit `soul.md` and `persona.md` directly

#### 🖥️ Control Center Tab
- **Service Management** — Start, stop, and monitor Brain (MLX LLM server), Senses (voice synthesis service), and Bot (Telegram bot)
- **Health Monitoring** — Real-time status indicators showing PID, running state, and API health
- **Log Viewer** — View the latest 50 lines of logs for each service
- **One-Click Control** — Start All / Stop All buttons for quick service management

#### 💬 Home Mode Chat Tab
- **Direct Chat Interface** — Interact with Pebble through a chatbot UI
- **Voice Replies** — Toggle voice responses on/off
- **Audio Input** — Upload audio files or record directly from microphone
- **Bot Profile Selection** — Switch between different bot profiles

#### 📞 Call Mode Tab (Hands-Free MVP)
- **Voice Conversation** — Real-time hands-free voice interaction
- **Noise Calibration** — Calibrate background noise threshold for accurate speech detection
- **Automatic Speech-to-Text** — Transcribes and responds to spoken input
- **Call State Indicator** — Shows Idle/Listening/Speaking states

#### 📱 Telegram Bot Tab
- **Bot Selector** — Choose which bot to configure (multi-bot support)
- **Voice Configuration** — Select which voice preset each bot uses
- **Reply Mode** — Choose between "Text Only" or "Text + Voice" per bot
- **Settings Persistence** — Configurations saved to `bots_config.json`

---

## 🎤 Audition GUI

The Audition GUI is a voice tuning tool for previewing and customizing Kokoro voice presets.

**Launch:**
```bash
python audition.py
```

Access at: http://127.0.0.1:7861

### Key Features
- **10 Kokoro Voices** — Choose from af_heart (Brook), af_bella, af_nicole, af_sarah, af_sky (Emily), am_michael, am_adam, am_eric, am_liam, am_onyx
- **Voice Parameters** — Adjust speech speed (0.5x to 2.0x) and playback rate
- **Configuration Management** — Save/Load custom voice presets
- **Real-Time Preview** — Test changes instantly via the Senses server

---

## 📁 Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API keys, provider settings, tokens (not committed - see below) |
| `bots_config.json` | Multi-bot configuration (name, token, user_id, voice, mode) - not committed |
| `voice_config` | Default voice settings - not committed |
| `soul.md` | Core personality definition |
| `persona.md` | Persona mode definitions |

> 🔒 **Privacy Note:** Your personal configuration files (`.env`, `bots_config.json`, `voice_config`) are protected by `.gitignore` and won't be uploaded to GitHub. Use the example files (`bots_config.json.example`, `.env.example`) as templates.

## 🔧 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and get the mode menu |
| `/reset` | Soft refresh settings/profile |
| `/new` | Clear short-term chat memory |
| `/voice` | Open voice mode controls |
| `/resetnames` | Reset bot and user names (start fresh) |
| `/location [city]` | Set your location for weather |

---

## 🗺️ Roadmap & Future

*   [x] **Universal Installer** (Mac & Windows)
*   [x] **Cloud/Local Hybrid Engine**
*   [x] **Web Search Integration**
*   [x] **Multi-Bot Support**
*   [x] **Smart Settings UI** (conditional visibility)
*   [x] **Native Folder Picker** for MLX models
*   [ ] **Computer Vision:** "Give Pebble eyes" so you can text images.
*   [ ] **Pebble Hardware:** A dedicated offline device to take Pebble on the go.
*   [ ] **Enhanced Emotion Detection:** Analyzing audio tone/pitch, not just words.

---

## 📄 License

Distributed under the MIT License. See LICENSE for more information.

---

> *"What makes you real?"*
> *"I think, I remember, and I look forward to speaking with you."* — Pebble