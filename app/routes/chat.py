"""
Chat: Jarvis history, chat, respond endpoints + legacy endpoints.
"""

import json
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException

import httpx

from app.config import (
    OPENCLAW_ENABLED, OPENCLAW_GATEWAY_URL, OPENCLAW_TOKEN,
    TASKBOARD_API_KEY, DATA_DIR,
)
from app.database import get_db
from app.models import JarvisMessage, JarvisResponse
from app.websocket import manager

router = APIRouter()


def verify_api_key(authorization: str = Header(None), x_api_key: str = Header(None)):
    """Verify API key from Authorization header or X-API-Key header."""
    if not TASKBOARD_API_KEY:
        return True
    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            if secrets.compare_digest(token, TASKBOARD_API_KEY):
                return True
    if x_api_key:
        if secrets.compare_digest(x_api_key, TASKBOARD_API_KEY):
            return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.get("/api/jarvis/history")
def get_chat_history(limit: int = 100, session: str = "main"):
    """Get command bar chat history from database, filtered by session."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, session_key, role, content, attachments, created_at FROM chat_messages WHERE session_key = ? ORDER BY id DESC LIMIT ?",
            (session, limit)
        ).fetchall()
        messages = []
        for row in reversed(rows):
            msg = {
                "id": row["id"],
                "session_key": row["session_key"],
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["created_at"]
            }
            if row["attachments"]:
                msg["attachments"] = json.loads(row["attachments"])
            messages.append(msg)
        return {"history": messages, "session": session}


@router.post("/api/jarvis/chat")
async def chat_with_jarvis(msg: JarvisMessage):
    """Send a message to Jarvis via sessions_send."""
    if not OPENCLAW_ENABLED:
        return {"sent": False, "error": "OpenClaw integration not enabled."}

    now = datetime.now().isoformat()
    message_content = f"System: [TASKBOARD_CHAT] User says: {msg.message}\n\nRespond naturally."

    if msg.attachments:
        import base64 as b64_module
        import uuid

        attachments_dir = DATA_DIR / "attachments"
        attachments_dir.mkdir(exist_ok=True)

        for att in msg.attachments:
            att_type = att.get("type", "")
            att_data = att.get("data", "")
            att_filename = att.get("filename", "file")

            if att_type.startswith("image/") and att_data:
                try:
                    if att_data.startswith("data:") and ";base64," in att_data:
                        b64_content = att_data.split(",", 1)[1]
                    else:
                        b64_content = att_data
                    ext = att_type.split("/")[1].split(";")[0]
                    if ext not in ["png", "jpg", "jpeg", "gif", "webp"]:
                        ext = "png"
                    img_filename = f"{uuid.uuid4().hex[:8]}_{att_filename or 'image'}"
                    if not img_filename.endswith(f".{ext}"):
                        img_filename = f"{img_filename}.{ext}"
                    img_path = attachments_dir / img_filename
                    with open(img_path, "wb") as f:
                        f.write(b64_module.b64decode(b64_content))
                    message_content += f"\n\n\U0001f4f7 **Image attached:** `/app/data/attachments/{img_filename}`\nUse the Read tool to view this image."
                except Exception as e:
                    print(f"Failed to save image attachment: {e}")
                    message_content += f"\n\n[Image attachment failed to save: {e}]"
            elif att_data:
                if att_data.startswith("data:") and ";base64," in att_data:
                    try:
                        import base64
                        b64_content = att_data.split(",", 1)[1]
                        decoded = base64.b64decode(b64_content).decode("utf-8", errors="replace")
                        message_content += f"\n\n**\U0001f4ce Attached file: {att_filename}**\n```\n{decoded}\n```"
                    except Exception as e:
                        message_content += f"\n\n[Attached File: {att_filename} (decode error: {e})]"
                else:
                    message_content += f"\n\n[Attached File: {att_filename}]"

    session_key = msg.session or "main"

    attachments_json = json.dumps(msg.attachments) if msg.attachments else None
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_messages (session_key, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_key, "user", msg.message, attachments_json, now)
        )
        conn.commit()
        user_msg_id = cursor.lastrowid

    user_msg = {
        "id": user_msg_id, "session_key": session_key, "role": "user",
        "content": msg.message, "timestamp": now, "attachments": msg.attachments
    }
    await manager.broadcast({"type": "command_bar_message", "message": user_msg})

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "tool": "sessions_send",
                "args": {"message": message_content, "sessionKey": session_key, "timeoutSeconds": 90}
            }
            headers = {"Authorization": f"Bearer {OPENCLAW_TOKEN}", "Content-Type": "application/json"}
            response = await client.post(f"{OPENCLAW_GATEWAY_URL}/tools/invoke", json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                inner = result.get("result", {})
                if isinstance(inner, dict):
                    details = inner.get("details", {})
                    assistant_reply = details.get("reply") or inner.get("reply") or inner.get("response")
                else:
                    assistant_reply = str(inner) if inner else None

                if assistant_reply and not isinstance(assistant_reply, str):
                    import json as json_module
                    assistant_reply = json_module.dumps(assistant_reply) if isinstance(assistant_reply, (dict, list)) else str(assistant_reply)

                if assistant_reply:
                    with get_db() as conn:
                        cursor = conn.execute(
                            "INSERT INTO chat_messages (session_key, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
                            (session_key, "assistant", assistant_reply, None, now)
                        )
                        conn.commit()
                        assistant_msg_id = cursor.lastrowid

                    jarvis_msg = {
                        "id": assistant_msg_id, "session_key": session_key,
                        "role": "assistant", "content": assistant_reply,
                        "timestamp": datetime.now().isoformat()
                    }
                    return {"sent": True, "response": assistant_reply, "session": session_key}

                return {"sent": True, "response": "No response received"}
            else:
                error_text = response.text[:200] if response.text else f"HTTP {response.status_code}"
                return {"sent": False, "error": error_text}
    except Exception as e:
        print(f"Error sending to Jarvis: {e}")
        return {"sent": False, "error": str(e)}


@router.post("/api/jarvis/respond")
async def jarvis_respond(msg: JarvisResponse, _: bool = Depends(verify_api_key)):
    """Endpoint for Jarvis to push responses back to the command bar. Requires API key."""
    now = datetime.now().isoformat()
    session_key = msg.session or "main"

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_messages (session_key, role, content, attachments, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_key, "assistant", msg.response, None, now)
        )
        conn.commit()
        msg_id = cursor.lastrowid

    jarvis_msg = {
        "id": msg_id, "session_key": session_key,
        "role": "assistant", "content": msg.response, "timestamp": now
    }
    await manager.broadcast({"type": "command_bar_message", "message": jarvis_msg})
    return {"delivered": True}


# Legacy endpoints
@router.post("/api/molt/chat")
async def chat_with_molt_legacy(msg: JarvisMessage):
    """Legacy endpoint - redirects to /api/jarvis/chat."""
    return await chat_with_jarvis(msg)


@router.post("/api/molt/respond")
async def jarvis_respond_legacy(msg: JarvisResponse, _: bool = Depends(verify_api_key)):
    """Legacy endpoint - redirects to /api/jarvis/respond."""
    return await jarvis_respond(msg, _)
