# Easy setup guide

A step-by-step walkthrough to get the task board running, no prior command-line
experience needed. It takes about 5 minutes. Commands are written for macOS /
Linux; Windows notes are called out where they differ.

---

## Step 1 — Make sure you have Python

The board runs on Python 3 (version 3.7 or newer). Most Macs and Linux machines
already have it. Open a terminal and check:

```bash
python3 --version
```

- If you see something like `Python 3.11.x`, you're set, go to Step 2.
- If you get "command not found", install Python from
  <https://www.python.org/downloads/> (the standard installer), then re-open the
  terminal and check again.

> **Windows:** install Python from the link above and tick *"Add Python to PATH"*
> during install. Use `python` instead of `python3` in the commands below.

You do **not** need to install anything else for the web version, no packages,
no Node, nothing.

## Step 2 — Get the code

**Option A — download (easiest):**
1. Go to <https://github.com/ad-halfspace/markdown-task-board>.
2. Click the green **Code** button → **Download ZIP**.
3. Unzip it. You'll get a folder called `markdown-task-board`.

**Option B — git clone (if you use git):**
```bash
git clone https://github.com/ad-halfspace/markdown-task-board.git
```

## Step 3 — Tell it where your task files are (optional but recommended)

The board reads `.md` task files from a folder. By default it looks for them at
`agent_brain/tasks/` two levels up from the code. The simplest setups:

- **Just trying it out?** Skip this step. The board opens with an empty list and
  you can add tasks from the UI, they'll be saved next to the app.
- **Have an Obsidian vault or a notes folder?** Open `server.py` in any text
  editor and look at the top:

  ```python
  ROOT         = Path(__file__).resolve().parents[2]
  TASKS_DIR    = BRAIN / "tasks"        # change this to your tasks folder
  PROJECTS_DIR = BRAIN / "projects"
  ```

  Set `TASKS_DIR` to the folder where you want your task files, for example:

  ```python
  TASKS_DIR = Path("/Users/you/Documents/MyVault/tasks")
  ```

  Save the file. (More detail in the README's *Where it reads tasks from*.)

## Step 4 — Start the board

In the terminal, go into the folder and run the server:

```bash
cd markdown-task-board
python3 server.py
```

You should see:

```
Task board: http://localhost:3737
```

Leave this terminal window open, it's the running app. (To stop it later, click
the terminal and press **Ctrl + C**.)

## Step 5 — Open it

Open your web browser and go to:

<http://localhost:3737>

That's the board. Click **+ Add task** to create your first task, set its
priority, due date, and topics, and it's saved as a Markdown file automatically.

---

## Add a task by hand (optional)

You can also create a task by dropping a Markdown file into your tasks folder:

```markdown
---
type: task
summary: "Buy groceries for the week"
status: open
priority: p2
due: 2026-06-20
area: personal
tags: [task, errands]
---

# Buy groceries

Milk, eggs, coffee. Notes go here in Markdown.
```

Refresh the board and it appears. (Full field list is in the README.)

---

## Use it with Obsidian (optional)

If your task files live in an Obsidian vault, put the `markdown-task-board`
folder *inside* the vault and point `TASKS_DIR` at your vault's task folder
(Step 3). When the board detects the vault, the **Open** button on a linked note
opens it directly in Obsidian. See the README's *Use with Obsidian* section.

---

## Get the macOS menu-bar app (optional, Mac only)

If you'd like a one-click menu-bar icon and a floating window instead of a
browser tab:

```bash
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit py2app
python3 setup.py py2app -A
open dist/Tasks.app
```

After that you can just double-click **Task Board.command** to launch it. (This
needs a framework build of Python, the python.org installer or Homebrew's
`python` both work.)

---

## Troubleshooting

**"command not found: python3"**
Python isn't installed or isn't on your PATH. Re-do Step 1.

**"Address already in use" / port 3737 is busy**
The board is probably already running in another terminal. Either use that one,
or stop it (Ctrl + C) and start again. To run on a different port, change
`PORT = 3737` near the top of `server.py`.

**The board is empty**
That's normal if your tasks folder is empty or `TASKS_DIR` points somewhere with
no `.md` files. Add a task with **+ Add task**, or check the path in Step 3.

**It stopped working after I closed the terminal**
The server only runs while that terminal window is open. Re-run
`python3 server.py` to start it again (or build the macOS app, which keeps
running on its own).
