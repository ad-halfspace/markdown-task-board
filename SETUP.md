# Easy setup guide

A step-by-step walkthrough to get the task board running, no prior command-line
experience needed. It takes about 10 minutes.

We recommend running it on top of an **[Obsidian](https://obsidian.md) vault**,
a free app that turns a folder of Markdown files into a personal "second brain".
That way your tasks live right next to your notes as plain files, sync to your
phone, and the board can open any linked note straight in Obsidian. This guide
sets that up; if you already use Obsidian, even better.

Commands are written for macOS / Linux; Windows notes are called out where they
differ.

---

## Step 1 — Set up an Obsidian vault (your second brain)

1. Download Obsidian (free) from <https://obsidian.md> and install it.
2. Open it and choose **Create new vault**. A vault is just a folder on your
   computer that Obsidian manages. Give it a name (e.g. `Brain`) and pick where
   to save it. **Note the folder's location**, you'll need it in Step 3.
3. That's it. Everything in the vault is plain Markdown, so the task board can
   read and write the same files.

> Already have a vault, or want to use a plain folder instead? You can. Just use
> that folder's path wherever this guide says "your vault".

## Step 2 — Make sure you have Python

The board runs on Python 3 (version 3.7 or newer), already present on most Macs
and Linux machines. Open a terminal and check:

```bash
python3 --version
```

- If you see something like `Python 3.11.x`, you're set.
- If you get "command not found", install Python from
  <https://www.python.org/downloads/>, then re-open the terminal and check again.

> **Windows:** install Python from the link above and tick *"Add Python to PATH"*
> during install. Use `python` instead of `python3` in the commands below.

You don't need to install anything else for the web version, no packages, no
Node, nothing.

## Step 3 — Put the task board inside your vault

1. Get the code: go to
   <https://github.com/ad-halfspace/markdown-task-board>, click the green
   **Code** button → **Download ZIP**, and unzip it. (Or `git clone` it if you
   use git.)
2. Inside your vault, create a folder called `workspace`, and move the
   `markdown-task-board` folder into it. You should end up with:

   ```
   <your vault>/
   ├── workspace/
   │   └── markdown-task-board/   ← the code you just downloaded
   │       ├── server.py
   │       ├── index.html
   │       └── …
   └── agent_brain/
       └── tasks/                 ← create this folder; your task files live here
   ```

   So: create `workspace/markdown-task-board/` (the code) and an empty
   `agent_brain/tasks/` folder (your tasks). This layout lets the board find your
   vault automatically, no editing required.

> **Prefer different folder names?** Open `server.py` and edit the `TASKS_DIR` /
> `PROJECTS_DIR` lines near the top to point anywhere you like (see the README's
> *Where it reads tasks from*).

## Step 4 — Start the board

In the terminal, go into the code folder and run the server:

```bash
cd "<your vault>/workspace/markdown-task-board"
python3 server.py
```

(Replace `<your vault>` with the real path, e.g.
`cd "/Users/you/Brain/workspace/markdown-task-board"`.)

You should see:

```
Task board: http://localhost:3737
```

Leave this terminal window open, it's the running app. To stop it later, click
the terminal and press **Ctrl + C**.

## Step 5 — Open it

Open your browser and go to <http://localhost:3737>.

That's the board. Click **+ Add task** to create your first task, set its
priority, due date, and topics. It's saved as a Markdown file in your vault's
`agent_brain/tasks/` folder, so it shows up in Obsidian too, instantly.

---

## You now have an Obsidian-connected board

Because the board lives in your vault:

- **Edits sync both ways.** Add or tick off a task in the board and it changes the
  file; edit the file in Obsidian and the board reflects it on refresh.
- **Notes open in Obsidian.** The **Open** button on a linked note launches it
  directly in Obsidian; `[[wiki-links]]` in a task's notes are clickable in the
  detail drawer.
- **Capture from your phone.** Install Obsidian on your phone, turn on sync
  (Obsidian Sync or iCloud/Dropbox), and you can add a task from anywhere, it's
  on the board when you're back at your computer. For frictionless capture see
  the README's *Capturing tasks from your phone* (including the `/scribbles`
  inbox-note pattern).

## Add a task by hand (optional)

You can also create a task by adding a Markdown file to `agent_brain/tasks/`:

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

## Get the macOS menu-bar app (optional, Mac only)

For a one-click menu-bar icon and a floating window instead of a browser tab:

```bash
pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit py2app
python3 setup.py py2app -A
open dist/Tasks.app
```

Afterwards just double-click **Task Board.command** to launch it. (Needs a
framework build of Python, the python.org installer or Homebrew's `python` both
work.)

---

## Troubleshooting

**"command not found: python3"**
Python isn't installed or isn't on your PATH. Re-do Step 2.

**"Address already in use" / port 3737 is busy**
The board is probably already running in another terminal. Use that one, or stop
it (Ctrl + C) and start again. To change the port, edit `PORT = 3737` near the
top of `server.py`.

**The board is empty**
Normal if `agent_brain/tasks/` has no `.md` files yet. Add one with **+ Add
task**, or confirm the code is in `<vault>/workspace/markdown-task-board/` so the
vault is detected.

**Linked notes don't open in Obsidian**
Make sure the code folder sits two levels under the vault root
(`<vault>/workspace/markdown-task-board/`) so the board detects the vault's
`.obsidian` folder.

**It stopped working after I closed the terminal**
The server only runs while that terminal window is open. Re-run
`python3 server.py`, or build the macOS app, which keeps running on its own.
