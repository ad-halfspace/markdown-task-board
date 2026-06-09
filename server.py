import http.server
import json
import re
import subprocess
import urllib.parse
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
BRAIN = ROOT / "agent_brain"
TASKS_DIR = BRAIN / "tasks"
PROJECTS_DIR = BRAIN / "projects"
ARTIFACTS_DIR = ROOT / "artifacts"
WEB_DIR = Path(__file__).resolve().parent   # web assets (index.html) live with the code
PORT = 3737

# Obsidian vault = nearest ancestor with a .obsidian folder (here: the project root)
VAULT = ROOT if (ROOT / ".obsidian").exists() else None
OPEN_OK_EXT = {".md", ".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls",
               ".png", ".jpg", ".jpeg", ".gif", ".key", ".csv", ".txt", ".numbers", ".pages"}

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript",
    ".otf": "font/otf", ".ttf": "font/ttf", ".woff": "font/woff", ".woff2": "font/woff2",
}

# UI workflow status  <->  markdown status
MD_STATUS = {"todo": "open", "doing": "in_progress", "onhold": "on_hold", "blocked": "blocked", "done": "done"}


def norm_status(s):
    s = (s or "open").lower()
    if s in ("done", "completed"):
        return "done"
    if s in ("in_progress", "in-progress", "doing"):
        return "doing"
    if s in ("on_hold", "on-hold", "onhold", "hold"):
        return "onhold"
    if s == "blocked":
        return "blocked"
    return "todo"


