import os
import random
import tempfile
import signal
import sys

os.environ["TOKENIZERS_PARALLELISM"] = "false"

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Tuple

import dateparser
import httpx
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from brain import Brain
from config import (
    ALLOWED_USER_ID,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    TELEGRAM_BOT_TOKEN,
)
from db import (
    get_active_mode,
    get_chat_logs_for_day,
    get_persona_by_mode,
    get_personas,
    get_recent_chat_logs,
    get_user_profile,
    get_voice_settings,
    init_db,
    list_users_with_logs,
    log_chat,
    set_active_mode,
    update_voice_setting,
    upsert_voice_settings,
    update_persona_prompt,
    upsert_user_profile,
    update_user_location,
)
from memory_engine import MemoryEngine
from emotional_core import EmotionalCore
from tools import get_weather, get_voice_config
from voice_engine import (
    extract_emotion_tag,
    load_voice_configs,
    synthesize_voice_bytes,
    transcribe_audio_file,
)


PERSONA_PREFIX = "Mode: "
LEGACY_MODE_ALIASES = {
    "Girlfriend (Nani)": "Fun Pebble",
    "Executive": "Executive Pebble",
    "Health Coach": "Fitness Pebble",
}
SHORT_TERM_TURNS = 10
OVERFLOW_TRIGGER = 40
OVERFLOW_DREAM_CHUNK = 30
GOODNIGHT_TRIGGERS = {"goodnight", "gn", "going to sleep"}
VOICE_SETTINGS_BUTTON = "Voice Settings"
pending_custom_persona_users: set[str] = set()
short_term_memory: Dict[str, Deque[Dict[str, str]]] = defaultdict(
    lambda: deque(maxlen=120)
)
# Voice settings: mode = "off" or "on", voice = name from true_voices.json
VOICE_MODES = {"off", "on"}


def build_voice_menu() -> InlineKeyboardMarkup:
    """Build simple voice menu:
    - Mode: Voice Off / Voice On
    - Voice: Pebble (default), Nicole, Sarah, Emily, Bella
    """
    configs = load_voice_configs()
    
    # Section 1: Mode toggle
    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("🔇 Voice Off", callback_data="voice_mode:off"),
            InlineKeyboardButton("🔊 Voice On", callback_data="voice_mode:on"),
        ]
    ]
    
    # Section 2: Voice selection (only shown when voice mode is being selected)
    voice_buttons = [
        InlineKeyboardButton(str(cfg.get("name", "Unnamed")), callback_data=f"voice_sel:{idx}")
        for idx, cfg in enumerate(configs)
        if cfg.get("name") and cfg.get("name") in ["Pebble", "Nicole", "Sarah", "Emily", "Bella"]
    ]
    # Add voice buttons in a single row
    if voice_buttons:
        rows.append(voice_buttons)

    return InlineKeyboardMarkup(rows)


async def transcribe_telegram_audio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> Tuple[Optional[str], str]:
    if not update.message:
        return None, "neutral"

    tg_file = None
    filename = "audio_input.ogg"

    if update.message.voice:
        filename = "voice_note.ogg"
        tg_file = await context.bot.get_file(update.message.voice.file_id)
    elif update.message.audio:
        filename = update.message.audio.file_name or "audio_file.mp3"
        tg_file = await context.bot.get_file(update.message.audio.file_id)
    elif update.message.document and (update.message.document.mime_type or "").startswith("audio/"):
        filename = update.message.document.file_name or "audio_document"
        tg_file = await context.bot.get_file(update.message.document.file_id)

    if not tg_file:
        return None, "neutral"

    audio_bytes = bytes(await tg_file.download_as_bytearray())
    suffix = os.path.splitext(filename)[1] or ".ogg"
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        transcript = transcribe_audio_file(temp_path)
        emotion_tag = extract_emotion_tag(temp_path)
        return transcript, emotion_tag
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


