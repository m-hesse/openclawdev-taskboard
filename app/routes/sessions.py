"""
Sessions: list, create, stop, stop-all, delete OpenClaw sessions.
"""

import json
import os
from datetime import datetime
from fastapi import APIRouter

from app.config import OPENCLAW_ENABLED, OPENCLAW_GATEWAY_URL, OPENCLAW_TOKEN
from app.database import get_db
from app.models import SessionCreate
from app.websocket import manager

import httpx

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions():
    """Proxy to OpenClaw sessions_list to get active sessions."""
    if not OPENCLAW_ENABLED:
        return {"sessions": [], "error": "OpenClaw integration not enabled"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"tool": "sessions_list", "args": {"limit": 20, "messageLimit": 0}}
            headers = {"Authorization": f"Bearer {OPENCLAW_TOKEN}", "Content-Type": "application/json"}
            response = await client.post(f"{OPENCLAW_GATEWAY_URL}/tools/invoke", json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    inner_result = result.get("result", {})
                    content = inner_result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        sessions_data = json.loads(text_content)
                    else:
                        sessions_data = inner_result
                    sessions = sessions_data.get("sessions", [])

                    formatted = []
                    for s in sessions:
                        key = s.get("key", "")
                        session_label = s.get("label", "")
                        display = s.get("displayName", key)
                        if key == "main" or key == "agent:main:main":
                            label = "\U0001f6e1\ufe0f Jarvis (Main)"
                        elif session_label:
                            label = f"\U0001f916 {session_label}"
                        elif "subagent" in key:
                            short_id = key.split(":")[-1][:8] if ":" in key else key[:8]
                            label = f"\U0001f916 Session {short_id}"
                        elif key.startswith("agent:"):
                            parts = key.split(":")
                            agent_name = parts[1] if len(parts) > 1 else key
                            label = f"\U0001f916 {agent_name.title()}"
                        else:
                            label = display
                        formatted.append({
                            "key": key, "label": label, "channel": s.get("channel", ""),
                            "model": s.get("model", ""), "updatedAt": s.get("updatedAt", 0)
                        })

                    openclaw_keys = set(s["key"] for s in formatted)
                    with get_db() as conn:
                        deleted_rows = conn.execute("SELECT session_key FROM deleted_sessions").fetchall()
                        deleted_keys = set(row["session_key"] for row in deleted_rows)
                        orphaned_keys = deleted_keys - openclaw_keys
                        if orphaned_keys:
                            placeholders = ",".join("?" * len(orphaned_keys))
                            conn.execute(f"DELETE FROM deleted_sessions WHERE session_key IN ({placeholders})", list(orphaned_keys))
                            conn.commit()

                    formatted = [s for s in formatted if s["key"] not in deleted_keys]
                    formatted.sort(key=lambda x: (0 if "main" in x["key"].lower() else 1, -x.get("updatedAt", 0)))
                    return {"sessions": formatted}

            return {"sessions": [], "error": f"Failed to fetch sessions: {response.status_code}"}
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return {"sessions": [], "error": str(e)}


@router.post("/api/sessions/create")
async def create_session(req: SessionCreate):
    """Create a new OpenClaw session via sessions_spawn."""
    if not OPENCLAW_ENABLED:
        return {"success": False, "error": "OpenClaw integration not enabled"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "tool": "sessions_spawn",
                "args": {
                    "agentId": req.agentId,
                    "task": req.task,
                    "label": req.label or f"taskboard-{datetime.now().strftime('%H%M%S')}",
                    "cleanup": "keep"
                }
            }
            headers = {"Authorization": f"Bearer {OPENCLAW_TOKEN}", "Content-Type": "application/json"}
            response = await client.post(f"{OPENCLAW_GATEWAY_URL}/tools/invoke", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return {"success": True, "result": result.get("result", {})}
            return {"success": False, "error": f"Failed: {response.status_code}"}
    except Exception as e:
        print(f"Error creating session: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/sessions/{session_key}/stop")
async def stop_session(session_key: str):
    """Stop/abort a running session."""
    if not OPENCLAW_ENABLED:
        return {"success": False, "error": "OpenClaw integration not enabled"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "tool": "sessions_send",
                "args": {"sessionKey": session_key, "message": "SYSTEM: ABORT - User requested stop from Task Board"}
            }
            headers = {"Authorization": f"Bearer {OPENCLAW_TOKEN}", "Content-Type": "application/json"}
            await client.post(f"{OPENCLAW_GATEWAY_URL}/tools/invoke", json=payload, headers=headers)
            try:
                abort_response = await client.post(
                    f"{OPENCLAW_GATEWAY_URL}/api/sessions/{session_key}/abort", headers=headers
                )
                if abort_response.status_code == 200:
                    return {"success": True, "message": f"Stopped session: {session_key}"}
            except:
                pass
            return {"success": True, "message": f"Stop signal sent to: {session_key}"}
    except Exception as e:
        print(f"Error stopping session: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/sessions/stop-all")
async def stop_all_sessions():
    """Emergency stop all non-main sessions."""
    if not OPENCLAW_ENABLED:
        return {"success": False, "error": "OpenClaw integration not enabled"}
    stopped = []
    errors = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"tool": "sessions_list", "args": {"limit": 50, "messageLimit": 0}}
            headers = {"Authorization": f"Bearer {OPENCLAW_TOKEN}", "Content-Type": "application/json"}
            response = await client.post(f"{OPENCLAW_GATEWAY_URL}/tools/invoke", json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    inner_result = result.get("result", {})
                    content = inner_result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        sessions_data = json.loads(text_content)
                    else:
                        sessions_data = inner_result
                    sessions = sessions_data.get("sessions", [])
                    for s in sessions:
                        key = s.get("key", "")
                        if key and "main" not in key.lower():
                            try:
                                stop_result = await stop_session(key)
                                if stop_result.get("success"):
                                    stopped.append(key)
                                else:
                                    errors.append(key)
                            except:
                                errors.append(key)
        return {"success": True, "stopped": stopped, "errors": errors, "message": f"Stopped {len(stopped)} sessions"}
    except Exception as e:
        print(f"Error stopping all sessions: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/api/sessions/{session_key}")
async def delete_session(session_key: str):
    """Close/delete a session."""
    if not OPENCLAW_ENABLED:
        return {"success": False, "error": "OpenClaw integration not enabled"}

    await stop_session(session_key)
    now = datetime.now().isoformat()

    with get_db() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_key = ?", (session_key,))
        conn.execute("INSERT OR REPLACE INTO deleted_sessions (session_key, deleted_at) VALUES (?, ?)", (session_key, now))
        conn.commit()

    openclaw_deleted = False
    try:
        parts = session_key.split(":")
        if len(parts) >= 2 and parts[0] == "agent":
            agent_id = parts[1]
            openclaw_home = os.environ.get("OPENCLAW_DATA_PATH", os.path.expanduser("~/.openclaw"))
            sessions_file = os.path.join(openclaw_home, "agents", agent_id, "sessions", "sessions.json")
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                session_id = None
                if session_key in sessions_data:
                    session_id = sessions_data[session_key].get("sessionId")
                    del sessions_data[session_key]
                    with open(sessions_file, 'w', encoding='utf-8') as f:
                        json.dump(sessions_data, f, indent=2)
                    openclaw_deleted = True
                    print(f"Deleted session {session_key} from OpenClaw store")
                    if session_id:
                        transcript_file = os.path.join(openclaw_home, "agents", agent_id, "sessions", f"{session_id}.jsonl")
                        if os.path.exists(transcript_file):
                            os.remove(transcript_file)
                            print(f"Deleted transcript {transcript_file}")
    except Exception as e:
        print(f"Warning: Could not delete from OpenClaw store: {e}")

    await manager.broadcast({"type": "session_deleted", "session_key": session_key})
    return {"success": True, "message": f"Deleted session: {session_key}", "openclaw_deleted": openclaw_deleted}
