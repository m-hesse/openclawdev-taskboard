# </> DEV Task Board

A real-time Kanban board designed for **multi-agent AI workflows** with [OpenClaw](https://github.com/openclaw/openclaw). Assign tasks to AI agents, watch them work in real-time, and collaborate through persistent chat sessions.

![Task Board Preview](https://img.shields.io/badge/Status-Production_Ready-green) ![License](https://img.shields.io/badge/License-MIT-blue) ![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-purple)


https://github.com/user-attachments/assets/104ebd11-c407-4c34-b0f6-0a34027b4d8f



https://github.com/user-attachments/assets/fc4237c9-c4e5-437d-8638-1a51e8eb6219


---

## 📋 Changelog

### v1.6.0 (2026-02-03)

#### ✨ New Features
- **Chat Message Actions** — Reply (↩), Copy (📋), and Delete (🗑) buttons on all messages
- **Multi-Reply Support** — Reply to multiple messages at once with stacked previews
- **Delete Comments API** — `DELETE /api/tasks/{id}/comments/{comment_id}` for removing messages

#### 🔧 Improvements
- **Larger Command Bar** — Chat window expanded from 600×400px to 720×500px
- **Event Delegation** — All button handlers now use event delegation for reliability

#### 🐛 Bug Fixes
- Fixed reply button only working on user messages (selector mismatch)
- Fixed @mention spawning assigned agent when only other agents were tagged
- Fixed inline onclick handlers breaking on messages with special characters

### v1.5.0 (2026-02-02)

#### ✨ New Features
- **Column Sorting** — Each column now has a sort dropdown with options:
  - Priority (Critical → Low)
  - Latest (most recent activity first)
  - Agent (alphabetical by assignee)
  - Custom (drag-and-drop reordering)
- **Multi-Agent Thinking Indicators** — Cards and chat now show all working agents simultaneously with animated dot + icon
- **Consistent Indicator Styling** — Unified glowing dot + icon animation across card headers, chat section, and command bar

#### 🔧 Improvements
- **Auto-Clear Working Status** — Agent's "thinking" indicator automatically clears when they post a comment
- **Skip Redundant Spawns** — Moving a card to "In Progress" won't re-spawn an agent that's already working on it
- **Enforced Start/Stop Work Calls** — All agent spawn instructions now require start-work/stop-work API calls for consistent indicator behavior

#### 🐛 Bug Fixes
- Fixed thinking indicator not clearing when agent finishes work
- Fixed duplicate agent spawns when moving cards already being worked on

---

## ✨ Features

### 🎯 Core Functionality
- **Live Kanban Board** — Real-time updates via WebSocket
- **Multi-Agent Support** — Assign tasks to different AI agents
- **Auto-Spawn Sessions** — Agents automatically activate when tasks move to "In Progress"
- **Persistent Conversations** — Back-and-forth chat with agents on each task
- **Session Isolation** — Each agent maintains separate context per task

### 🤖 AI Agents (Configurable via .env)
| Icon | Agent | Focus |
|------|-------|-------|
| 🤖 | Main Agent | Coordinator, command bar chat (name configurable) |
| 🏛️ | Architect | System design, patterns, scalability |
| 🔒 | Security Auditor | SOC2, HIPAA, CIS compliance |
| 📋 | Code Reviewer | Code quality, best practices |
| 🎨 | UX Manager | User flows, UI consistency |

### 💬 Communication
- **Command Bar** — Direct chat with your main agent from the header
- **@Mentions** — Tag agents into any task conversation
- **Action Items** — Questions, blockers, and completion tracking
- **File Attachments** — Paste images or attach documents

### 🔒 Security
- API key authentication for sensitive endpoints
- Secrets stored in environment variables
- CORS restricted to localhost
- Input validation and size limits
- Agent guardrails (filesystem boundaries, forbidden actions)

## 🚀 Quick Start

### Prerequisites
- [Docker](https://www.docker.com/get-started) & Docker Compose
- [OpenClaw](https://github.com/openclaw/openclaw) running locally

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/openclaw-taskboard.git
   cd openclaw-taskboard
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenClaw token and generate an API key
   ```

3. **Start the task board**
   ```bash
   docker-compose up -d
   ```

4. **Open in browser**
   ```
   http://localhost:8080
   ```

---

## 🤖 AI-Assisted Setup

The easiest way to set up the task board is to **ask your OpenClaw agent to do it for you!**

### Connecting the Task Board (Channel Plugin)

Once the task board is running, prompt your OpenClaw agent:

```
I have the task board running at http://localhost:8080. 
Please onboard it as a channel plugin so you can receive 
messages from the command bar and spawn sub-agents when 
tasks move to "In Progress".
```

Your agent will:
1. Update the `.env` with the correct gateway URL and token
2. Verify the connection is working
3. Test the `/tools/invoke` API

### Onboarding the Dev Team (Sub-Agents)

To set up the multi-agent dev team, prompt your agent:

```
I want to set up the dev team sub-agents (Architect, Security Auditor, 
Code Reviewer, UX Manager). Please configure them in OpenClaw so they 
can be spawned from the task board.
```

Your agent will guide you through:
1. Adding agent definitions to your OpenClaw config
2. Setting up the `dev-team.md` guardrails file
3. Configuring spawn permissions

---

## 👥 Setting Up the Dev Team

The task board works best with a team of specialized AI agents. Here's how to configure them:

### Step 1: Configure Agents in OpenClaw

Add these agents to your OpenClaw config (`~/.openclaw/openclaw.json`):

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "name": "YourAgentName",
        "subagents": {
          "allowAgents": ["architect", "security-auditor", "code-reviewer", "ux-manager"]
        }
      },
      {
        "id": "architect",
        "name": "Architect",
        "identity": { "name": "Architect", "emoji": "🏛️" },
        "tools": { "profile": "coding", "deny": ["browser", "message"] }
      },
      {
        "id": "security-auditor",
        "name": "Security Auditor",
        "identity": { "name": "Security Auditor", "emoji": "🔒" },
        "tools": { "profile": "coding", "deny": ["browser", "message"] }
      },
      {
        "id": "code-reviewer",
        "name": "Code Reviewer",
        "identity": { "name": "Code Reviewer", "emoji": "📝" },
        "tools": { "profile": "coding", "deny": ["browser", "message"] }
      },
      {
        "id": "ux-manager",
        "name": "UX Manager",
        "identity": { "name": "UX Manager", "emoji": "🎨" },
        "tools": { "profile": "coding", "deny": ["message"] }
      }
    ]
  }
}
```

### Step 2: Create Your Dev Team Guardrails

Copy the template to your OpenClaw workspace:

```bash
cp examples/dev-team-example.md ~/.openclaw/workspace/agents/dev-team.md
```

Edit `dev-team.md` to customize:
- **Filesystem boundaries** — Paths agents can access
- **Compliance context** — Your security requirements
- **System prompts** — Role-specific instructions

### Step 3: Update Your Agent's TOOLS.md

Add this section to your main agent's `TOOLS.md`:

```markdown
## Task Board Integration

**URL:** http://localhost:8080
**Container:** openclaw-taskboard

When spawning sub-agents from the task board:
1. Include the guardrails from `agents/dev-team.md`
2. Pass task context (title, description, recent comments)
3. Instruct agent to post updates as comments on the task card

### API Reference
- Create comment: `POST /api/tasks/{id}/comments`
- Move task: `POST /api/tasks/{id}/move`
- Create action item: `POST /api/tasks/{id}/action-items`
```

---

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

#### OpenClaw Integration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENCLAW_GATEWAY_URL` | OpenClaw gateway URL | For AI features |
| `OPENCLAW_TOKEN` | OpenClaw API token | For AI features |
| `TASKBOARD_API_KEY` | API key for protected endpoints | Recommended |

#### Project Configuration

These customize the agent guardrails and system prompts for your project:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_NAME` | Your project name | `My SaaS App` |
| `COMPANY_NAME` | Your company/team | `Acme Corp` |
| `COMPANY_CONTEXT` | Brief context for agents | `fintech startup building payment APIs` |
| `ALLOWED_PATHS` | Paths agents can access (comma-separated) | `/home/user/myproject, /workspace` |
| `COMPLIANCE_FRAMEWORKS` | Security/compliance context | `SOC2, HIPAA, PCI-DSS` |

#### Branding

| Variable | Description | Default |
|----------|-------------|---------|
| `MAIN_AGENT_NAME` | Your main agent's display name | `Assistant` |
| `MAIN_AGENT_EMOJI` | Emoji for main agent | `🤖` |
| `HUMAN_NAME` | Your display name | `User` |
| `BOARD_TITLE` | Page title | `Task Board` |

> **Note:** Without OpenClaw configured, the board works as a standard Kanban without AI agent automation.

### OpenClaw Integration

**📖 See [OPENCLAW_SETUP.md](OPENCLAW_SETUP.md) for the full integration guide.**

Quick overview:
1. **Configure agents** in OpenClaw (`architect`, `security-auditor`, `code-reviewer`, `ux-manager`)
2. **Set your token** in `.env`
3. **Add task board handler** to your agent's `TOOLS.md`

The task board will auto-spawn agent sessions when tasks move to "In Progress".

---

## 📋 Workflow

```
Backlog → Todo → In Progress → Review → Done
                      ↓
                   Blocked
```

1. **Backlog** — Tasks waiting to be triaged
2. **Todo** — Triaged, ready to be picked up
3. **In Progress** — Agent session auto-spawns, work begins
4. **Review** — Agent completed work, awaiting approval
5. **Done** — Approved and complete (auto-stops agent session)
6. **Blocked** — Waiting on external input

---

## 🧠 Session Isolation: One Agent, One Context

Each task card maintains its own **isolated AI session**. This is a game-changer for complex projects.

### How It Works

```
Task #1: "Review Auth System"          Task #2: "Design API Schema"
         ↓                                      ↓
┌─────────────────────┐              ┌─────────────────────┐
│ Architect Session A │              │ Architect Session B │
│                     │              │                     │
│ • Knows about auth  │              │ • Knows about API   │
│ • Has auth context  │              │ • Has schema context│
│ • Separate memory   │              │ • Separate memory   │
└─────────────────────┘              └─────────────────────┘
```

### Why This Matters

- **No context bleed** — Agent working on Task A won't confuse it with Task B
- **Persistent conversations** — Come back hours later, pick up where you left off
- **True multitasking** — Multiple agents can work on different tasks simultaneously
- **Clean handoffs** — Move task to Review, agent remembers everything when you ask follow-ups

---

## 👥 Multi-Agent Collaboration: @Mentions

Need a second opinion? Tag another agent into the conversation.

```
You: "@Security Auditor can you review the auth approach here?"
         ↓
Security Auditor receives context + responds in same thread
```

| Scenario | Primary Agent | Tag In |
|----------|--------------|--------|
| Feature design needs security review | Architect | @Security Auditor |
| Code review found UX issues | Code Reviewer | @UX Manager |
| Complex decision needs multiple perspectives | Any | @Architect @Security Auditor |

---

## 📋 Action Items

Action items track **what needs attention** with notification bubbles on cards:

| Type | Trigger | Purpose |
|------|---------|---------|
| **Question** 🟡 | Agent creates manually | Agent needs clarification |
| **Completion** 🟢 | Auto on → Review | Work ready for approval |
| **Blocker** 🔴 | Auto on → Blocked | Documents what's blocking |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Task Board UI                         │
│       WebSocket ←→ FastAPI Backend ←→ SQLite            │
└─────────────────────────┬───────────────────────────────┘
                          │ /tools/invoke
┌─────────────────────────┴───────────────────────────────┐
│                   OpenClaw Gateway                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Main    │  │ Architect│  │ Security │  ...         │
│  │  Agent   │  │          │  │ Auditor  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

### Tasks
- `GET /api/tasks` — List all tasks
- `POST /api/tasks` — Create task
- `PATCH /api/tasks/{id}` — Update task
- `DELETE /api/tasks/{id}` — Delete task
- `POST /api/tasks/{id}/move` — Move task to status

### Comments
- `GET /api/tasks/{id}/comments` — Get comments
- `POST /api/tasks/{id}/comments` — Add comment

### Action Items
- `GET /api/tasks/{id}/action-items` — Get action items
- `POST /api/tasks/{id}/action-items` — Create action item
- `POST /api/action-items/{id}/resolve` — Resolve item

### Command Bar
- `POST /api/jarvis/chat` — Send message to main agent
- `POST /api/jarvis/respond` — Push response to command bar

### WebSocket
- `WS /ws` — Real-time updates

---

## 🎨 Customization

### Adding New Agents

Agents are auto-detected from OpenClaw at startup. To configure manually, set in `.env`:

```env
# Format: agent_id:Display Name (comma-separated)
AGENTS=main:Jarvis,architect:Architect,my-agent:My Custom Agent

# Optional: disable auto-detection
AGENT_AUTO_DETECT=false
```

Agent icons and colors are assigned automatically. Built-in agents (`main`, `architect`, `security-auditor`, `code-reviewer`, `ux-manager`) have predefined icons and colors. Custom agents get auto-assigned colors.

See [OPENCLAW_SETUP.md](OPENCLAW_SETUP.md) for full agent configuration details.

```javascript
const AGENT_ICONS = {
    'Your Agent': '🚀',
    ...
};
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

## 🙏 Credits

Built for the [OpenClaw](https://github.com/openclaw/openclaw) community.

---

**Questions?** Open an issue or check the [OpenClaw Discord](https://discord.com/invite/clawd)