async def deliver_reply(
    update: Update,
    user_id: str,
    reply: str,
    detected_emotion: str = "neutral",
    send_text: Optional[bool] = None,
    send_audio: Optional[bool] = None,
) -> None:
    if not update.message:
        return

    # Read voice settings from voice_config.json (controlled by GUI)
    voice_config = get_voice_config()
    voice_enabled = voice_config.get("voice_enabled", False)
    active_voice_name = voice_config.get("voice_name", "Pebble")
    print(f"[DEBUG] deliver_reply: voice_enabled={voice_enabled}, active_voice={active_voice_name}")

    if send_text is None or send_audio is None:
        if voice_enabled:
            send_text = True
            send_audio = True
        else:
            # Default to text only
            send_text = True
            send_audio = False

    if send_text and not send_audio:
        print("[DEBUG] send_audio=False. Skipping audio.")
        await update.message.reply_text(reply)
        return

    audio_buf = None
    if send_audio:
        audio_buf = synthesize_voice_bytes(reply, active_voice_name, detected_emotion=detected_emotion)

    if not send_text and send_audio:
        if audio_buf is None:
            print("[WARN] Voice synthesis failed. Falling back to text.")
            await update.message.reply_text(reply)
        elif audio_buf:
            await update.message.reply_audio(
                audio=audio_buf,
                filename="brook_reply.wav",
                title=f"Pebble — {active_voice_name}",
            )
        else:
            await update.message.reply_text(reply)
        return

    if audio_buf:
        await update.message.reply_audio(
            audio=audio_buf,
            filename="brook_reply.wav",
            title=f"Pebble — {active_voice_name}",
        )
    if send_text:
        await update.message.reply_text(reply)


def resolve_delivery_preferences(user_id: str) -> Tuple[str, bool, bool]:
    # Read voice settings from voice_config.json (controlled by GUI)
    voice_config = get_voice_config()
    voice_enabled = voice_config.get("voice_enabled", False)
    active_voice = voice_config.get("voice_name", "Pebble")
    
    print(f"[Voice Config] voice_enabled={voice_enabled}, voice={active_voice}")

    if voice_enabled:
        return "voice", True, True
    # Default to text only
    return "text", True, False


def now_iso() -> str:
    return datetime.now().isoformat()


def format_gap_since(last_time: datetime | None) -> str:
    if not last_time:
        return "a while"
    seconds = max(int((datetime.now() - last_time).total_seconds()), 0)
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days} day" + ("s" if days != 1 else "")
    if seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour" + ("s" if hours != 1 else "")
    minutes = seconds // 60
    return f"{minutes} minute" + ("s" if minutes != 1 else "")


def get_last_interaction_time(user_id: str) -> datetime | None:
    recent = get_recent_chat_logs(user_id, limit=1)
    if not recent:
        return None
    latest = recent[0].get("created_at")
    if not latest:
        return None
    return brain._parse_timestamp(str(latest))


memory_engine = MemoryEngine()
emotional_core = EmotionalCore()
brain = Brain(
    model=OPENAI_MODEL,
    base_url=OPENAI_BASE_URL,
    api_key=OPENAI_API_KEY,
    memory_engine=memory_engine,
    emotional_core=emotional_core,
)
telegram_app: Application | None = None


def is_allowed_user(user_id: str) -> bool:
    if not ALLOWED_USER_ID:
        return True
    return user_id == str(ALLOWED_USER_ID)


def is_goodnight_message(text: str) -> bool:
    lowered = text.lower().strip()
    return any(trigger in lowered for trigger in GOODNIGHT_TRIGGERS)


def build_persona_menu() -> ReplyKeyboardMarkup:
    ordered_modes = ["Fun Pebble", "Executive Pebble", "Fitness Pebble", "Custom"]
    persona_map = {p["mode"]: p for p in get_personas()}
    persona_rows = [
        [KeyboardButton(f"{PERSONA_PREFIX}{mode}")]
        for mode in ordered_modes
        if mode in persona_map
    ]
    return ReplyKeyboardMarkup(persona_rows, resize_keyboard=True, is_persistent=True)


async def reminder_callback(
    context: ContextTypes.DEFAULT_TYPE | None = None,
    chat_id: int | None = None,
    task: str = "your reminder",
) -> None:
    resolved_chat_id: int | None = chat_id
    resolved_task = task

    if context and context.job:
        job_data = context.job.data if context.job else None
        if job_data:
            resolved_chat_id = job_data.get("chat_id", resolved_chat_id)
            resolved_task = job_data.get("task", resolved_task)

    if not resolved_chat_id:
        return

    if context:
        await context.bot.send_message(chat_id=resolved_chat_id, text=f"⏰ Reminder: {resolved_task}")
        return

    if telegram_app:
        await telegram_app.bot.send_message(chat_id=resolved_chat_id, text=f"⏰ Reminder: {resolved_task}")


