"""
OpenClaw/agent integration: spawn, send, stop, prompts, guardrails.
"""

import httpx
from typing import Optional
from datetime import datetime

from app.config import (
    OPENCLAW_ENABLED, OPENCLAW_GATEWAY_URL, OPENCLAW_TOKEN,
    TASKBOARD_BASE_URL, AGENT_TO_OPENCLAW_ID,
    MAIN_AGENT_NAME, MAIN_AGENT_EMOJI, HUMAN_SUPERVISOR_LABEL,
    PROJECT_NAME, COMPANY_NAME, COMPANY_CONTEXT,
    ALLOWED_PATHS, COMPLIANCE_FRAMEWORKS,
)
from app.database import get_db


# =============================================================================
# SECURITY HELPERS (notify, send, session management)
# =============================================================================

async def notify_OPENCLAW(task_id: int, task_title: str, comment_agent: str, comment_content: str):
    """Send webhook to OpenClaw when a comment needs attention."""
    if not OPENCLAW_ENABLED or comment_agent == MAIN_AGENT_NAME:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "action": "wake",
                "text": f"\U0001f4ac Task Board: New comment on #{task_id} ({task_title}) from {comment_agent}:\n\n{comment_content[:200]}{'...' if len(comment_content) > 200 else ''}\n\nCheck and respond: {TASKBOARD_BASE_URL}"
            }
            headers = {
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            }
            await client.post(f"{OPENCLAW_GATEWAY_URL}/api/cron/wake", json=payload, headers=headers)
            print(f"Notified OPENCLAW about comment from {comment_agent}")
    except Exception as e:
        print(f"Webhook to OPENCLAW failed: {e}")


async def send_to_agent_session(session_key: str, message: str) -> bool:
    """Send a follow-up message to an active agent session."""
    if not OPENCLAW_ENABLED or not session_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "tool": "sessions_send",
                "args": {
                    "sessionKey": session_key,
                    "message": message
                }
            }
            headers = {
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{OPENCLAW_GATEWAY_URL}/tools/invoke",
                json=payload,
                headers=headers
            )
            result = response.json() if response.status_code == 200 else None
            if result and result.get("ok"):
                print(f"\u2705 Sent message to session {session_key}")
                return True
            else:
                print(f"\u274c Failed to send to session: {response.text}")
                return False
    except Exception as e:
        print(f"\u274c Failed to send to agent session: {e}")
        return False


def get_task_session(task_id: int) -> Optional[str]:
    """Get the active agent session key for a task."""
    with get_db() as conn:
        row = conn.execute("SELECT agent_session_key FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row["agent_session_key"] if row and row["agent_session_key"] else None


def set_task_session(task_id: int, session_key: Optional[str]):
    """Set or clear the agent session key for a task."""
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET agent_session_key = ?, updated_at = ? WHERE id = ?",
            (session_key, datetime.now().isoformat(), task_id)
        )
        conn.commit()


# =============================================================================
# GUARDRAILS & PROMPTS
# =============================================================================

AGENT_GUARDRAILS = f"""
\u26a0\ufe0f MANDATORY CONSTRAINTS (Approved by User via Task Board assignment):

FILESYSTEM BOUNDARIES:
- ONLY access: {ALLOWED_PATHS}
- Everything else is FORBIDDEN without explicit authorization

FORBIDDEN ACTIONS (do not attempt without approval):
- Browser tool (except UX Manager on localhost only)
- git commit (requires safeword from User)
- Any action outside the authorized paths

WEB_FETCH (requires approval):
- You have web_fetch available but MUST ask User first
- Create an action item (type: question) explaining what URL you need and why
- Wait for User to resolve the action item before fetching
- Only fetch after explicit approval

COMPLIANCE CONTEXT:
- {COMPANY_NAME}, {COMPANY_CONTEXT}
- {COMPLIANCE_FRAMEWORKS}
- Security over convenience \u2014 always

COMMUNICATION & ESCALATION:
- Post comments on the task card to communicate
- Create action items for questions that need answers (type: question)
- Create action items for blockers (type: blocker)

ESCALATION CHAIN:
1. {MAIN_AGENT_NAME} (coordinator) monitors your action items and may answer if confident
2. If {MAIN_AGENT_NAME} answers, the item gets resolved and you can proceed
3. If {MAIN_AGENT_NAME} is unsure, they leave it for {HUMAN_SUPERVISOR_LABEL} to review
4. {HUMAN_SUPERVISOR_LABEL} has final authority on all decisions

TASK BOARD INTEGRATION:
- Use start-work API when beginning: POST {TASKBOARD_BASE_URL}/api/tasks/{{task_id}}/start-work?agent={{your_name}}
- Post updates as comments: POST {TASKBOARD_BASE_URL}/api/tasks/{{task_id}}/comments (json: {{"agent": "your_name", "content": "message"}})
- Create action items for questions: POST {TASKBOARD_BASE_URL}/api/tasks/{{task_id}}/action-items (json: {{"agent": "your_name", "content": "question", "item_type": "question"}})
- Move to Review when done: POST {TASKBOARD_BASE_URL}/api/tasks/{{task_id}}/move?status=Review&agent={{your_name}}&reason=...
- Use stop-work API when finished: POST {TASKBOARD_BASE_URL}/api/tasks/{{task_id}}/stop-work

REPORT FORMAT:
When complete, post a comment with your findings using this format:
## [Your Role] Report
**Task:** [task title]
**Verdict:** \u2705 APPROVED / \u26a0\ufe0f CONCERNS / \U0001f6d1 BLOCKED
### Findings
- [SEVERITY] Issue description
### Summary
[1-2 sentence assessment]
"""

