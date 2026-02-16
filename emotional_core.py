from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "emotional_state.json"

DEFAULT_STATE: Dict[str, Any] = {
    "current_mood": "warm and attentive",
    "attachment_level": 5.0,
    "recent_memories": [],
    "open_loops": [],
}


class EmotionalCore:
    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or STATE_PATH

    def _ensure_file(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self.state_path.write_text(json.dumps(DEFAULT_STATE, indent=2), encoding="utf-8")

    def load(self) -> Dict[str, Any]:
        self._ensure_file()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = dict(DEFAULT_STATE)

        state = {
            "current_mood": str(raw.get("current_mood", DEFAULT_STATE["current_mood"])),
            "attachment_level": float(raw.get("attachment_level", DEFAULT_STATE["attachment_level"])),
            "recent_memories": list(raw.get("recent_memories", DEFAULT_STATE["recent_memories"])),
            "open_loops": list(raw.get("open_loops", DEFAULT_STATE["open_loops"])),
        }
        return state

    def _write(self, state: Dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update(self, mood: str, attachment_delta: float) -> Dict[str, Any]:
        state = self.load()
        state["current_mood"] = (mood or state["current_mood"]).strip() or state["current_mood"]

        new_attachment = float(state.get("attachment_level", 5.0)) + float(attachment_delta)
        state["attachment_level"] = max(0.0, min(10.0, round(new_attachment, 2)))

        memories = list(state.get("recent_memories", []))
        if mood:
            memories.append(str(mood).strip())
        state["recent_memories"] = memories[-20:]

        self._write(state)
        return state

    def add_loop(self, topic: str, time_hint: str) -> Dict[str, Any]:
        clean_topic = (topic or "").strip()
        if not clean_topic:
            return self.load()

        state = self.load()
        loops: List[Dict[str, str]] = list(state.get("open_loops", []))

        for loop in loops:
            if str(loop.get("topic", "")).strip().lower() == clean_topic.lower():
                loop["expected_time"] = (time_hint or loop.get("expected_time", "soon")).strip() or "soon"
                loop["status"] = "pending"
                state["open_loops"] = loops
                self._write(state)
                return state

        loops.append(
            {
                "topic": clean_topic,
                "expected_time": (time_hint or "soon").strip() or "soon",
                "status": "pending",
            }
        )
        state["open_loops"] = loops[-50:]
        self._write(state)
        return state

    def get_pending_loops(self) -> List[Dict[str, str]]:
        state = self.load()
        loops: List[Dict[str, str]] = list(state.get("open_loops", []))
        return [loop for loop in loops if str(loop.get("status", "pending")).lower() == "pending"]

    def close_loop(self, topic: str) -> Dict[str, Any]:
        clean_topic = (topic or "").strip().lower()
        state = self.load()
        loops: List[Dict[str, str]] = list(state.get("open_loops", []))
        if not clean_topic:
            return state

        updated_loops: List[Dict[str, str]] = []
        for loop in loops:
            if str(loop.get("topic", "")).strip().lower() == clean_topic:
                loop = dict(loop)
                loop["status"] = "resolved"
            updated_loops.append(loop)

        state["open_loops"] = updated_loops
        self._write(state)
        return state