# Track users who need to provide their name
pending_name_users: set[str] = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        await update.message.reply_text("Unauthorized user.")
        print(f"[Auth] Unauthorized user attempted /start: {user_id}")
        return

    print(f"[Auth] User {user_id} authorized.")

    if not get_active_mode(user_id):
        set_active_mode(user_id, "Fun Pebble")
    upsert_voice_settings(user_id=user_id)

    # Check if this is a new user (no bot_name or user_name set)
    profile = get_user_profile(user_id)
    bot_name = profile.get("bot_name", "").strip()
    user_name = profile.get("user_name", "").strip()

    if not bot_name or not user_name:
        # New user - ask for names
        pending_name_users.add(user_id)
        await update.message.reply_text(
            "Hey! I'm Pebble 💕\n\n"
            "I'm brand new here and want to know what to call you!\n\n"
            "What should I call you? And what do you want to call me?"
        )
        return

    await update.message.reply_text(
        f"{bot_name} is online! Choose a mode from the menu.",
        reply_markup=build_persona_menu(),
    )


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        await update.message.reply_text("Unauthorized user.")
        return

    # Read from voice_config.json
    voice_config = get_voice_config()
    voice_enabled = voice_config.get("voice_enabled", False)
    voice = voice_config.get("voice_name", "Pebble")
    mode_display = "Voice Off (🔇)" if not voice_enabled else "Voice On (🔊)"
    
    await update.message.reply_text(
        (
            "🎙️ Voice settings (controlled by GUI):\n"
            f"- Mode: {mode_display}\n"
            f"- Voice: {voice}\n\n"
            "Edit voice settings in the GUI at http://localhost:7860"
        )
    )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Debug command to test callback functionality"""
    if not update.effective_user or not update.message:
        return
    
    print("[TEST COMMAND] Received /test command")
    keyboard = [
        [InlineKeyboardButton("Test Button 1", callback_data="test:1")],
        [InlineKeyboardButton("Test Button 2", callback_data="test:2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tap a button to test callbacks:", reply_markup=reply_markup)


async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user location for weather tracking"""
    if not update.effective_user or not update.message:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        await update.message.reply_text("Unauthorized user.")
        return

    # Get city from command args
    args = context.args
    if not args:
        current_profile = get_user_profile(user_id)
        current_location = current_profile.get("location", "").strip()
        if current_location:
            await update.message.reply_text(f"Your current location is: {current_location}\nTo change, use: /location [city]")
        else:
            await update.message.reply_text("Usage: /location [city]\nExample: /location London")
        return

    city = " ".join(args).strip()
    if not city:
        await update.message.reply_text("Please provide a city name. Usage: /location [city]")
        return

    update_user_location(user_id, city)
    await update.message.reply_text(f"Got it. I'll keep track of the weather in {city} now. 🌤️")