def parse_frontmatter(content):
    m = re.match(r"^---\n([\s\S]*?)\n---", content)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        kv = re.match(r"^(\w+):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1]
            fm[key] = val
    return fm


def get_heading(content):
    m = re.search(r"^# (.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def body_after_fm(content):
    m = re.match(r"^---\n[\s\S]*?\n---\n?", content)
    return content[m.end():] if m else content


def strip_leading_heading(body):
    # drop a leading "# Title" line (the drawer already shows the title)
    return re.sub(r"^\s*#\s+.*\n+", "", body, count=1)


def parse_tags(fm):
    m = re.search(r"\[(.*)\]", fm.get("tags", ""))
    return [t.strip() for t in m.group(1).split(",") if t.strip()] if m else []


AREAS = ("projects", "adhoc", "social", "personal", "development")


def derive_area(fm, tags, has_real_project):
    explicit = (fm.get("area") or "").lower()
    if explicit in AREAS:
        return explicit
    if has_real_project:
        return "projects"
    hay = ((fm.get("category") or "") + " " + " ".join(tags)).lower()
    if any(k in hay for k in ["social", "party", "birthday", "brunch", "wedding", "run-club", "sparta", "figure-skating", "skating", "dhl"]):
        return "social"
    if any(k in hay for k in ["tools", "setup", "claude", "vscode", "companion", "spanish", "learning", "development", "upskilling"]):
        return "development"
    if any(k in hay for k in ["errand", "booking", "travel", "clothing", "gift", "hair", "tailor", "cleaner", "pilates"]):
        return "personal"
    return "adhoc"


def known_project_slugs():
    return {p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()}


def list_projects():
    out = []
    for sub in sorted(PROJECTS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        hub = sub / f"{sub.name}.md"
        title = sub.name
        if hub.exists():
            title = get_heading(hub.read_text(encoding="utf-8")) or sub.name
        out.append({"slug": sub.name, "title": title})
    return out


def project_title(slug):
    hub = PROJECTS_DIR / slug / f"{slug}.md"
    return (get_heading(hub.read_text(encoding="utf-8")) or slug) if hub.exists() else slug


def task_title(slug):
    f = TASKS_DIR / f"{slug}.md"
    if f.exists():
        c = f.read_text(encoding="utf-8")
        return get_heading(c) or parse_frontmatter(c).get("summary") or slug
    return slug


def update_field(content, key, value):
    pattern = rf"^({re.escape(key)}:\s*).*$"
    if re.search(pattern, content, re.MULTILINE):
        return re.sub(pattern, f"\\g<1>{value}", content, flags=re.MULTILINE)
    return re.sub(r"^---\n", f"---\n{key}: {value}\n", content, count=1)


def upsert_body_line(content, label, line):
    pat = rf"^\*\*{re.escape(label)}\*\*:.*$"
    if re.search(pat, content, re.MULTILINE):
        return re.sub(pat, lambda _: line, content, count=1, flags=re.MULTILINE)
    if re.search(r"^# .+$", content, re.MULTILINE):
        return re.sub(r"^# .+$", lambda m: m.group(0) + "\n\n" + line, content, count=1, flags=re.MULTILINE)
    return content.rstrip() + "\n\n" + line + "\n"


def remove_body_line(content, label):
    pat = rf"\n*^\*\*{re.escape(label)}\*\*:.*$\n?"
    return re.sub(pat, "\n", content, count=1, flags=re.MULTILINE)


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50].rstrip("-")


def fmt_tags(topics):
    clean = []
    for t in topics or []:
        s = re.sub(r"\s+", "-", (t or "").strip().lower()).lstrip("#")
        s = re.sub(r"[^a-z0-9\-]", "", s)
        if s and s not in clean:
            clean.append(s)
    return "[" + ", ".join(["task"] + clean) + "]"


def set_body(content, notes):
    """Replace the markdown body (keep frontmatter + the H1 title heading)."""
    fm_m = re.match(r"^---\n[\s\S]*?\n---\n?", content)
    fmblock = fm_m.group(0).rstrip("\n") if fm_m else ""
    head_m = re.search(r"^(# .+)$", content, re.MULTILINE)
    heading = head_m.group(1) if head_m else ""
    nb = (notes or "").strip()
    return fmblock + "\n\n" + (heading + "\n\n" if heading else "") + nb + "\n"


def parse_depends_on(content, fm):
    dep = fm.get("depends_on", "").strip()
    if dep in ("", "null", "~"):
        dep = ""
    if not dep:
        mb = re.search(r"\*\*Blocked on\*\*:\s*\[\[([^\]|]+)", content)
        dep = mb.group(1).strip() if mb else ""
    return dep or None


def task_dict(f):
    content = f.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)
    tags = parse_tags(fm)
    summary = fm.get("summary") or ""
    title = get_heading(content) or summary or f.stem
    due = fm.get("due", "null")
    if due in ("null", "", "~", None):
        due = None
    proj = fm.get("project", "")
    project = proj if proj in known_project_slugs() else None
    return {
        "slug": f.stem,
        "status": norm_status(fm.get("status")),
        "title": title,
        "summary": summary if summary != title else "",
        "priority": fm.get("priority", "p2").lower(),
        "due": due,
        "area": derive_area(fm, tags, project is not None),
        "project": project,
        "depends_on": parse_depends_on(content, fm),
        "owner": fm.get("owner") or None,
        "tags": [t for t in tags if t not in ("task", "todo")],   # topics for relating tasks
    }


# ── lightweight markdown rendering for the detail drawer ──
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_md(s):
    s = esc(s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)

    def wl(m):
        raw, _, label = m.group(1).partition("|")
        txt = label.strip() or raw.strip().split("/")[-1]
        tgt = raw.strip().replace('"', "&quot;")
        return f'<span class="wl" data-wl="{tgt}">{txt}</span>'
    s = re.sub(r"\[\[([^\]]+)\]\]", wl, s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    return s


def render_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    body = [c for c in cells if not all(re.match(r"^:?-{2,}:?$", (x or "-").strip()) for x in c)]
    if not body:
        return ""
    head, rest = body[0], body[1:]
    h = "<table class='dt'><thead><tr>" + "".join(f"<th>{inline_md(x)}</th>" for x in head) + "</tr></thead><tbody>"
    for r in rest:
        h += "<tr>" + "".join(f"<td>{inline_md(x)}</td>" for x in r) + "</tr>"
    return h + "</tbody></table>"


def md_to_html(md):
    lines = md.split("\n")
    out = []
    i = 0
    in_ul = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            close_ul(); i += 1; continue
        if line.lstrip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                tbl.append(lines[i]); i += 1
            close_ul(); out.append(render_table(tbl)); continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            close_ul()
            lvl = min(len(h.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{inline_md(h.group(2))}</h{lvl}>"); i += 1; continue
        b = re.match(r"^\s*[-*]\s+(.*)$", line)
        if b:
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline_md(b.group(1))}</li>"); i += 1; continue
        close_ul()
        out.append(f"<p>{inline_md(line)}</p>"); i += 1
    close_ul()
    return "\n".join(out)


def find_brain_file(raw):
    """Resolve a wiki-link target to an actual brain file. Handles sloppy ../ paths
    (Obsidian resolves by basename) and falls back to a vault-wide basename search.
    Supports any extension; defaults to .md when the target has none."""
    raw = raw.split("|")[0].split("#")[0].strip()
    if not raw:
        return None
    name = raw.rstrip("/").split("/")[-1]
    has_ext = "." in name
    cleaned = re.sub(r"^(\.\./|\./)+", "", raw)
    # 1) literal path after stripping any leading ./ ../ — try the brain dir first,
    #    then the repo root (so links to artifacts/, raw/, etc. resolve too).
    for base in (BRAIN, ROOT):
        if (base / cleaned).exists():
            return base / cleaned
        if not has_ext and (base / (cleaned + ".md")).exists():
            return base / (cleaned + ".md")
    # 2) basename search, preferring paths matching more of the original segments
    pattern = name if has_ext else name + ".md"
    segs = [s.lower() for s in re.split(r"/", raw) if s not in ("..", ".", "")]
    best, best_score = None, -1
    for p in BRAIN.rglob(pattern):
        score = sum(1 for s in segs if s in str(p).lower())
        if score > best_score:
            best, best_score = p, score
    return best


def find_open_file(target):
    """Like find_brain_file but also looks in artifacts/ and raw/ for attachments (slides, PDFs)."""
    f = find_brain_file(target)
    if f:
        return f
    name = target.split("|")[0].split("#")[0].strip().rstrip("/").split("/")[-1]
    if "." not in name:
        return None
    for base in (ARTIFACTS_DIR, ROOT / "raw"):
        if base.exists():
            for p in base.rglob(name):
                return p
    return None


def resolve_wikilink(raw_target):
    raw, _, label = raw_target.partition("|")
    raw, label = raw.strip(), label.strip()
    low = raw.lower()
    if "people/" in low:
        kind = "person"
    elif "projects/" in low:
        # Only the hub itself (projects/<slug>/<slug>) is a "project"; every other
        # file in a project folder is a supporting document.
        parts = [p for p in raw.split("/") if p not in ("..", ".", "")]
        stem = parts[-1][:-3] if parts[-1].endswith(".md") else parts[-1]
        kind = "project" if len(parts) >= 2 and stem == parts[-2] else "doc"
    elif "artifacts/" in low or "meetings/" in low:
        kind = "source"
    elif "/" not in raw:
        kind = "task"
    else:
        kind = "other"
    f = find_brain_file(raw)
    exists = f is not None
    summary, title = None, label
    if exists:
        c = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(c)
        summary = fm.get("summary") or get_heading(c)
        if not title:
            title = get_heading(c) or fm.get("summary") or raw.split("/")[-1]
    if not title:
        title = raw.split("/")[-1]
    resolved = str(f.resolve()) if f else None
    return {"kind": kind, "target": raw, "title": title, "summary": summary, "exists": exists, "resolved": resolved}


def doc_payload(f):
    content = f.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)
    body = strip_leading_heading(body_after_fm(content))
    seen, links = set(), []
    for mt in re.finditer(r"\[\[([^\]]+)\]\]", body):
        r = resolve_wikilink(mt.group(1))
        key = r["resolved"] or r["target"]   # same file via different paths → one entry
        if key in seen:
            continue
        seen.add(key); links.append(r)
    return {
        "found": True,
        "title": get_heading(content) or fm.get("summary") or f.stem,
        "summary": fm.get("summary"),
        "kind": fm.get("type", "doc"),
        "path": str(f.relative_to(ROOT)),
        "body_html": md_to_html(body),
        "links": links,
    }


def task_detail(f):
    content = f.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)
    d = task_dict(f)
    d["source_field"] = fm.get("source")
    d["created"] = fm.get("created")
    d["updated"] = fm.get("updated")
    d["category"] = fm.get("category")
    body = strip_leading_heading(body_after_fm(content))
    d["body_html"] = md_to_html(body)
    d["body_raw"] = body.strip()      # editable notes (heading stripped)
    seen, links = set(), []

    def add(r):
        key = r["resolved"] or r["target"]   # same file via different paths → one entry
        if key in seen:
            return
        seen.add(key); links.append(r)

    # Broader brain link from frontmatter: the project hub this task belongs to,
    # surfaced even if the task body doesn't explicitly wiki-link it.
    if d.get("project"):
        add(resolve_wikilink(f"../projects/{d['project']}/{d['project']}"))

    for mt in re.finditer(r"\[\[([^\]]+)\]\]", body):
        add(resolve_wikilink(mt.group(1)))
    d["links"] = links
    return d


def apply_links(content, data):
    forced = None
    if "project" in data:
        p = data["project"]
        if p:
            content = update_field(content, "project", p)
            content = upsert_body_line(content, "Project", f"**Project**: [[../projects/{p}/{p}|{project_title(p)}]]")
        else:
            content = remove_body_line(content, "Project")
    if "depends_on" in data:
        d = data["depends_on"]
        if d:
            content = update_field(content, "depends_on", d)
            content = upsert_body_line(content, "Blocked on", f"**Blocked on**: [[{d}]] — {task_title(d)}")
            depf = TASKS_DIR / f"{d}.md"
            if depf.exists() and norm_status(parse_frontmatter(depf.read_text(encoding='utf-8')).get("status")) != "done":
                forced = "blocked"
        else:
            content = update_field(content, "depends_on", "null")
            content = remove_body_line(content, "Blocked on")
    return content, forced


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(fmt % args)

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/tasks":
            self.send_json(200, [task_dict(f) for f in sorted(TASKS_DIR.glob("*.md"))])
            return
        if path == "/api/projects":
            self.send_json(200, list_projects())
            return
        if path == "/api/doc":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            target = (qs.get("target") or [""])[0]
            f = find_brain_file(target)
            allowed = (BRAIN, ARTIFACTS_DIR, ROOT / "raw")
            if not f or not any(str(f.resolve()).startswith(str(b.resolve())) for b in allowed):
                self.send_json(200, {"found": False, "target": target}); return
            self.send_json(200, doc_payload(f))
            return
        m = re.match(r"^/api/task/([^/]+)/detail$", path)
        if m:
            slug = urllib.parse.unquote(m.group(1))
            f = TASKS_DIR / f"{slug}.md"
            if not f.exists():
                self.send_json(404, {"error": "not found"}); return
            self.send_json(200, task_detail(f))
            return
        if path == "/":
            body = (WEB_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return
        file_path = (WEB_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(WEB_DIR)):
            self.send_response(403); self.end_headers(); return
        if file_path.is_file():
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(file_path.suffix, "application/octet-stream"))
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404); self.end_headers()

    def do_DELETE(self):
        m = re.match(r"^/api/task/([^/]+)$", urllib.parse.urlparse(self.path).path)
        if m:
            slug = urllib.parse.unquote(m.group(1))
            f = TASKS_DIR / f"{slug}.md"
            if not f.exists():
                self.send_json(404, {"error": "not found"}); return
            f.unlink()
            print(f"  Deleted: {slug}")
            self.send_json(200, {"slug": slug, "deleted": True})
            return
        self.send_response(404); self.end_headers()

    def do_PUT(self):
        m = re.match(r"^/api/task/([^/]+)$", urllib.parse.urlparse(self.path).path)
        if m:
            slug = urllib.parse.unquote(m.group(1))
            f = TASKS_DIR / f"{slug}.md"
            if not f.exists():
                self.send_json(404, {"error": "not found"}); return
            data = self.read_json()
            content = f.read_text(encoding="utf-8")
            if "title" in data:
                t = data["title"].strip()
                content = update_field(content, "summary", f'"{t}"')
                if re.search(r"^# .+$", content, re.MULTILINE):
                    content = re.sub(r"^# .+$", lambda _: f"# {t}", content, count=1, flags=re.MULTILINE)
            if "priority" in data:
                content = update_field(content, "priority", data["priority"].lower())
            if "due" in data:
                content = update_field(content, "due", data["due"] if data["due"] else "null")
            content, forced = apply_links(content, data)
            if "area" in data:
                content = update_field(content, "area", data["area"].lower())
            if "tags" in data:
                content = update_field(content, "tags", fmt_tags(data["tags"]))
            if "status" in data:
                content = update_field(content, "status", MD_STATUS.get(data["status"], "open"))
            if forced:
                content = update_field(content, "status", MD_STATUS[forced])
            if "body" in data:
                content = set_body(content, data["body"])
            content = update_field(content, "updated", date.today().isoformat())
            f.write_text(content, encoding="utf-8")
            print(f"  Updated: {slug} {list(data.keys())}")
            self.send_json(200, task_dict(f))
            return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        m = re.match(r"^/api/task/([^/]+)/toggle$", path)
        if m:
            slug = urllib.parse.unquote(m.group(1))
            f = TASKS_DIR / f"{slug}.md"
            if not f.exists():
                self.send_json(404, {"error": "not found"}); return
            content = f.read_text(encoding="utf-8")
            cur = norm_status(parse_frontmatter(content).get("status"))
            nxt = "todo" if cur == "done" else "done"
            f.write_text(update_field(content, "status", MD_STATUS[nxt]), encoding="utf-8")
            print(f"  {slug}: {cur} -> {nxt}")
            self.send_json(200, {"slug": slug, "status": nxt})
            return

        if path == "/api/open":
            data = self.read_json()
            target = data.get("target", "")
            f = find_open_file(target)
            if not f or f.suffix.lower() not in OPEN_OK_EXT:
                self.send_json(404, {"opened": False, "target": target}); return
            fr = f.resolve()
            if not str(fr).startswith(str(ROOT.resolve())):
                self.send_json(403, {"opened": False}); return
            try:
                if fr.suffix.lower() == ".md" and VAULT:
                    rel = fr.relative_to(VAULT).with_suffix("")
                    uri = ("obsidian://open?vault=" + urllib.parse.quote(VAULT.name)
                           + "&file=" + urllib.parse.quote(str(rel)))
                    subprocess.Popen(["open", uri])   # fire-and-forget so the handler never blocks
                    app = "Obsidian"
                else:
                    subprocess.Popen(["open", str(fr)])
                    app = "default app"
                print(f"  Opened {fr.name} in {app}")
                self.send_json(200, {"opened": True, "app": app, "file": fr.name})
            except Exception as e:
                self.send_json(500, {"opened": False, "error": str(e)})
            return

        if path == "/api/projects":
            data = self.read_json()
            name = (data.get("name") or "").strip()
            if not name:
                self.send_json(400, {"error": "name required"}); return
            slug = slugify(name)
            pdir = PROJECTS_DIR / slug
            if pdir.exists():
                self.send_json(200, {"slug": slug, "title": project_title(slug), "existed": True}); return
            pdir.mkdir(parents=True)
            today_str = date.today().isoformat()
            (pdir / f"{slug}.md").write_text(
                f'---\ntype: project\nsummary: "{name}"\nstate: active\nstatus: active\n'
                f'owner: Me\ncreated: {today_str}\nupdated: {today_str}\ntags: [project]\n---\n\n# {name}\n',
                encoding="utf-8"
            )
            print(f"  Created project: {slug}")
            self.send_json(201, {"slug": slug, "title": name})
            return

        if path == "/api/task/new":
            data = self.read_json()
            title = data.get("title", "").strip()
            if not title:
                self.send_json(400, {"error": "title required"}); return
            priority = data.get("priority", "p2").lower()
            due = data.get("due", "") or None
            area = data.get("area", "adhoc").lower()
            project = data.get("project") or None
            depends_on = data.get("depends_on") or None
            status = data.get("status", "todo")
            tags_line = fmt_tags(data.get("tags"))
            today_str = date.today().isoformat()
            slug = slugify(title)
            f = TASKS_DIR / f"{slug}.md"
            if f.exists():
                i = 2
                while (TASKS_DIR / f"{slug}-{i}.md").exists():
                    i += 1
                slug = f"{slug}-{i}"
                f = TASKS_DIR / f"{slug}.md"
            content = (
                f'---\ntype: task\nsummary: "{title}"\nstatus: {MD_STATUS.get(status, "open")}\n'
                f'priority: {priority}\nowner: Me\narea: {area}\nproject: {project or "none"}\n'
                f'due: {due or "null"}\ndepends_on: {depends_on or "null"}\n'
                f'created: {today_str}\nupdated: {today_str}\ntags: {tags_line}\n---\n\n# {title}\n'
            )
            content, forced = apply_links(content, {"project": project, "depends_on": depends_on})
            if forced:
                content = update_field(content, "status", MD_STATUS[forced])
            f.write_text(content, encoding="utf-8")
            print(f"  Created: {slug}")
            self.send_json(201, task_dict(f))
            return

        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"Task board: http://localhost:{PORT}")
    server.serve_forever()
