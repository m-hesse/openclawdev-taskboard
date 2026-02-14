# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-02-13

### Added
- **Multi-project support**: Create, switch between, and manage multiple projects. Tasks belong to a project, with a "Default" project for backwards compatibility.
- **Project switcher**: Dropdown in header to filter tasks by project. "All Projects" view shows colored project badges on cards.
- **Project manager modal**: Add/remove projects with custom name, color, and description.
- **"Todo" status column**: New column between Backlog and In Progress (6 columns total).
- **Advanced filter bar**: Combine Priority, Agent, and keyword search filters (client-side AND logic).
- **Markdown export**: "Export MD" button in task modal exports task details, action items, and comments as downloadable `.md` file.
- **Agent session hardening**: Guard against double-spawn, session liveness check on card open, auto-stop agent when task moves to Done.
- **Configurable agent detection**: `AGENTS` env var for manual agent configuration, `AGENT_AUTO_DETECT` toggle. Priority: ENV > OpenClaw auto-detect > fallback defaults.
- **Responsive design**: CSS media queries for tablet (768px) and mobile (480px) breakpoints.
- **Status validation**: Backend rejects invalid statuses/priorities with HTTP 422.

### Changed
- **Backend architecture**: Refactored monolithic `app.py` (2600 lines) into `app/` package with modular structure (`config.py`, `database.py`, `models.py`, `websocket.py`, `openclaw.py`, `routes/`).
- **Dockerfile**: Now copies `app/` directory, runs `uvicorn app.main:app`.
- **Task form**: Now includes Project dropdown for assigning tasks to projects.

### Fixed
- **Status enforcement**: Backend now strictly validates statuses against UI-represented values.

## [1.3.0] - 2026-02-03

### Added
- **Chat message actions**: Reply, copy, and delete buttons on all chat messages
  - Reply (↩) — Shows preview above input, supports multi-reply (reply to multiple messages at once)
  - Copy (📋) — Copies message content with fallback for non-HTTPS contexts
  - Delete (🗑) — Removes message with confirmation (clears context or secrets)
- **DELETE endpoint for comments**: `DELETE /api/tasks/{id}/comments/{comment_id}` with WebSocket broadcast
- **Multi-reply support**: Click reply on multiple messages, each shows as stacked preview with "Clear all" button

### Changed
- **Command bar chat size**: Increased from 600×400px to 720×500px for better readability
- **Event delegation**: All chat button handlers now use event delegation (fixes special character issues in message content)

### Fixed
- **Reply button on assistant messages**: Fixed selector mismatch (`.command-chat-input-area` vs `.jarvis-chat-input-area`)
- **@Mention spawn logic**: Only explicitly @mentioned agents are spawned now — assigned agent no longer auto-spawns when other agents are tagged
- **Inline onclick handlers**: Replaced with data attributes + event delegation to handle messages with quotes, newlines, and special characters

## [1.2.0] - 2026-02-02

### Added
- **Image attachments for command bar chat**: Images now saved to `/data/attachments/` and passed as readable file paths to agents
- **Sub-agent guardrails documentation**: Updated `examples/dev-team-example.md` with comprehensive guardrails including:
  - Identity rules (main agent clones vs domain-specific agents)
  - Filesystem boundaries
  - Git safeword requirements
  - Browser access matrix (UX Manager only)
  - Compliance context templates

### Changed
- **Default column sort**: Changed from "Priority" to "Latest" (most recent first)
- **Theater mode spacing**: Tightened padding throughout for more conversation space
  - Chat header: 0.75rem → 0.5rem
  - Chat messages margin: 0.75rem → 0.25rem
  - Chat input area: 0.75rem/1rem → 0.25rem

### Fixed
- **Double image paste bug**: Removed duplicate `onpaste` handler that was causing images to paste twice
- **Card bottom border radius**: Added `border-radius: 0 0 16px 16px` to chat-input-area so modal corners are visible
- **UX Manager browser privilege**: Clarified in dev-team template that UX Manager is the ONLY agent with browser access; others must request their help

## [1.1.0] - 2026-01-31

### Added
- **Identity emoji support**: Command bar icon now uses `MAIN_AGENT_EMOJI` from environment variable (defaults to 🛡️)
- **Multi-line input**: Chat input is now a textarea supporting Shift+Enter for new lines
- **Graceful WebSocket reconnect**: Shows glowing indicator during reconnection instead of error messages
- **Retry logic**: API calls retry up to 3 times with exponential backoff for transient failures

### Changed
- **Scrollbar styling**: Thin, styled scrollbar (6px) that doesn't overlap borders
- **Textarea auto-resize**: Input grows with content up to 150px max height
- **Textarea reset**: Input resets to single line after sending message
- **Thinking indicator**: Moved from input area to header as glowing shield icon
- **Placeholder text**: Shortened to "Ctrl+V to paste images · Shift+Enter for new line"

### Fixed
- **Button alignment**: Attach, input, and send buttons now properly aligned at 44px height
- **OCD-compliant symmetry**: All input row elements use consistent sizing and box-sizing

## [1.0.0] - 2026-01-28

### Added
- Initial release
- Kanban board with Backlog, In Progress, Review, Done, Blocked columns
- Agent assignment and management
- Real-time WebSocket updates
- Agent chat integration via OpenClaw
- Task comments and action items
- Priority levels (Critical, High, Medium, Low)
- Agent work indicators