async def handle_voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    print(f"[Voice Callback] Received: query={query}, data={query.data if query else 'None'}")
    if not query or not update.effective_user:
        print("[Voice Callback] No query or no effective user")
        return

    user_id = str(update.effective_user.id)
    print(f"[Voice Callback] user_id={user_id}, data={query.data}")
    ack_text = "Saved"
    answered = False

    try:
        if not is_allowed_user(user_id):
            ack_text = "Unauthorized"
            await query.answer(ack_text, show_alert=True)
            answered = True
            return

        data = query.data or ""

        if data.startswith("voice_mode:"):
            mode = data.split(":", 1)[1].strip().lower()
            if mode not in VOICE_MODES:
                ack_text = "Invalid mode"
                await query.answer(ack_text, show_alert=True)
                answered = True
                return

            update_voice_setting(user_id=user_id, key="voice_mode", value=mode)
            persisted = get_voice_settings(user_id)
            mode_now = str(persisted.get("voice_mode", "text_and_voice")).strip().lower()
            active_voice_name = str(persisted.get("active_voice_name", "Pebble"))
            mode_label = {
                "off": "Voice Off",
                "text_only": "Text Only",
                "text_and_voice": "Text + Voice",
            }.get(mode_now, mode_now)

            ack_text = f"Settings updated to: {mode_label}"
            if query.message:
                await query.edit_message_text(
                    (
                        "🎙️ Voice settings\n"
                        f"✅ Current Mode: {mode_label}\n"
                        f"🎧 Active Voice: {active_voice_name}"
                    ),
                    reply_markup=build_voice_menu(),
                )
            return

        if data.startswith("voice_sel:"):
            try:
                idx = int(data.split(":", 1)[1])
            except ValueError:
                ack_text = "Invalid selection"
                await query.answer(ack_text, show_alert=True)
                answered = True
                return

            configs = load_voice_configs()
            if idx < 0 or idx >= len(configs):
                ack_text = "Voice config not found"
                await query.answer(ack_text, show_alert=True)
                answered = True
                return

            selected_name = str(configs[idx].get("name", "Pebble"))
            update_voice_setting(user_id=user_id, key="active_voice_name", value=selected_name)
            persisted = get_voice_settings(user_id)
            mode_now = str(persisted.get("voice_mode", "text_and_voice")).strip().lower()
            mode_label = {
                "off": "Voice Off",
                "text_only": "Text Only",
                "text_and_voice": "Text + Voice",
            }.get(mode_now, mode_now)

            # Force fresh query to confirm
            fresh = get_voice_settings(user_id)
            print(f"[Voice Updated & Verified] User {user_id}: mode={fresh.get('voice_mode')}, voice={fresh.get('active_voice_name')}")
            
            ack_text = f"Voice set to: {selected_name} ({mode_label})"
            if query.message:
                await query.edit_message_text(
                    (
                        "🎙️ Voice settings\n"
                        f"✅ Current Mode: {mode_label}\n"
                        f"🎧 Active Voice: {selected_name}"
                    ),
                    reply_markup=build_voice_menu(),
                )
            return

        ack_text = "Unknown action"
    except Exception as e:
        print(f"[Voice Callback Error] user={user_id} data={query.data if query else ''} error={e}")
        ack_text = "Error saving setting"
    finally:
        try:
            if not answered:
                await query.answer(ack_text)
        except Exception as answer_error:
            print(f"[Voice Callback Answer Error] user={user_id} error={answer_error}")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        await update.message.reply_text("Unauthorized user.")
        return

    # Soft refresh: force re-read of profile and active persona without wiping RAM history.
    _ = get_user_profile(user_id)
    current_mode = get_active_mode(user_id)
    _ = get_persona_by_mode(current_mode) or get_persona_by_mode("Fun Pebble")

    await update.message.reply_text(
        "I've refreshed my settings and memory, but I'm still here with you. What were we saying?",
        reply_markup=build_persona_menu(),
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        await update.message.reply_text("Unauthorized user.")
        return

    # Hard wipe: clear in-memory short-term conversation state.
    short_term_memory[user_id].clear()
    await update.message.reply_text("Memory wiped. Starting a fresh conversation. Hi!")


async def process_user_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_text: str,
    delivery_mode: str = "text",
    send_text: bool = True,
    send_audio: bool = False,
    emotion_tag: str = "neutral",
) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        print(f"[Auth] Unauthorized message blocked from user: {user_id}")
        return

    user_text = user_text.strip()
    if not user_text:
        await update.message.reply_text("I didn't catch that — can you try again?")
        return

    # Handle new user name collection
    if user_id in pending_name_users:
        # Use LLM to extract names from their response
        extracted_names = brain.extract_names_from_text(user_text)
        if extracted_names:
            user_name = extracted_names.get("user_name", "").strip()
            bot_name = extracted_names.get("bot_name", "").strip()
            
            if user_name and bot_name:
                upsert_user_profile(
                    user_id=user_id,
                    bot_name=bot_name,
                    user_name=user_name,
                )
                pending_name_users.discard(user_id)
                await update.message.reply_text(
                    f"Perfect! 💕\n\n"
                    f"I'll call you {user_name}, and you can call me {bot_name}!\n\n"
                    f"Now {user_name}, choose a mode from the menu to get started:",
                    reply_markup=build_persona_menu(),
                )
                return
            elif user_name:
                # Got user name, still need bot name
                await update.message.reply_text(
                    f"Got it, {user_name}! 💕\n\n"
                    "Now what do you want to call me?"
                )
                # Store user name temporarily and ask for bot name
                # For simplicity, just ask again - the next response should have both
                return
            else:
                # Couldn't extract names, ask again
                await update.message.reply_text(
                    "I didn't catch that! 😄\n\n"
                    "Please tell me:\n"
                    "1. What should I call you?\n"
                    "2. What do you want to call me?"
                )
                return
        else:
            # LLM couldn't extract, try to parse simply
            await update.message.reply_text(
                "I didn't quite get that! 😅\n\n"
                "Just tell me:\n"
                "- What should I call you?\n"
                "- What do you want to call me?"
            )
            return

    if user_text == VOICE_SETTINGS_BUTTON:
        await voice_command(update, context)
        return

    if is_goodnight_message(user_text):
        await update.message.reply_text("Goodnight! 🌙 I'm going to reflect on our day. Sleep well.")
        logs_for_reflection = list(short_term_memory[user_id])
        if not logs_for_reflection:
            logs_for_reflection = get_chat_logs_for_day(
                user_id=user_id,
                day_iso=datetime.now().date().isoformat(),
            )
        if logs_for_reflection:
            brain.run_dream_cycle(chat_logs=logs_for_reflection, user_id=user_id)
        short_term_memory[user_id].clear()
        return

    if user_text.startswith(PERSONA_PREFIX):
        selected_mode_raw = user_text.replace(PERSONA_PREFIX, "", 1).strip()
        selected_mode = LEGACY_MODE_ALIASES.get(selected_mode_raw, selected_mode_raw)
        available_modes = {p["mode"] for p in get_personas()}

        if selected_mode == "Custom":
            pending_custom_persona_users.add(user_id)
            set_active_mode(user_id, "Custom")
            await update.message.reply_text(
                "Describe your custom mode in one message, and I’ll generate it.",
                reply_markup=build_persona_menu(),
            )
            return

        if selected_mode not in available_modes:
            await update.message.reply_text(
                "That mode isn't available right now. Choose one from the menu.",
                reply_markup=build_persona_menu(),
            )
            return

        set_active_mode(user_id, selected_mode)
        await update.message.reply_text(
            f"Switched to: {selected_mode}",
            reply_markup=build_persona_menu(),
        )
        return

    if user_id in pending_custom_persona_users:
        custom_prompt = brain.generate_custom_persona_prompt(user_text)
        update_persona_prompt("Custom", custom_prompt)
        set_active_mode(user_id, "Custom", custom_description=user_text)
        pending_custom_persona_users.discard(user_id)
        await update.message.reply_text("Custom persona generated and activated.")
        return

    profile = get_user_profile(user_id)
    location = profile.get("location", "").strip()
    relationship_status = profile.get(
        "relationship_status", "We are getting to know each other."
    )

    extracted_location = brain.extract_location(user_text)
    if extracted_location:
        upsert_user_profile(
            user_id=user_id,
            summary=profile.get("summary", ""),
            emotional_notes=profile.get("emotional_notes", ""),
            day_summary=profile.get("day_summary", ""),
            location=extracted_location,
        )
        await update.message.reply_text(f"Got it — I’ll remember your location as {extracted_location}. 📍")
        profile = get_user_profile(user_id)
        location = profile.get("location", "").strip()
        relationship_status = profile.get(
            "relationship_status", "We are getting to know each other."
        )

    reminder = brain.detect_reminder(user_text)
    if reminder:
        parsed_time = dateparser.parse(
            reminder["time"],
            settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()},
        )
        if parsed_time:
            now = datetime.now()
            if parsed_time <= now:
                parsed_time = parsed_time + timedelta(days=1)

            if reminder.get("type") == "recurring" and reminder.get("interval") == "daily":
                task_id = f"reminder:daily:{user_id}:{reminder['task'].strip().lower().replace(' ', '_')}:{parsed_time.hour}:{parsed_time.minute}"
                context.job_queue.scheduler.add_job(
                    reminder_callback,
                    trigger="cron",
                    hour=parsed_time.hour,
                    minute=parsed_time.minute,
                    id=task_id,
                    replace_existing=True,
                    kwargs={"chat_id": update.effective_chat.id, "task": reminder["task"]},
                )
                await update.message.reply_text(
                    f"Bet. I'll text you every day at {reminder['time']} to {reminder['task']}. 🔄"
                )
            else:
                task_id = f"reminder:one_off:{user_id}:{int(parsed_time.timestamp())}"
                context.job_queue.scheduler.add_job(
                    reminder_callback,
                    trigger="date",
                    run_date=parsed_time,
                    id=task_id,
                    replace_existing=True,
                    kwargs={"chat_id": update.effective_chat.id, "task": reminder["task"]},
                )
                await update.message.reply_text(f"Got it. Set an alarm for {reminder['time']}. ⏰")
            return

    current_mode = get_active_mode(user_id)
    persona = get_persona_by_mode(current_mode) or get_persona_by_mode("Fun Pebble")
    persona_text = persona["system_prompt"] if persona else "You are a helpful companion AI."

    # === DEBUG LOGGING: PERSONA CHECK ===
    print(f"\n[BROOK DEBUG] Message received from {user_id}")
    print(f"[BROOK DEBUG] Active Mode from DB: '{current_mode}'")
    if persona:
        print(f"[BROOK DEBUG] Persona Loaded: YES (Length: {len(persona.get('system_prompt', ''))} chars)")
        # Show the first line of the persona to prove it switched
        first_line = persona.get('system_prompt', '').split('\n')[0]
        print(f"[BROOK DEBUG] Persona Snippet: {first_line}")
    else:
        print(f"[BROOK DEBUG] Persona Loaded: NO (Using Default)")
    print("-" * 50)
    # ====================================

    profile_summary = "\n".join(
        [
            profile.get("summary", ""),
            profile.get("emotional_notes", ""),
            profile.get("day_summary", ""),
        ]
    ).strip()

    lowered = user_text.lower()
    weather_or_outfit_query = any(
        token in lowered for token in ("weather", "what should i wear", "outfit", "what do i wear")
    )
    weather_system_data = ""
    current_weather = "Unknown"
    if weather_or_outfit_query:
        if not location:
            await update.message.reply_text("I don't know where we are yet! 🌍 Tell me your city so I can check.")
            return
        weather_data = get_weather(location)
        current_weather = weather_data
        weather_system_data = (
            f"[SYSTEM DATA: Current Weather in {location} is {weather_data}. Advice the user accordingly.]"
        )
    elif location:
        current_weather = get_weather(location)

    short_term_memory[user_id].append(
        {"role": "user", "content": user_text, "created_at": now_iso()}
    )

    history = list(short_term_memory[user_id])
    if not history:
        recent_logs = get_recent_chat_logs(user_id, limit=SHORT_TERM_TURNS * 2)
        history = [
            {
                "role": row["role"],
                "content": row["content"],
                "created_at": row.get("created_at", ""),
            }
            for row in recent_logs
        ]

    retrieved_context = memory_engine.retrieve_relevant_context(query=user_text, user_id=user_id)
    if weather_system_data:
        retrieved_context = f"{retrieved_context}\n\n{weather_system_data}".strip()

    try:
        text_len = len(user_text.strip())
        user_length_hint = "short" if text_len < 80 else ("medium" if text_len < 260 else "long")

        enriched_context = retrieved_context
        if emotion_tag and emotion_tag != "neutral":
            enriched_context = (
                f"{retrieved_context}\n\n"
                f"[VOICE EMOTION SIGNAL]: User sounded {emotion_tag}. "
                "Use this softly as emotional context."
            ).strip()

        reply, detected_emotion = await asyncio.to_thread(
            brain.generate_response,
            history=history,
            persona=persona_text,
            user_profile=profile_summary,
            retrieved_context=enriched_context,
            current_weather=current_weather,
            user_id=user_id,
            relationship_status=relationship_status,
            delivery_mode=delivery_mode,
            user_length_hint=user_length_hint,
        )
    except Exception as e:
        print(f"[Reply Error] generate_response failed for user={user_id}: {e}")
        reply = "Sorry love — I hit a glitch for a second. Can you try that again?"
        detected_emotion = "neutral"

    reply = (reply or "").strip()
    if not reply:
        print(f"[Reply Warning] Empty model output for user={user_id}; using fallback.")
        reply = "Sorry love — I blanked for a second. Say that one more time?"

    short_term_memory[user_id].append(
        {"role": "assistant", "content": reply, "created_at": now_iso()}
    )

    if len(short_term_memory[user_id]) > OVERFLOW_TRIGGER:
        overflow_logs = list(short_term_memory[user_id])[:OVERFLOW_DREAM_CHUNK]
        if overflow_logs:
            asyncio.create_task(
                run_dream_cycle_for_logs(
                    user_id=user_id,
                    logs=overflow_logs,
                    clear_short_term=False,
                )
            )
        short_term_memory[user_id] = deque(
            list(short_term_memory[user_id])[-SHORT_TERM_TURNS:],
            maxlen=120,
        )

    log_chat(user_id, "user", user_text)
    log_chat(user_id, "assistant", reply)

    await deliver_reply(
        update,
        user_id,
        reply,
        detected_emotion=detected_emotion,
        send_text=send_text,
        send_audio=send_audio,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = str(update.effective_user.id) if update.effective_user else ""
    delivery_mode, send_text, send_audio = resolve_delivery_preferences(user_id)

    await process_user_text(
        update,
        context,
        update.message.text,
        delivery_mode=delivery_mode,
        send_text=send_text,
        send_audio=send_audio,
    )


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = str(update.effective_user.id)
    if not is_allowed_user(user_id):
        print(f"[Auth] Unauthorized audio blocked from user: {user_id}")
        return

    await update.message.reply_text("🎧 Got it — transcribing your audio...")
    transcript, emotion_tag = await transcribe_telegram_audio(update, context)
    if not transcript:
        await update.message.reply_text("I couldn't hear that clearly. Can you retry with a clearer voice note? ❤️")
        return

    await update.message.reply_text(f"📝 You said: {transcript}")
    delivery_mode, send_text, send_audio = resolve_delivery_preferences(user_id)

    await process_user_text(
        update,
        context,
        transcript,
        delivery_mode=delivery_mode,
        send_text=send_text,
        send_audio=send_audio,
        emotion_tag=emotion_tag,
    )


async def heartbeat_job() -> None:
    healthy = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8080")
            healthy = response.status_code < 500
    except Exception:
        healthy = False

    if not healthy and telegram_app:
        for user_id in list_users_with_logs():
            try:
                await telegram_app.bot.send_message(
                    chat_id=int(user_id),
                    text="⚠️ Brain offline. Please check server.",
                )
            except Exception:
                continue


async def spontaneity_job() -> None:
    for user_id in list_users_with_logs():
        profile = get_user_profile(user_id)
        emotional_state = emotional_core.load()
        attachment_level = float(emotional_state.get("attachment_level", 5.0))
        mood = str(emotional_state.get("current_mood", "warm and attentive"))
        last_time = get_last_interaction_time(user_id)

        due_loop = brain.get_due_open_loop()
        if due_loop:
            topic = str(due_loop.get("topic", "")).strip()
            expected_time = str(due_loop.get("expected_time", "soon")).strip() or "soon"
            thought = brain.generate_loop_followup(topic=topic, expected_time=expected_time)
            if thought and telegram_app:
                try:
                    await telegram_app.bot.send_message(chat_id=int(user_id), text=thought)
                    log_chat(user_id, "assistant", thought)
                    emotional_core.close_loop(topic)
                except Exception:
                    pass
            continue

        if not brain.decide_to_message(last_time, attachment_level):
            continue

        location = profile.get("location", "").strip()
        weather = get_weather(location) if location else "Unknown"
        gap = format_gap_since(last_time)

        thought = ""
        if not emotional_core.get_pending_loops() and random.random() < 0.05:
            memory_summary = memory_engine.get_random_memory_summary(user_id=user_id)
            if memory_summary:
                thought = brain.generate_reminiscence_thought(memory_summary)

        if not thought:
            thought = brain.generate_spontaneous_thought(gap=gap, mood=mood, weather=weather)

        if not thought:
            continue

        if telegram_app:
            try:
                await telegram_app.bot.send_message(chat_id=int(user_id), text=thought)
                log_chat(user_id, "assistant", thought)
            except Exception:
                continue


async def consolidate_memory_job() -> None:
    await run_dream_cycle_for_all_users()


async def run_dream_cycle(user_id: str) -> None:
    day_iso = datetime.now().date().isoformat()
    print(f"[Dream Cycle] Starting for user={user_id} day={day_iso}...")

    day_logs = get_chat_logs_for_day(user_id=user_id, day_iso=day_iso)
    if not day_logs:
        print(f"[Dream Cycle] No logs found for user={user_id}. Skipping.")
        return

    dream_summary = brain.run_dream_cycle(chat_logs=day_logs, user_id=user_id, date=day_iso)
    print(f"[Dream Cycle] Summary generated for user={user_id}.")

    current_profile = get_user_profile(user_id)
    merged_summary = "\n".join(
        [
            current_profile.get("summary", "").strip(),
            f"[{day_iso}] {dream_summary}",
        ]
    ).strip()
    merged_notes = "\n".join(
        [
            current_profile.get("emotional_notes", "").strip(),
            dream_summary,
        ]
    ).strip()

    upsert_user_profile(
        user_id=user_id,
        summary=merged_summary,
        emotional_notes=merged_notes,
        day_summary=dream_summary,
    )
    print(f"[Dream Cycle] SQLite profile updated for user={user_id}.")

    short_term_memory[user_id].clear()
    print(f"[Dream Cycle] short_term_memory reset for user={user_id}.")


async def run_dream_cycle_for_all_users() -> None:
    for user_id in list_users_with_logs():
        await run_dream_cycle(user_id)


async def run_dream_cycle_for_logs(
    user_id: str,
    logs: List[Dict[str, str]],
    clear_short_term: bool = False,
) -> None:
    if not logs:
        return

    day_iso = datetime.now().date().isoformat()
    dream_summary = brain.run_dream_cycle(chat_logs=logs, user_id=user_id, date=day_iso)
    current_profile = get_user_profile(user_id)
    merged_summary = "\n".join(
        [
            current_profile.get("summary", "").strip(),
            f"[{day_iso}] {dream_summary}",
        ]
    ).strip()
    merged_notes = "\n".join(
        [
            current_profile.get("emotional_notes", "").strip(),
            dream_summary,
        ]
    ).strip()
    upsert_user_profile(
        user_id=user_id,
        summary=merged_summary,
        emotional_notes=merged_notes,
        day_summary=dream_summary,
    )

    if clear_short_term:
        short_term_memory[user_id].clear()


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    scheduler = app.job_queue.scheduler
    scheduler.configure(
        jobstores={
            "default": SQLAlchemyJobStore(url="sqlite:////Users/ys/Pebble/data/brook.db"),
            "memory": MemoryJobStore(),
        },
        timezone="America/Los_Angeles",
    )
    scheduler.add_job(
        heartbeat_job,
        "interval",
        minutes=5,
        id="heartbeat",
        replace_existing=True,
        jobstore="memory",
    )
    scheduler.add_job(
        consolidate_memory_job,
        "cron",
        hour=4,
        minute=0,
        id="dream_cycle",
        replace_existing=True,
        jobstore="memory",
    )
    scheduler.add_job(
        spontaneity_job,
        "interval",
        minutes=60,
        id="spontaneity",
        replace_existing=True,
        jobstore="memory",
    )
    scheduler.start()
    return scheduler


# Graceful shutdown handler
def graceful_shutdown(sig, frame):
    print("\n[Shutdown] Caught interrupt — cleaning up...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)


async def run() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Set it in your environment.")

    global telegram_app

    init_db()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app = app
    setup_scheduler(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("voice", voice_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("location", location_command))
    # Debug: catch ALL callbacks first
    app.add_handler(CallbackQueryHandler(handle_voice_callback))
    # app.add_handler(CallbackQueryHandler(handle_voice_callback, pattern=r"^voice_(mode|sel):"))
    app.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO | filters.Document.AUDIO,
            handle_audio_message,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Start Pebble and show mode menu"),
            BotCommand("reset", "Soft refresh settings/profile"),
            BotCommand("new", "Clear short-term chat memory"),
            BotCommand("voice", "Open voice mode and voice preset controls"),
        ]
    )
    await app.start()
    await app.updater.start_polling()

    print("[Bot Ready] Pebble online ❤️")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("[Shutdown] Keyboard interrupt — exiting cleanly")
        sys.exit(0)
