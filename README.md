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

By default `server.py` looks for tasks in `<vault>/agent_brain/tasks/` and
projects in `<vault>/agent_brain/projects/`, resolving the vault root three
levels up from the script (`Path(__file__).resolve().parents[2]`). Drop this
folder at `<vault>/workspace/task-board/`, or edit the path constants at the top
of `server.py` to point anywhere you like.

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
