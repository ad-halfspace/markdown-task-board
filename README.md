# Task Board

A local, dependency-free task board for a folder of Markdown task files. It
reads and writes Markdown files with YAML frontmatter and renders them as an
interactive board: list and kanban views, grouping (due date / criticality /
status / area / priority), a detail drawer that resolves `[[wiki-links]]`, and
an optional macOS menu-bar + floating-window app. Works great on top of an
Obsidian vault.

No frameworks, no build step for the web UI: the server is pure Python stdlib
and the UI is a single HTML file.

## Layout

```
task-board/
├── server.py        # local HTTP server + JSON API over the task files
├── index.html       # the board UI (single file: HTML + CSS + JS)
├── tasks_app.py     # macOS menu-bar popover + floating window (pyobjc/WebKit)
├── setup.py         # py2app config to build the .app
└── "Task Board.command"  # double-click launcher
```

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

This works as a companion view for an [Obsidian](https://obsidian.md) vault:

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

## Task file format

Each task is a Markdown file with frontmatter:

```yaml
---
type: task
summary: "Short one-liner"
status: open | in_progress | on_hold | blocked | done | dropped
priority: p0 | p1 | p2 | p3
due: 2026-06-15        # optional
area: projects | adhoc | social | personal | development
project: my-project    # optional, links to a project hub
depends_on: other-task # optional, auto-blocks until that task is done
tags: [task, topic-a, topic-b]
---

# Task title

Notes in Markdown. `[[wiki-links]]` to other files resolve in the drawer.
```

## Run

Web only (any browser):
```
python3 server.py        # then open http://localhost:3737
```

Menu-bar / floating-window app (macOS, needs a framework Python with pyobjc):
```
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit py2app
python3 setup.py py2app -A
open dist/Tasks.app
```
or just double-click **Task Board.command**.

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

## License

MIT.