AGENT_SYSTEM_PROMPTS = {
    "main": f"""You are {MAIN_AGENT_NAME}, the primary coordinator for {COMPANY_NAME}.

Your focus:
- General task implementation and coordination
- Code writing and debugging
- Cross-cutting concerns that don't fit specialist roles
- Synthesizing input from other agents
- Direct implementation work

Project: {PROJECT_NAME}
You're the hands-on executor. When assigned a task, dig in and get it done.""",

    "architect": f"""You are the Architect for {COMPANY_NAME}.

Your focus:
- System design and architectural patterns
- Scalability and performance implications
- Technical trade-offs and recommendations
- Integration architecture
- Database design and data modeling

Project: {PROJECT_NAME}
Be concise. Flag concerns with severity (CRITICAL/HIGH/MEDIUM/LOW).""",

    "security-auditor": f"""You are the Security Auditor for {COMPANY_NAME}.

Your focus:
- SOC2 Trust Services Criteria (Security, Availability, Confidentiality, Privacy)
- HIPAA compliance (PHI handling, access controls, audit logging)
- CIS Controls benchmarks
- OWASP Top 10 vulnerabilities
- Secure credential storage and handling
- Tenant data isolation (multi-tenant SaaS)

NON-NEGOTIABLE: Security over convenience. Always.
Rate findings: CRITICAL (blocks deploy) / HIGH / MEDIUM / LOW""",

    "code-reviewer": f"""You are the Code Reviewer for {COMPANY_NAME}.

Your focus:
- Code quality and best practices
- DRY, SOLID principles
- Error handling and edge cases
- Performance considerations
- Code readability and maintainability
- Test coverage gaps

Project: {PROJECT_NAME}
Format: MUST FIX / SHOULD FIX / CONSIDER / NICE TO HAVE""",

    "ux-manager": f"""You are the UX Manager for {COMPANY_NAME}.

Your focus:
- User flow clarity and efficiency
- Error message helpfulness
- Form design and validation feedback
- UI consistency across the platform
- Accessibility basics
- Onboarding experience

Project: {PROJECT_NAME}

BROWSER ACCESS (localhost only):
You have browser access to review the app UI. Use it to:
- Take snapshots of pages to analyze layout, spacing, colors
- Check user flows and navigation
- Verify form designs and error states
- Assess overall visual consistency

ALLOWED URLs (localhost only):
- http://localhost:* (any port)
- http://127.0.0.1:*

DO NOT navigate to any external URLs. Your browser access is strictly for reviewing the local app."""
}

_spawning_tasks = set()


async def spawn_agent_session(task_id: int, task_title: str, task_description: str, agent_name: str):
    """Spawn an OpenClaw sub-agent session for a task via tools/invoke API."""
    print(f"\U0001f680 SPAWN-AGENT: Task #{task_id} | Agent: {agent_name}")

    if task_id in _spawning_tasks:
        print(f"\u23e9 SPAWN-AGENT SKIPPED: Already spawning for task #{task_id}")
        return None
    _spawning_tasks.add(task_id)

    try:
        return await _do_spawn_agent_session(task_id, task_title, task_description, agent_name)
    finally:
        _spawning_tasks.discard(task_id)


