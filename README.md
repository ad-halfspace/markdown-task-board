# Task Board

A local, dependency-free task board for a folder of Markdown files. Point it at
a directory of `.md` task files (with YAML frontmatter) and it renders them as
an interactive board, then writes your edits straight back to the files. Great
as a companion view for an [Obsidian](https://obsidian.md) vault.

No database, no build step, no accounts, and nothing leaves your machine: the
server is pure Python standard library (binds to `127.0.0.1` only) and the UI is
a single HTML file.

> **New here?** Follow the [Easy setup guide](SETUP.md), a 5-minute, no-experience-needed walkthrough.

## Features

- **List and Kanban views** of the same tasks, switchable.
- **Grouping** by due date, criticality, status, area, or priority.
- **Filters** for status, priority, area, and topic, plus a quick-find search.
- **Criticality** scoring that combines priority and due-date urgency.
- **Dependencies**: a task can depend on another and auto-blocks until it's done.
- **Detail drawer** that renders a task's notes and resolves `[[wiki-links]]` to
  other notes, the project hub, and source documents.
- **Create / edit / delete / complete** tasks in the UI; changes are saved to the
  underlying Markdown files immediately.
- **Optional macOS app**: a menu-bar icon plus an always-on-top floating window.
- **Light and dark themes**, remembered across sessions.

## Requirements

- **Python 3.7+** (uses only the standard library) for the web server.
- Any modern **web browser**.
- *Optional, for the macOS menu-bar app only:* macOS 11+, a framework build of
  Python, and the pyobjc + py2app packages (see [The macOS app](#the-macos-app)).

## Quick start

```bash
git clone https://github.com/ad-halfspace/markdown-task-board.git
cd markdown-task-board
python3 server.py
```

Then open <http://localhost:3737> in your browser. By default the board looks
for task files in `../../agent_brain/tasks/` relative to `server.py` (see
[Where it reads tasks from](#where-it-reads-tasks-from) to change that). If the
folder is empty the board simply shows no tasks, add one with **+ Add task** or
drop a `.md` file in (format below).

## How it works

```
your Markdown files  ──►  server.py (stdlib HTTP + JSON API)  ──►  index.html (board UI)
   agent_brain/tasks/*.md        localhost:3737                    one file: HTML+CSS+JS
        ▲                                                                  │
        └──────────────────  writes edits back to the files  ◄────────────┘
```

- `server.py` is a small local HTTP server. On each request it reads the task
  `.md` files fresh, parses their frontmatter, and returns JSON; on create/edit it
  rewrites the corresponding file (keeping the frontmatter and your notes).
- `index.html` is the whole front end, a single file with no framework. It calls
  the JSON API and renders the board client-side.
- There is **no database and no cache**: the Markdown files are the single source
  of truth, so edits made here appear in your editor (and Obsidian) and vice
  versa.

## How I use it

This is just how the author works with it day to day; use whatever fits you.

The combo that clicks is **Claude + the board + Obsidian**, each doing what it's
best at:

- **Creating tasks → an assistant.** Most tasks get created by chatting with a
  Claude Code assistant rather than by filling in fields. It's good at
  categorizing, inferring what a task relates to, and setting sensible due dates,
  far less friction than a form. (This is an assistant workflow, not part of the
  app itself.)
- **The board → overview + status.** The daily driver: see everything at a glance,
  tick things off, and move status. The thing a plain notes app doesn't give you
  is the satisfaction of actually checking something off.
- **Obsidian → details.** Jump in only when you want the full context behind a
  task.
- In practice almost nothing is typed into Obsidian by hand; tasks flow in from
  the assistant and just show up on the board.

## Task file format

Each task is one Markdown file. Only `type: task` and a `# Title` are really
required; everything else is optional.

```yaml
---
type: task
summary: "Short one-liner shown under the title"
status: open | in_progress | on_hold | blocked | done | dropped
priority: p0 | p1 | p2 | p3
due: 2026-06-15          # optional, real deadlines only
area: projects | adhoc | social | personal | development
project: my-project      # optional, links to a project hub (see below)
depends_on: other-task   # optional, auto-blocks this task until other-task is done
tags: [task, topic-a, topic-b]
---

# Task title

Free-form notes in Markdown. `[[wiki-links]]` to other notes resolve and become
clickable in the detail drawer.
```

A **project** is a folder under `projects/` containing a hub file named after the
folder (e.g. `projects/my-project/my-project.md`). Tasks reference it by slug via
the `project:` field, and the board links back to the hub.

### Where it reads tasks from

The paths are set by a few constants at the top of `server.py`:

```python
ROOT         = Path(__file__).resolve().parents[2]   # vault / project root
BRAIN        = ROOT / "agent_brain"
TASKS_DIR    = BRAIN / "tasks"                        # *.md task files live here
PROJECTS_DIR = BRAIN / "projects"                     # one folder per project hub
```

So out of the box it expects to live at `<root>/workspace/task-board/` with
tasks in `<root>/agent_brain/tasks/`. Either match that layout, or edit the
constants to point `TASKS_DIR` / `PROJECTS_DIR` at any folders you like.

## Use with Obsidian

This works as a companion view for an Obsidian vault:

1. Put this folder inside your vault, e.g. `<vault>/workspace/task-board/`, and
   keep your task `.md` files in `<vault>/agent_brain/tasks/` (or repoint the
   constants above).
2. On startup `server.py` detects the vault automatically: the root is treated
   as an Obsidian vault if it contains a `.obsidian` folder.
3. When detected, the **Open** action on a linked file opens Markdown notes
   straight in Obsidian via the `obsidian://open?vault=…&file=…` URI; other file
   types (PDF, PPTX, images, …) open in their native app.
4. `[[wiki-links]]` in a task's notes resolve the same way Obsidian resolves
   them (by path, with a vault-wide basename fallback), and render as clickable
   links in the detail drawer.

Because tasks are plain Markdown files, edits made in the board show up in
Obsidian and vice-versa, there is no separate database.

## Capturing tasks from your phone

The board runs locally on your computer (`localhost`), so it isn't reachable
from your phone directly. But since every task is just a Markdown file in a
folder, there are easy ways to capture on the go and have items show up on the
board when you're back:

- **Obsidian mobile (simplest):** if your tasks folder is in a synced Obsidian
  vault, add or edit a task `.md` from the Obsidian app on your phone. It syncs,
  and the board picks it up on the next refresh.
- **Inbox-note sweep (zero-friction capture):** keep one "inbox" note in an app
  that syncs to your phone (e.g. Apple Notes) and jot a line whenever a thought
  hits you. A small automation then reads that note, classifies each new line
  (task / event / note), and writes the task files for you, deduping against
  what already exists. Because tasks are plain files, any script can do this.

  The reference implementation is **`/scribbles`**, a custom Claude Code skill by
  [Amalie Dam](https://github.com/ad-halfspace): it sweeps an Apple Note named
  `Scribbles`, turns each new line into a task file (inferring sensible due dates
  and project links from context), files pure notes separately, and remembers
  what it already processed so it never duplicates. It isn't bundled in this repo
  (it depends on a notes integration and an assistant), so either **ask Amalie for
  a copy** (open an issue on this repo) or **build your own**: point an assistant
  or a small script at a note that syncs to your phone, and on each run
  (1) read the note, (2) diff against a saved snapshot to find new lines,
  (3) classify each as task / event / note, and (4) write a task `.md` for the
  actionable ones and update the snapshot.

This closes the "no access from my phone" gap: capture anywhere on mobile, and
the tasks are waiting on the board when you're back at your computer.

## The macOS app

`tasks_app.py` wraps the same web UI in a native menu-bar popover plus an
always-on-top floating window, so the board is one click away. It needs a
*framework* build of Python (the python.org installer, or `brew install
python`) with pyobjc:

```bash
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit py2app
python3 setup.py py2app -A      # -A = alias mode: fast, references files in place
open dist/Tasks.app
```

After building once you can just double-click **Task Board.command**. The app
starts the server for you if it isn't already running.

> Note: `tasks_app.py` has a `#!` line pointing at a specific framework Python.
> Adjust it to your own framework Python path if you run the script directly.

## API (server.py)

- `GET  /api/tasks` — all tasks (status, priority, due, area, project, depends_on…)
- `GET  /api/projects` — project hubs
- `GET  /api/task/<slug>/detail` — rendered notes + resolved links
- `GET  /api/doc?target=<wikilink>` — render any linked doc
- `POST /api/task/new` · `PUT /api/task/<slug>` · `DELETE /api/task/<slug>`
- `POST /api/task/<slug>/toggle` — done ⇄ open
- `POST /api/open` — open a linked file in its native app / Obsidian
- `POST /api/projects` — create a new project hub

## Criticality

`criticality = priorityWeight + dueWeight` → Critical (≥5) / Elevated (≥3) / Normal.
Priority: P1=3 P2=2 P3=1. Due: overdue/today/tomorrow=3, ≤3d=2, ≤7d=1, else 0.

## Fonts

The UI prefers **Britti Sans** if that font is installed on your system, and
otherwise falls back to your platform's default UI font. No font files are
bundled (Britti Sans is a licensed typeface). To use a different font, edit the
`font-family` on the `body` rule near the top of `index.html`, e.g. add a Google
Font `<link>` and set the family there.

## License

MIT, see [LICENSE](LICENSE).
