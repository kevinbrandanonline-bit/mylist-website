from pathlib import Path

content = r'''import json
import os
import sqlite3
import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template_string, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

BASE_DIR = Path(__file__).resolve().parent
LINKBOX_DB_PATH = os.environ.get("LINKBOX_DB_PATH", str(BASE_DIR / "database.db"))
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
_LINKBOX_SHARED_CONN = None


def get_linkbox_connection(db_path=None):
    resolved_path = db_path or LINKBOX_DB_PATH
    if resolved_path == ":memory:":
        global _LINKBOX_SHARED_CONN
        if _LINKBOX_SHARED_CONN is None:
            _LINKBOX_SHARED_CONN = sqlite3.connect(":memory:", check_same_thread=False)
            _LINKBOX_SHARED_CONN.row_factory = sqlite3.Row
        return _LINKBOX_SHARED_CONN

    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    return conn


def close_linkbox_connection(conn, db_path=None):
    if (db_path or LINKBOX_DB_PATH) == ":memory:":
        return
    conn.close()


def init_db(db_path=None):
    conn = get_linkbox_connection(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS linkbox_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            notes TEXT,
            links TEXT NOT NULL,
            image_url TEXT,
            theme_color TEXT DEFAULT '#6d5dfc',
            accent_color TEXT DEFAULT '#4f46e5',
            views INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    close_linkbox_connection(conn, db_path)


init_db()


def parse_linkbox_links(form_data):
    titles = form_data.getlist("link_title") if hasattr(form_data, "getlist") else []
    urls = form_data.getlist("link_url") if hasattr(form_data, "getlist") else []
    links = []
    for title, url in zip(titles, urls):
        title = (title or "").strip()
        url = (url or "").strip()
        if title and url:
            links.append({"title": title, "url": url})
    return links


def save_uploaded_image(uploaded_file):
    if not uploaded_file or not getattr(uploaded_file, "filename", None):
        return None
    filename = secure_filename(uploaded_file.filename)
    ext = Path(filename).suffix.lower() or ".png"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    target_path = UPLOAD_FOLDER / safe_name
    uploaded_file.save(target_path)
    return f"/static/uploads/{safe_name}"


def serialize_linkbox_page(row):
    page = dict(row)
    try:
        page["links"] = json.loads(page.get("links") or "[]")
    except (TypeError, json.JSONDecodeError):
        page["links"] = []
    return page


def get_linkbox_pages(db_path=None):
    conn = get_linkbox_connection(db_path)
    rows = conn.execute("SELECT * FROM linkbox_pages ORDER BY created_at DESC").fetchall()
    close_linkbox_connection(conn, db_path)
    return [serialize_linkbox_page(row) for row in rows]


def get_linkbox_page(slug, db_path=None):
    conn = get_linkbox_connection(db_path)
    row = conn.execute("SELECT * FROM linkbox_pages WHERE slug = ?", (slug,)).fetchone()
    close_linkbox_connection(conn, db_path)
    return serialize_linkbox_page(row) if row else None


def create_unique_slug(db_path=None):
    slug = uuid.uuid4().hex[:10]
    conn = get_linkbox_connection(db_path)
    while conn.execute("SELECT 1 FROM linkbox_pages WHERE slug = ?", (slug,)).fetchone():
        slug = uuid.uuid4().hex[:10]
    close_linkbox_connection(conn, db_path)
    return slug


DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LinkBox Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #060816;
      --panel: rgba(12, 18, 36, 0.82);
      --text: #f4f7ff;
      --muted: #90a2c7;
      --accent: #6d5dfc;
      --accent-2: #4f46e5;
      --border: rgba(255,255,255,0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, system-ui, sans-serif;
      background: radial-gradient(circle at top left, #16214a 0%, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
    }
    .app-shell { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
    .sidebar { padding: 24px 18px; border-right: 1px solid var(--border); background: rgba(4, 8, 20, 0.42); backdrop-filter: blur(24px); }
    .brand { display: flex; gap: 12px; align-items: center; margin-bottom: 28px; }
    .brand-mark { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; background: linear-gradient(135deg, var(--accent), var(--accent-2)); font-size: 1.1rem; }
    .nav-links { display: flex; flex-direction: column; gap: 8px; }
    .nav-links a { text-decoration: none; color: var(--text); padding: 10px 12px; border-radius: 12px; display: flex; gap: 10px; align-items: center; }
    .nav-links a.active, .nav-links a:hover { background: rgba(109, 93, 252, 0.16); }
    .sidebar-card, .panel, .hero-card { background: var(--panel); border: 1px solid var(--border); border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.24); backdrop-filter: blur(20px); }
    .sidebar-card { padding: 16px; margin-top: 24px; }
    .main-panel { padding: 24px; }
    .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .eyebrow { text-transform: uppercase; letter-spacing: 0.25em; color: #f4b95d; font-size: 0.75rem; margin: 0 0 6px; }
    .hero-card { padding: 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 18px; }
    .grid-two { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 18px; }
    .panel { padding: 18px; }
    .panel label { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; color: var(--muted); }
    .panel input, .panel textarea { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; background: rgba(255,255,255,0.04); color: var(--text); }
    .panel textarea { min-height: 90px; resize: vertical; }
    .pill { padding: 6px 10px; border-radius: 999px; background: rgba(109, 93, 252, 0.16); color: #c8beff; font-size: 0.8rem; }
    .ghost-btn, .primary-btn { border: none; cursor: pointer; padding: 10px 14px; border-radius: 999px; color: white; background: linear-gradient(135deg, var(--accent), var(--accent-2)); }
    .ghost-btn { background: rgba(255,255,255,0.06); color: var(--text); }
    .ghost-btn.danger { color: #ffb0b0; }
    .action-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    .color-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .page-list { display: flex; flex-direction: column; gap: 10px; margin-top: 10px; }
    .page-card { padding: 14px; border-radius: 16px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); }
    .page-card h5 { margin: 0 0 4px; }
    .page-card p { margin: 0; color: var(--muted); }
    .empty-state { color: var(--muted); }
    @media (max-width: 920px) { .app-shell { grid-template-columns: 1fr; } .sidebar { border-right: 0; border-bottom: 1px solid var(--border); } .grid-two { grid-template-columns: 1fr; } }
    @media (max-width: 560px) { .main-panel { padding: 14px; } .topbar { flex-direction: column; align-items: flex-start; gap: 8px; } .hero-card { flex-direction: column; align-items: flex-start; } .color-row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">⬢</div>
        <div>
          <h1>LinkBox</h1>
          <p>Share your story</p>
        </div>
      </div>
      <nav class="nav-links">
        <a class="active" href="/linkbox"><span>◉</span> Dashboard</a>
        <a href="/page/demo"><span>⬢</span> Preview</a>
      </nav>
      <div class="sidebar-card">
        <h3>Share instantly</h3>
        <p>Create a modern public page and send one link to everyone.</p>
      </div>
    </aside>
    <main class="main-panel">
      <header class="topbar">
        <div>
          <p class="eyebrow">LinkBox</p>
          <h2>{{ page_title }}</h2>
        </div>
        <button class="ghost-btn" type="button" onclick="document.documentElement.style.colorScheme = document.documentElement.style.colorScheme === 'light' ? 'dark' : 'light'">☀︎</button>
      </header>

      <section class="hero-card">
        <div>
          <p class="eyebrow">MVP</p>
          <h3>Create a beautiful share page in seconds.</h3>
          <p>Use one public URL to share links, notes, optional images, and a custom theme.</p>
        </div>
        <a class="ghost-btn" href="/page/demo" target="_blank">Preview</a>
      </section>

      <section class="grid-two">
        <form class="panel" method="post" action="{{ action_url }}" enctype="multipart/form-data">
          <div class="panel-head" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h4>{% if editing %}Edit page{% else %}Create a page{% endif %}</h4>
            <span class="pill">Single URL</span>
          </div>
          <label>Title
            <input name="title" required value="{{ page.title if page else '' }}" placeholder="My launch page">
          </label>
          <label>Description
            <textarea name="description" rows="3" placeholder="A short summary for your audience">{{ page.description if page else '' }}</textarea>
          </label>
          <label>Notes
            <textarea name="notes" rows="3" placeholder="Optional notes for your visitors">{{ page.notes if page else '' }}</textarea>
          </label>
          <div id="link-blocks">
            <label>Link 1 title
              <input name="link_title" value="{{ (page.links[0].title if page and page.links|length > 0 else '') }}" placeholder="Docs">
            </label>
            <label>Link 1 URL
              <input name="link_url" value="{{ (page.links[0].url if page and page.links|length > 0 else '') }}" placeholder="https://example.com">
            </label>
          </div>
          <button class="ghost-btn" type="button" onclick="addLinkField()">+ Add link</button>
          <label>Image upload
            <input type="file" name="image" accept="image/*">
          </label>
          <div class="color-row">
            <label>Theme color
              <input type="color" name="theme_color" value="{{ page.theme_color if page else '#6d5dfc' }}">
            </label>
            <label>Accent color
              <input type="color" name="accent_color" value="{{ page.accent_color if page else '#4f46e5' }}">
            </label>
          </div>
          <button class="primary-btn" type="submit">{% if editing %}Save changes{% else %}Create page{% endif %}</button>
        </form>

        <div class="panel">
          <div class="panel-head" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h4>Your pages</h4>
            <span class="pill">{{ pages|length }} total</span>
          </div>
          {% if pages %}
            <div class="page-list">
              {% for item in pages %}
                <article class="page-card">
                  <div>
                    <h5>{{ item.title }}</h5>
                    <p>{{ item.description or 'No description yet' }}</p>
                  </div>
                  <div class="action-row">
                    <a class="ghost-btn" href="/page/{{ item.slug }}" target="_blank">Open</a>
                    <a class="ghost-btn" href="/linkbox/{{ item.slug }}/edit">Edit</a>
                    <button class="ghost-btn" type="button" onclick="copyShareLink('/page/{{ item.slug }}')">Share</button>
                    <form method="post" action="/linkbox/{{ item.slug }}/duplicate" style="display:inline;">
                      <button class="ghost-btn" type="submit">Duplicate</button>
                    </form>
                    <form method="post" action="/linkbox/{{ item.slug }}/delete" style="display:inline;" onsubmit="return confirm('Delete this page?')">
                      <button class="ghost-btn danger" type="submit">Delete</button>
                    </form>
                  </div>
                </article>
              {% endfor %}
            </div>
          {% else %}
            <p class="empty-state">No pages yet. Create your first page to get started.</p>
          {% endif %}
        </div>
      </section>
    </main>
  </div>
  <script>
    function addLinkField() {
      const container = document.getElementById('link-blocks');
      if (!container) return;
      const count = container.querySelectorAll('label').length / 2 + 1;
      const wrapper = document.createElement('div');
      wrapper.innerHTML = `
        <label>Link ${count} title
          <input name="link_title" placeholder="Social">
        </label>
        <label>Link ${count} URL
          <input name="link_url" placeholder="https://example.com">
        </label>
      `;
      container.appendChild(wrapper);
    }
    function copyShareLink(path) {
      const url = `${window.location.origin}${path}`;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => window.alert('Share link copied!'));
      } else {
        window.prompt('Copy this link', url);
      }
    }
  </script>
</body>
</html>
"""


PUBLIC_TEMPLATE = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page.title }} | LinkBox</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #060816;
      --text: #f4f7ff;
      --muted: #9fb0d0;
      --accent: {{ page.theme_color or '#6d5dfc' }};
      --accent-2: {{ page.accent_color or '#4f46e5' }};
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, system-ui, sans-serif;
      min-height: 100vh;
      background: radial-gradient(circle at top left, #16214a 0%, var(--bg) 55%);
      color: var(--text);
      display: grid;
      place-items: center;
      padding: 24px;
    }
    .card {
      width: min(720px, 100%);
      border-radius: 28px;
      padding: 24px;
      background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.06));
      border: 1px solid rgba(255,255,255,0.14);
      box-shadow: 0 22px 60px rgba(0,0,0,0.35);
      backdrop-filter: blur(16px);
    }
    .card img { width: 100%; height: 240px; object-fit: cover; border-radius: 18px; margin-bottom: 18px; }
    .eyebrow { text-transform: uppercase; letter-spacing: 0.26em; color: #f4b95d; font-size: 0.74rem; margin: 0 0 6px; }
    .link-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
    .link-pill { text-decoration: none; color: white; padding: 12px 14px; border-radius: 14px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); }
    .meta-row { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; color: var(--muted); }
    .ghost-btn { border: none; cursor: pointer; padding: 10px 14px; border-radius: 999px; color: white; background: rgba(255,255,255,0.06); }
    @media (max-width: 560px) { body { padding: 12px; } .meta-row { flex-direction: column; gap: 10px; align-items: flex-start; } }
  </style>
</head>
<body>
  <main class="card">
    {% if page.image_url %}<img src="{{ page.image_url }}" alt="{{ page.title }}">{% endif %}
    <p class="eyebrow">LinkBox</p>
    <h1>{{ page.title }}</h1>
    {% if page.description %}<p>{{ page.description }}</p>{% endif %}
    {% if page.notes %}<p style="color: var(--muted); line-height: 1.7;">{{ page.notes }}</p>{% endif %}
    <div class="link-list">
      {% for link in page.links %}
        <a class="link-pill" href="{{ link.url }}" target="_blank" rel="noreferrer">{{ link.title }}</a>
      {% endfor %}
    </div>
    <div class="meta-row">
      <span>Views: {{ page.views }}</span>
      <button class="ghost-btn" type="button" onclick="copyLink()">Copy share link</button>
    </div>
  </main>
  <script>
    function copyLink() {
      const url = window.location.href;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => window.alert('Share link copied!'));
      } else {
        window.prompt('Copy this link', url);
      }
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return redirect(url_for("linkbox_dashboard"))


@app.route("/linkbox")
def linkbox_dashboard():
    pages = get_linkbox_pages()
    return render_template_string(
        DASHBOARD_TEMPLATE,
        page_title="Dashboard",
        pages=pages,
        page=None,
        editing=False,
        action_url=url_for("create_linkbox_page"),
    )


@app.route("/linkbox/create", methods=["POST"])
def create_linkbox_page():
    title = (request.form.get("title") or "").strip()
    if not title:
        return redirect(url_for("linkbox_dashboard"))

    description = (request.form.get("description") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    links = parse_linkbox_links(request.form)
    image_url = save_uploaded_image(request.files.get("image"))
    theme_color = (request.form.get("theme_color") or "#6d5dfc").strip()
    accent_color = (request.form.get("accent_color") or "#4f46e5").strip()

    conn = get_linkbox_connection()
    slug = create_unique_slug()
    conn.execute(
        """
        INSERT INTO linkbox_pages (slug, title, description, notes, links, image_url, theme_color, accent_color, views)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (slug, title, description, notes, json.dumps(links), image_url, theme_color, accent_color),
    )
    conn.commit()
    close_linkbox_connection(conn)
    return redirect(url_for("public_linkbox_page", slug=slug))


@app.route("/linkbox/<slug>/edit", methods=["GET", "POST"])
def edit_linkbox_page(slug):
    page = get_linkbox_page(slug)
    if not page:
        abort(404)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            return redirect(url_for("edit_linkbox_page", slug=slug))

        description = (request.form.get("description") or "").strip()
        notes = (request.form.get("notes") or "").strip()
        links = parse_linkbox_links(request.form)
        image_url = save_uploaded_image(request.files.get("image")) or page.get("image_url")
        theme_color = (request.form.get("theme_color") or "#6d5dfc").strip()
        accent_color = (request.form.get("accent_color") or "#4f46e5").strip()

        conn = get_linkbox_connection()
        conn.execute(
            """
            UPDATE linkbox_pages
            SET title = ?, description = ?, notes = ?, links = ?, image_url = ?, theme_color = ?, accent_color = ?, updated_at = CURRENT_TIMESTAMP
            WHERE slug = ?
            """,
            (title, description, notes, json.dumps(links), image_url, theme_color, accent_color, slug),
        )
        conn.commit()
        close_linkbox_connection(conn)
        return redirect(url_for("public_linkbox_page", slug=slug))

    pages = get_linkbox_pages()
    return render_template_string(
        DASHBOARD_TEMPLATE,
        page_title="Edit page",
        pages=pages,
        page=page,
        editing=True,
        action_url=url_for("edit_linkbox_page", slug=slug),
    )


@app.route("/linkbox/<slug>/duplicate", methods=["POST"])
def duplicate_linkbox_page(slug):
    source = get_linkbox_page(slug)
    if not source:
        abort(404)

    conn = get_linkbox_connection()
    new_slug = create_unique_slug()
    conn.execute(
        """
        INSERT INTO linkbox_pages (slug, title, description, notes, links, image_url, theme_color, accent_color, views)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            new_slug,
            f"{source['title']} copy",
            source.get("description") or "",
            source.get("notes") or "",
            json.dumps(source.get("links") or []),
            source.get("image_url"),
            source.get("theme_color") or "#6d5dfc",
            source.get("accent_color") or "#4f46e5",
        ),
    )
    conn.commit()
    close_linkbox_connection(conn)
    return redirect(url_for("linkbox_dashboard"))


@app.route("/linkbox/<slug>/delete", methods=["POST"])
def delete_linkbox_page(slug):
    conn = get_linkbox_connection()
    conn.execute("DELETE FROM linkbox_pages WHERE slug = ?", (slug,))
    conn.commit()
    close_linkbox_connection(conn)
    return redirect(url_for("linkbox_dashboard"))


@app.route("/page/demo")
def demo_linkbox_page():
    return render_template_string(
        PUBLIC_TEMPLATE,
        page={
            "title": "LinkBox Demo",
            "description": "A beautifully simple public share page built with Flask and a single self-contained file.",
            "notes": "Use this as a preview for your own landing page.",
            "links": [
                {"title": "Docs", "url": "https://example.com/docs"},
                {"title": "GitHub", "url": "https://github.com"},
            ],
            "image_url": None,
            "theme_color": "#6d5dfc",
            "accent_color": "#4f46e5",
            "views": 42,
        },
    )


@app.route("/page/<slug>")
def public_linkbox_page(slug):
    page = get_linkbox_page(slug)
    if not page:
        abort(404)

    conn = get_linkbox_connection()
    conn.execute("UPDATE linkbox_pages SET views = views + 1 WHERE slug = ?", (slug,))
    conn.commit()
    close_linkbox_connection(conn)
    return render_template_string(PUBLIC_TEMPLATE, page=page)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
'''
Path('app.py').write_text(content, encoding='utf-8')