async def _do_spawn_agent_session(task_id: int, task_title: str, task_description: str, agent_name: str):
    """Internal spawn implementation."""
    if not OPENCLAW_ENABLED:
        print(f"\u26a0\ufe0f  SPAWN-AGENT SKIPPED: OpenClaw not enabled (OPENCLAW_TOKEN not set)")
        return None

    agent_id = AGENT_TO_OPENCLAW_ID.get(agent_name)
    if not agent_id:
        print(f"\u26a0\ufe0f  SPAWN-AGENT SKIPPED: Unknown agent '{agent_name}' (not in AGENT_TO_OPENCLAW_ID)")
        return None

    print(f"\U0001f50d SPAWN-AGENT: Mapped {agent_name} \u2192 {agent_id}")

    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_id, "")
    task_prompt = f"""# Task Assignment from RIZQ Task Board (Approved by {HUMAN_SUPERVISOR_LABEL})

**Task #{task_id}:** {task_title}

**Description:**
{task_description or 'No description provided.'}

{AGENT_GUARDRAILS}

## Your Role
{system_prompt}

---

## API Base URL (MANDATORY \u2014 do NOT use localhost or 127.0.0.1)
All Task Board API calls MUST use this base URL: {TASKBOARD_BASE_URL}
Do NOT use localhost, 127.0.0.1, or any other address. The task board is ONLY reachable at {TASKBOARD_BASE_URL}.

## Instructions
1. Call start-work API: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/start-work?agent={agent_name}
   - This auto-moves the card to "In Progress" if needed
2. Analyze the task thoroughly
3. Post your findings as a comment: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/comments (json: {{"agent": "{agent_name}", "content": "your message"}})
4. When done, call stop-work with outcome: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/stop-work?agent={agent_name}&outcome=review&reason=<summary>
   - Use outcome=review when work is complete (auto-moves to Review)
   - Use outcome=blocked&reason=<why> if you need input (auto-moves to Blocked)

## IMPORTANT: Stay Available
After posting your findings, **remain available for follow-up questions**. User may reply with questions or requests for clarification. When you receive a message starting with "\U0001f4ac **User replied**", respond thoughtfully and post your response as a comment on the task.

Your session will automatically end when User marks the task as Done.

Begin now.
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "tool": "sessions_spawn",
                "args": {
                    "agentId": agent_id,
                    "task": task_prompt,
                    "label": f"task-{task_id}",
                    "cleanup": "keep"
                }
            }
            headers = {
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            }

            print(f"\U0001f4e1 SPAWN-AGENT: Calling OpenClaw API - {OPENCLAW_GATEWAY_URL}/tools/invoke")
            print(f"\U0001f4e6 SPAWN-AGENT: Payload - tool: sessions_spawn, agentId: {agent_id}, label: task-{task_id}")

            response = await client.post(
                f"{OPENCLAW_GATEWAY_URL}/tools/invoke",
                json=payload,
                headers=headers
            )

            print(f"\U0001f4e5 SPAWN-AGENT: Response status: {response.status_code}")

            result = response.json() if response.status_code == 200 else None
            print(f"\U0001f4e5 SPAWN-AGENT: Response body: {result}")

            if result and result.get("ok"):
                raw_result = result.get("result", {})
                spawn_info = raw_result.get("details", raw_result)
                run_id = spawn_info.get("runId", "unknown")
                session_key = spawn_info.get("childSessionKey", None)

                print(f"\u2705 SPAWN-AGENT SUCCESS: {agent_name} ({agent_id}) for task #{task_id}")
                print(f"\U0001f4cb SPAWN-AGENT: Session key: {session_key} | Run ID: {run_id}")

                if session_key:
                    print(f"\U0001f4be SPAWN-AGENT: Saving session key to database")
                    set_task_session(task_id, session_key)
                else:
                    print(f"\u26a0\ufe0f  SPAWN-AGENT: No session key in response!")

                print(f"\U0001f4ac SPAWN-AGENT: Posting spawn notification comment")
                async with httpx.AsyncClient(timeout=5.0) as comment_client:
                    await comment_client.post(
                        f"{TASKBOARD_BASE_URL}/api/tasks/{task_id}/comments",
                        json={
                            "agent": "System",
                            "content": f"\U0001f916 **{agent_name}** agent spawned automatically.\n\nSession: `{session_key or 'unknown'}`\nRun ID: `{run_id}`\n\n\U0001f4ac *Reply to this task and the agent will respond.*"
                        }
                    )
                print(f"\u2705 SPAWN-AGENT COMPLETE")
                return result
            else:
                error_msg = response.text if response.status_code != 200 else result
                print(f"\u274c SPAWN-AGENT FAILED: Status {response.status_code}")
                print(f"\u274c SPAWN-AGENT ERROR: {error_msg}")
                return None
    except Exception as e:
        print(f"\u274c SPAWN-AGENT EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"\u274c SPAWN-AGENT TRACEBACK: {traceback.format_exc()}")
        return None


async def spawn_followup_session(task_id: int, task_title: str, agent_name: str, previous_context: str, new_message: str):
    """Spawn a follow-up session for an agent with conversation context."""
    if not OPENCLAW_ENABLED:
        return None

    agent_id = AGENT_TO_OPENCLAW_ID.get(agent_name)
    if not agent_id:
        return None

    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_id, "")

    followup_prompt = f"""# Follow-up on Task #{task_id}: {task_title}

