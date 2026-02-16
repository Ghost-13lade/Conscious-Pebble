from __future__ import annotations

import os
import random
from datetime import date as date_type
from pathlib import Path
from typing import List
from uuid import uuid4

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"


class MemoryEngine:
    def __init__(self, chroma_path: Path | None = None) -> None:
        self.chroma_path = chroma_path or CHROMA_DIR
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.chroma_path))
        self.embedder = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True
        )

        self.daily_journals = self.client.get_or_create_collection("daily_journals")
        self.facts_and_goals = self.client.get_or_create_collection("facts_and_goals")

    def _embed(self, text: str) -> List[float]:
        vector = self.embedder.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vector.tolist()

    def retrieve_relevant_context(self, query: str, user_id: str, k: int = 3) -> str:
        if not query.strip():
            return "[Past Related Events]: None\n[Relevant Facts]: None"

        query_embedding = [self._embed(query)]

        event_results = self.daily_journals.query(
            query_embeddings=query_embedding,
            n_results=k,
            where={"user_id": user_id},
        )
        fact_results = self.facts_and_goals.query(
            query_embeddings=query_embedding,
            n_results=k,
            where={"user_id": user_id},
        )

        events = (event_results.get("documents") or [[]])[0]
        facts = (fact_results.get("documents") or [[]])[0]

        events_block = "\n- " + "\n- ".join(events) if events else " None"
        facts_block = "\n- " + "\n- ".join(facts) if facts else " None"

        return f"[Past Related Events]:{events_block}\n[Relevant Facts]:{facts_block}"

    def archive_day(self, summary_text: str, date: str | date_type, user_id: str) -> None:
        if not summary_text.strip():
            return

        date_str = date.isoformat() if isinstance(date, date_type) else str(date)
        self.daily_journals.add(
            ids=[f"journal-{user_id}-{date_str}-{uuid4().hex[:8]}"],
            documents=[summary_text],
            embeddings=[self._embed(summary_text)],
            metadatas=[{"user_id": user_id, "date": date_str, "kind": "daily_summary"}],
        )

    def archive_facts(self, facts: List[str], date: str | date_type, user_id: str) -> None:
        clean_facts = [fact.strip() for fact in facts if fact and fact.strip()]
        if not clean_facts:
            return

        date_str = date.isoformat() if isinstance(date, date_type) else str(date)
        ids = [f"fact-{user_id}-{date_str}-{uuid4().hex[:8]}-{idx}" for idx, _ in enumerate(clean_facts)]
        embeddings = [self._embed(item) for item in clean_facts]
        metadatas = [{"user_id": user_id, "date": date_str, "kind": "fact"} for _ in clean_facts]

        self.facts_and_goals.add(
            ids=ids,
            documents=clean_facts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def get_random_memory_summary(self, user_id: str) -> str:
        snippets: List[str] = []

        for collection in (self.daily_journals, self.facts_and_goals):
            try:
                result = collection.get(where={"user_id": user_id}, limit=25)
                docs = result.get("documents", []) if isinstance(result, dict) else []
                snippets.extend([str(doc).strip() for doc in docs if str(doc).strip()])
            except Exception:
                continue

        if not snippets:
            return ""

        picked = random.choice(snippets)
        return picked[:240].strip()
