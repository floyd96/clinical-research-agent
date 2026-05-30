"""
Supabase persistence layer.

One connection per process via @lru_cache.
All functions are synchronous — the supabase-py SDK is sync by default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import os
from supabase import create_client, Client


@lru_cache(maxsize=1)
def _get_client() -> Client:
    url: str = os.environ["SUPABASE_URL"]
    key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── users ─────────────────────────────────────────────────────────────────────

def upsert_user(email: str, display_name: Optional[str] = None) -> str:
    """Insert or update user on login. Returns user UUID."""
    client = _get_client()
    result = (
        client.table("users")
        .upsert(
            {
                "email": email,
                "display_name": display_name or email.split("@")[0],
                "last_seen_at": _now(),
            },
            on_conflict="email",
        )
        .execute()
    )
    return result.data[0]["id"]


# ── chat_sessions ─────────────────────────────────────────────────────────────

def create_session(user_id: str) -> str:
    """Create a new chat session row. Returns session UUID."""
    client = _get_client()
    result = (
        client.table("chat_sessions")
        .insert({"user_id": user_id})
        .execute()
    )
    return result.data[0]["id"]


def create_session_with_id(session_id: str, user_id: str) -> str:
    """Create a chat session row with a specific ID (synced with Chainlit's thread_id)."""
    client = _get_client()
    client.table("chat_sessions").insert({"id": session_id, "user_id": user_id}).execute()
    return session_id


def close_session(session_id: str) -> None:
    """Stamp ended_at when the user starts a new session."""
    client = _get_client()
    client.table("chat_sessions").update({"ended_at": _now()}).eq("id", session_id).execute()


def set_session_title(session_id: str, first_user_message: str) -> None:
    """Set session title from the first user message (called once, on first turn)."""
    client = _get_client()
    client.table("chat_sessions").update({"title": first_user_message[:120]}).eq("id", session_id).execute()


def load_recent_sessions(user_id: str, limit: int = 20) -> list[dict]:
    """Return the user's most recent sessions, newest first. Each dict has id, title, started_at."""
    client = _get_client()
    result = (
        client.table("chat_sessions")
        .select("id, title, started_at")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


# ── chat_messages ─────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    msg_index: int,
    role: str,
    content: str,
    tools_used: list,
    sources: list,
) -> str:
    """
    Persist one chat_display item. Returns the message UUID.
    sources is list of (type, id) tuples or lists — coerced to list-of-lists for JSONB.
    """
    client = _get_client()
    result = (
        client.table("chat_messages")
        .insert(
            {
                "session_id": session_id,
                "msg_index": msg_index,
                "role": role,
                "content": content,
                "tools_used": list(tools_used),
                "sources": [list(s) for s in sources],
            }
        )
        .execute()
    )
    return result.data[0]["id"]


def load_session_messages(session_id: str) -> list[dict]:
    """Return all messages for a session ordered by msg_index. Each dict has id, msg_index, role, content, tools_used, sources."""
    client = _get_client()
    result = (
        client.table("chat_messages")
        .select("id, msg_index, role, content, tools_used, sources")
        .eq("session_id", session_id)
        .order("msg_index", desc=False)
        .execute()
    )
    return result.data


# ── feedback ──────────────────────────────────────────────────────────────────

def upsert_feedback(message_id: str, user_id: str, vote: str) -> None:
    """Insert or update a 👍/👎 vote. Idempotent — calling twice updates the existing row."""
    client = _get_client()
    client.table("feedback").upsert(
        {"message_id": message_id, "user_id": user_id, "vote": vote},
        on_conflict="message_id,user_id",
    ).execute()


def load_session_feedback(session_id: str, user_id: str) -> dict[str, str]:
    """Return {message_id: vote} for all messages in this session that the user has voted on."""
    client = _get_client()
    msgs = (
        client.table("chat_messages")
        .select("id")
        .eq("session_id", session_id)
        .execute()
    )
    if not msgs.data:
        return {}
    msg_ids = [row["id"] for row in msgs.data]
    result = (
        client.table("feedback")
        .select("message_id, vote")
        .eq("user_id", user_id)
        .in_("message_id", msg_ids)
        .execute()
    )
    return {row["message_id"]: row["vote"] for row in result.data}