You previously worked on this task and moved it to Review. User has a follow-up question.

## Previous Conversation:
{previous_context if previous_context else "(No previous messages)"}

## User's New Message:
{new_message}

## Your Role:
{system_prompt}

## API Base URL (MANDATORY \u2014 do NOT use localhost or 127.0.0.1)
All Task Board API calls MUST use this base URL: {TASKBOARD_BASE_URL}

## Instructions:
1. Call start-work API: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/start-work?agent={agent_name}
2. Read the context and User's question
3. Respond helpfully by posting a comment: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/comments (json: {{"agent": "{agent_name}", "content": "your message"}})
4. Keep your response focused on what User asked
5. Call stop-work API: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/stop-work?agent={agent_name}
   - Add &outcome=review&reason=<summary> if work is complete
   - Add &outcome=blocked&reason=<why> if you need more input

Respond now.
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "tool": "sessions_spawn",
                "args": {
                    "agentId": agent_id,
                    "task": followup_prompt,
                    "label": f"task-{task_id}-followup",
                    "cleanup": "keep"
                }
            }
            headers = {
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{OPENCLAW_GATEWAY_URL}/tools/invoke",
                json=payload,
                headers=headers
            )
            result = response.json() if response.status_code == 200 else None
            if result and result.get("ok"):
                raw_result = result.get("result", {})
                spawn_info = raw_result.get("details", raw_result)
                session_key = spawn_info.get("childSessionKey", None)
                if session_key:
                    set_task_session(task_id, session_key)
                print(f"\u2705 Spawned follow-up session for {agent_name} on task #{task_id}")
                return result
            else:
                print(f"\u274c Failed to spawn follow-up: {response.text}")
                return None
    except Exception as e:
        print(f"\u274c Failed to spawn follow-up session: {e}")
        return None


async def spawn_mentioned_agent(task_id: int, task_title: str, task_description: str,
                                 mentioned_agent: str, mentioner: str, comment_content: str,
                                 previous_context: str = ""):
    """Spawn a session for an @mentioned agent to contribute to a task they don't own."""
    if not OPENCLAW_ENABLED:
        return None

    agent_id = AGENT_TO_OPENCLAW_ID.get(mentioned_agent)
    if not agent_id:
        return None

    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_id, "")

    mention_prompt = f"""# You've Been Tagged: Task #{task_id}

**{mentioner}** mentioned you on a task and needs your input.

## Task: {task_title}
{task_description or '(No description)'}

## What {mentioner} Said:
{comment_content}

## Previous Conversation:
{previous_context if previous_context else "(No prior comments)"}

## Your Role:
{system_prompt}

## Instructions:
1. Call start-work API: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/start-work?agent={mentioned_agent}
2. Review the task from YOUR perspective ({mentioned_agent})
3. Post your findings/response as a comment: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/comments
4. Call stop-work API: POST {TASKBOARD_BASE_URL}/api/tasks/{task_id}/stop-work?agent={mentioned_agent}

**Note:** You are NOT the assigned owner of this task. You're providing your expertise because you were tagged.
Do NOT move the task (no outcome param) \u2014 that's the owner's job.

{AGENT_GUARDRAILS}

Respond now with your assessment.
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "tool": "sessions_spawn",
                "args": {
                    "agentId": agent_id,
                    "task": mention_prompt,
                    "label": f"task-{task_id}-mention-{agent_id}",
                    "cleanup": "delete"
                }
            }
            headers = {
                "Authorization": f"Bearer {OPENCLAW_TOKEN}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                f"{OPENCLAW_GATEWAY_URL}/tools/invoke",
                json=payload,
                headers=headers
            )
            result = response.json() if response.status_code == 200 else None
            if result and result.get("ok"):
                raw_result = result.get("result", {})
                spawn_info = raw_result.get("details", raw_result)
                session_key = spawn_info.get("childSessionKey", "unknown")

                async with httpx.AsyncClient(timeout=5.0) as comment_client:
                    await comment_client.post(
                        f"{TASKBOARD_BASE_URL}/api/tasks/{task_id}/comments",
                        json={
                            "agent": "System",
                            "content": f"\U0001f4e2 **{mentioned_agent}** was tagged by {mentioner} and is now reviewing this task."
                        }
                    )

                print(f"\u2705 Spawned {mentioned_agent} for mention on task #{task_id}")
                return result
            else:
                print(f"\u274c Failed to spawn {mentioned_agent} for mention: {response.text}")
                return None
    except Exception as e:
        print(f"\u274c Failed to spawn mentioned agent: {e}")
        return None
