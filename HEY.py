import json
import os
import re
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import fitz
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "user_data" / "notes.json"
PRAYERS_FILE = BASE_DIR / "user_data" / "prayers.json"
BIBLE_SOURCE_FILE = BASE_DIR / "bible"
DATA_FILE.parent.mkdir(exist_ok=True)

SCRIPTURE = [
    {"reference": "Genesis 1:1", "text": "In the beginning God created the heavens and the earth.", "topic": "Creation"},
    {"reference": "Psalm 23:1", "text": "The Lord is my shepherd; I shall not want.", "topic": "Peace"},
    {"reference": "Philippians 4:13", "text": "I can do all things through Christ who strengthens me.", "topic": "Strength"},
    {"reference": "Romans 8:28", "text": "And we know that in all things God works for the good of those who love him.", "topic": "Hope"},
    {"reference": "John 3:16", "text": "For God so loved the world that he gave his one and only Son.", "topic": "Love"},
]

BOOK_CATALOG = [
    {"name": "Genesis", "testament": "Old Testament", "genre": "Law", "summary": "The beginning of creation, people, and the covenant story. Creation is central to the opening chapters.", "highlights": ["Creation", "Covenant", "Joseph"]},
    {"name": "Exodus", "testament": "Old Testament", "genre": "Law", "summary": "The story of God rescuing Israel and establishing his covenant with his people.", "highlights": ["Deliverance", "Law", "Moses"]},
    {"name": "Leviticus", "testament": "Old Testament", "genre": "Law", "summary": "Instruction for worship, holiness, and the daily life of God’s covenant people.", "highlights": ["Holiness", "Worship", "Sacrifice"]},
    {"name": "Numbers", "testament": "Old Testament", "genre": "Law", "summary": "The wilderness journey of Israel and the lessons learned in testing.", "highlights": ["Wilderness", "Testing", "Obedience"]},
    {"name": "Deuteronomy", "testament": "Old Testament", "genre": "Law", "summary": "Moses’ final words calling Israel to remember, obey, and trust God.", "highlights": ["Remember", "Obedience", "Blessing"]},
    {"name": "Joshua", "testament": "Old Testament", "genre": "History", "summary": "The conquest and settlement of the promised land under Joshua’s leadership.", "highlights": ["Leadership", "Victory", "Inheritance"]},
    {"name": "Judges", "testament": "Old Testament", "genre": "History", "summary": "Stories of Israel’s repeated cycles of faithfulness, failure, and rescue.", "highlights": ["Cycles", "Deliverance", "Faith"]},
    {"name": "Ruth", "testament": "Old Testament", "genre": "History", "summary": "A beautiful story of loyalty, mercy, and God’s quiet providence.", "highlights": ["Loyalty", "Mercy", "Providence"]},
    {"name": "1 Samuel", "testament": "Old Testament", "genre": "History", "summary": "The rise of Samuel, Saul, and the early monarchy in Israel.", "highlights": ["Leadership", "Kingship", "Prophecy"]},
    {"name": "2 Samuel", "testament": "Old Testament", "genre": "History", "summary": "The reign of David and the shaping of Israel’s kingdom.", "highlights": ["David", "Kingship", "Courage"]},
    {"name": "1 Kings", "testament": "Old Testament", "genre": "History", "summary": "The division of the kingdom and the reigns of Israel’s kings.", "highlights": ["Kingdom", "Wisdom", "Judgment"]},
    {"name": "2 Kings", "testament": "Old Testament", "genre": "History", "summary": "The decline of the kingdoms and the consequences of turning away from God.", "highlights": ["Decline", "Judgment", "Exile"]},
    {"name": "1 Chronicles", "testament": "Old Testament", "genre": "History", "summary": "A retelling of Israel’s history with an eye on God’s covenant and worship.", "highlights": ["Temple", "Worship", "Lineage"]},
    {"name": "2 Chronicles", "testament": "Old Testament", "genre": "History", "summary": "The history of Judah and the renewal of worship under reforming kings.", "highlights": ["Reform", "Temple", "Faithfulness"]},
    {"name": "Ezra", "testament": "Old Testament", "genre": "History", "summary": "The return from exile and the rebuilding of the temple and the people.", "highlights": ["Restoration", "Temple", "Community"]},
    {"name": "Nehemiah", "testament": "Old Testament", "genre": "History", "summary": "The rebuilding of Jerusalem’s walls and the people’s renewed commitment.", "highlights": ["Rebuilding", "Commitment", "Prayer"]},
    {"name": "Esther", "testament": "Old Testament", "genre": "History", "summary": "A story of courage, providence, and God’s hidden hand in danger.", "highlights": ["Courage", "Providence", "Deliverance"]},
    {"name": "Job", "testament": "Old Testament", "genre": "Poetry", "summary": "A probing conversation about suffering, trust, and the character of God.", "highlights": ["Suffering", "Trust", "Wisdom"]},
    {"name": "Psalms", "testament": "Old Testament", "genre": "Poetry", "summary": "A rich collection of prayers, praises, laments, and songs of devotion.", "highlights": ["Praise", "Lament", "Hope"]},
    {"name": "Proverbs", "testament": "Old Testament", "genre": "Wisdom", "summary": "Practical wisdom for life, character, and the fear of the Lord.", "highlights": ["Wisdom", "Character", "Instruction"]},
    {"name": "Ecclesiastes", "testament": "Old Testament", "genre": "Wisdom", "summary": "A reflection on the fleeting nature of life and the meaning of wisdom.", "highlights": ["Meaning", "Vanity", "Wisdom"]},
    {"name": "Song of Songs", "testament": "Old Testament", "genre": "Poetry", "summary": "A lyrical celebration of love, devotion, and beauty.", "highlights": ["Love", "Beauty", "Devotion"]},
    {"name": "Isaiah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A major prophetic voice calling the people back to God and pointing to hope.", "highlights": ["Hope", "Judgment", "Messiah"]},
    {"name": "Jeremiah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A prophet of warning, lament, and renewal during the fall of Judah.", "highlights": ["Warning", "Lament", "Renewal"]},
    {"name": "Lamentations", "testament": "Old Testament", "genre": "Poetry", "summary": "Poems of grief and sorrow over the destruction of Jerusalem.", "highlights": ["Grief", "Sorrow", "Mercy"]},
    {"name": "Ezekiel", "testament": "Old Testament", "genre": "Prophecy", "summary": "Visions of judgment, restoration, and the glory of God.", "highlights": ["Vision", "Restoration", "Glory"]},
    {"name": "Daniel", "testament": "Old Testament", "genre": "Prophecy", "summary": "Stories and visions that reveal God’s sovereignty over kingdoms and history.", "highlights": ["Sovereignty", "Vision", "Faith"]},
    {"name": "Hosea", "testament": "Old Testament", "genre": "Prophecy", "summary": "A prophet’s message of covenant love and the consequences of unfaithfulness.", "highlights": ["Love", "Faithfulness", "Repentance"]},
    {"name": "Joel", "testament": "Old Testament", "genre": "Prophecy", "summary": "A call to repentance and a promise of God’s Spirit.", "highlights": ["Repentance", "Spirit", "Judgment"]},
    {"name": "Amos", "testament": "Old Testament", "genre": "Prophecy", "summary": "A prophetic call for justice, mercy, and right living.", "highlights": ["Justice", "Mercy", "Righteousness"]},
    {"name": "Obadiah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A short prophecy about Edom’s pride and the justice of God.", "highlights": ["Pride", "Justice", "Humility"]},
    {"name": "Jonah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A story of compassion, repentance, and God’s mercy beyond borders.", "highlights": ["Mercy", "Repentance", "Compassion"]},
    {"name": "Micah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A message of justice, mercy, and the coming of the ruler from Bethlehem.", "highlights": ["Justice", "Mercy", "Messiah"]},
    {"name": "Nahum", "testament": "Old Testament", "genre": "Prophecy", "summary": "A prophecy of judgment against Nineveh and the justice of God.", "highlights": ["Judgment", "Justice", "Hope"]},
    {"name": "Habakkuk", "testament": "Old Testament", "genre": "Prophecy", "summary": "A dialogue about faith, suffering, and trusting God in hard times.", "highlights": ["Faith", "Suffering", "Trust"]},
    {"name": "Zephaniah", "testament": "Old Testament", "genre": "Prophecy", "summary": "A call to repentance before the day of the Lord.", "highlights": ["Repentance", "Judgment", "Hope"]},
    {"name": "Haggai", "testament": "Old Testament", "genre": "Prophecy", "summary": "A call to rebuild the temple and renew the people’s devotion.", "highlights": ["Rebuilding", "Devotion", "Priority"]},
    {"name": "Zechariah", "testament": "Old Testament", "genre": "Prophecy", "summary": "Visions of restoration, hope, and the coming king.", "highlights": ["Restoration", "Hope", "King"]},
    {"name": "Malachi", "testament": "Old Testament", "genre": "Prophecy", "summary": "A final call to covenant faithfulness before the coming of the Lord.", "highlights": ["Faithfulness", "Covenant", "Preparation"]},
    {"name": "Matthew", "testament": "New Testament", "genre": "Gospel", "summary": "The Gospel that presents Jesus as the promised Messiah and King.", "highlights": ["Messiah", "Kingdom", "Teaching"]},
    {"name": "Mark", "testament": "New Testament", "genre": "Gospel", "summary": "A vivid Gospel that highlights the action, authority, and compassion of Jesus.", "highlights": ["Action", "Authority", "Compassion"]},
    {"name": "Luke", "testament": "New Testament", "genre": "Gospel", "summary": "A Gospel that emphasizes Jesus’ compassion, mercy, and care for the vulnerable.", "highlights": ["Compassion", "Mercy", "Salvation"]},
    {"name": "John", "testament": "New Testament", "genre": "Gospel", "summary": "A Gospel that reveals Jesus as the eternal Word and the Son of God.", "highlights": ["Word", "Life", "Light"]},
    {"name": "Acts", "testament": "New Testament", "genre": "History", "summary": "The story of the early church, the spread of the gospel, and the work of the Spirit.", "highlights": ["Church", "Mission", "Spirit"]},
    {"name": "Romans", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s great letter on sin, grace, righteousness, and life in Christ.", "highlights": ["Grace", "Righteousness", "Justification"]},
    {"name": "1 Corinthians", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s guidance for a church facing division, immorality, and spiritual confusion.", "highlights": ["Church", "Holiness", "Love"]},
    {"name": "2 Corinthians", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s encouragement and defense of his ministry and the church’s faith.", "highlights": ["Encouragement", "Ministry", "Grace"]},
    {"name": "Galatians", "testament": "New Testament", "genre": "Letter", "summary": "A strong letter on freedom in Christ and the gospel of grace.", "highlights": ["Freedom", "Grace", "Faith"]},
    {"name": "Ephesians", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s teaching on unity, spiritual blessing, and the church as Christ’s body.", "highlights": ["Unity", "Church", "Blessing"]},
    {"name": "Philippians", "testament": "New Testament", "genre": "Letter", "summary": "A joyful letter about joy, humility, and Christ’s example.", "highlights": ["Joy", "Humility", "Christ"]},
    {"name": "Colossians", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s teaching on the supremacy of Christ and the fullness of life in him.", "highlights": ["Christ", "Fullness", "Wisdom"]},
    {"name": "1 Thessalonians", "testament": "New Testament", "genre": "Letter", "summary": "Encouragement for a young church facing persecution and waiting for Christ.", "highlights": ["Hope", "Perseverance", "Holiness"]},
    {"name": "2 Thessalonians", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s instruction about endurance and the coming of the Lord.", "highlights": ["Endurance", "Hope", "Truth"]},
    {"name": "1 Timothy", "testament": "New Testament", "genre": "Letter", "summary": "Teaching on leadership, doctrine, and faithful ministry in the church.", "highlights": ["Leadership", "Doctrine", "Ministry"]},
    {"name": "2 Timothy", "testament": "New Testament", "genre": "Letter", "summary": "Paul’s last encouragement to remain faithful and bold in the gospel.", "highlights": ["Faithfulness", "Courage", "Gospel"]},
    {"name": "Titus", "testament": "New Testament", "genre": "Letter", "summary": "Instruction for healthy church life, godliness, and good works.", "highlights": ["Church", "Godliness", "Good works"]},
    {"name": "Philemon", "testament": "New Testament", "genre": "Letter", "summary": "A personal letter about forgiveness, reconciliation, and Christian brotherhood.", "highlights": ["Forgiveness", "Reconciliation", "Brotherhood"]},
    {"name": "Hebrews", "testament": "New Testament", "genre": "Letter", "summary": "A letter that exalts Jesus as superior and calls believers to persevere.", "highlights": ["Jesus", "Faith", "Perseverance"]},
    {"name": "James", "testament": "New Testament", "genre": "Letter", "summary": "Practical teaching on wisdom, patience, and living out the faith.", "highlights": ["Wisdom", "Patience", "Faith"]},
    {"name": "1 Peter", "testament": "New Testament", "genre": "Letter", "summary": "Encouragement for believers facing suffering and calling them to holy living.", "highlights": ["Suffering", "Holiness", "Hope"]},
    {"name": "2 Peter", "testament": "New Testament", "genre": "Letter", "summary": "A warning against false teaching and an appeal to grow in Christ.", "highlights": ["Growth", "Truth", "Warning"]},
    {"name": "1 John", "testament": "New Testament", "genre": "Letter", "summary": "Teaching on love, light, and the assurance of fellowship with God.", "highlights": ["Love", "Light", "Fellowship"]},
    {"name": "2 John", "testament": "New Testament", "genre": "Letter", "summary": "A brief letter urging believers to walk in truth and love.", "highlights": ["Truth", "Love", "Hospitality"]},
    {"name": "3 John", "testament": "New Testament", "genre": "Letter", "summary": "A short letter encouraging faithful hospitality and perseverance.", "highlights": ["Hospitality", "Faithfulness", "Truth"]},
    {"name": "Jude", "testament": "New Testament", "genre": "Letter", "summary": "A warning to contend for the faith and resist false teachers.", "highlights": ["Faith", "Warning", "Truth"]},
    {"name": "Revelation", "testament": "New Testament", "genre": "Prophecy", "summary": "The final vision of victory, judgment, and the new creation. Revelation points to hope and triumph.", "highlights": ["Victory", "Hope", "New creation"]},
]

BOOK_LOOKUP = {book["name"]: book for book in BOOK_CATALOG}

PDF_CACHE = None

LINKBOX_DB_PATH = os.environ.get("LINKBOX_DB_PATH", str(BASE_DIR / "database.db"))
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
_LINKBOX_SHARED_CONN = None


def get_book_catalog():
    return [dict(book) for book in BOOK_CATALOG]


def get_book_groups():
    books = get_book_catalog()
    old_testament = [book for book in books if book["testament"] == "Old Testament"]
    new_testament = [book for book in books if book["testament"] == "New Testament"]
    return [
        {"label": "Old Testament", "books": old_testament},
        {"label": "New Testament", "books": new_testament},
    ]


def get_book_detail(book_name):
    return dict(BOOK_LOOKUP.get(book_name, {"name": book_name, "testament": "Scripture", "genre": "Book", "summary": f"{book_name} is part of the Bible and can be explored in detail.", "highlights": []}))


def extract_bible_passages():
    global PDF_CACHE
    if PDF_CACHE is not None:
        return PDF_CACHE

    if not BIBLE_SOURCE_FILE.exists():
        PDF_CACHE = []
        return PDF_CACHE

    text = ""
    try:
        document = fitz.open(BIBLE_SOURCE_FILE)
        text = "\n".join(page.get_text("text") for page in document)
        document.close()
    except Exception:
        text = BIBLE_SOURCE_FILE.read_text(encoding="utf-8", errors="ignore")

    passages = []
    title_hint = "Bible passage"
    for line in re.split(r"\n+", text):
        line = line.strip()
        if not line or len(line) < 20:
            continue
        lowered = line.lower()
        if lowered.startswith(("the holy bible", "holman", "copyright", "books of the bible", "introduction", "csb_", "printed in china", "binding", "additional material")):
            continue
        if re.search(r"\b(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)\b", line):
            title_hint = line[:50]
            continue
        if len(line) > 500:
            continue
        reference = title_hint
        if re.match(r"^(?P<book>[1-3]?\s*[A-Za-z]+(?:\s[1-3])?)\s+(?P<chapter>\d+)(?::(?P<verse>\d+))?", line):
            match = re.match(r"^(?P<book>[1-3]?\s*[A-Za-z]+(?:\s[1-3])?)\s+(?P<chapter>\d+)(?::(?P<verse>\d+))?", line)
            book = match.group("book").strip()
            chapter = match.group("chapter")
            verse = match.group("verse") or ""
            reference = f"{book} {chapter}:{verse}".rstrip(':')
        passages.append({
            "reference": reference,
            "text": line[:360],
            "topic": "Bible text",
        })

    combined = []
    seen = set()
    for entry in SCRIPTURE + passages:
        key = (entry["reference"], entry["text"])
        if key in seen:
            continue
        seen.add(key)
        combined.append(entry)

    PDF_CACHE = combined[:80]
    return PDF_CACHE


def load_notes():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_notes(notes):
    DATA_FILE.write_text(json.dumps(notes, indent=2), encoding="utf-8")


def load_prayers():
    if PRAYERS_FILE.exists():
        try:
            return json.loads(PRAYERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_prayers(prayers):
    PRAYERS_FILE.write_text(json.dumps(prayers, indent=2), encoding="utf-8")


def get_daily_verse():
    passages = extract_bible_passages() or SCRIPTURE
    index = date.today().day % len(passages)
    return passages[index]


def build_page_context(page_title, template_name, assistant_question=None, assistant_answer=None):
    notes = load_notes()
    context = {
        "page_title": page_title,
        "daily_verse": get_daily_verse(),
        "favorite_count": len(notes),
        "assistant_question": assistant_question or "",
        "assistant_answer": assistant_answer or "",
        "prayers": load_prayers(),
    }
    return context


@app.route("/")
def index():
    return redirect(url_for("linkbox_dashboard"))


@app.route("/reader")
def reader():
    return render_template("reader.html", **build_page_context("Bible Reader", "reader"))


@app.route("/journal")
def journal():
    return render_template("journal.html", **build_page_context("Prayer Journal", "journal"))


@app.route("/favorites")
def favorites():
    return render_template("favorites.html", **build_page_context("Favorites", "favorites"))


@app.route("/assistant")
def assistant():
    question = request.args.get("question", "").strip()
    if not question:
        answer = "Ask about a passage, theme, or person in Scripture and I will offer a concise reflection."
    else:
        q = question.lower()
        if "love" in q:
            answer = "Love is presented throughout Scripture as patient, kind, and sacrificial, especially in Christ's example."
        elif "fear" in q:
            answer = "The Bible repeatedly reminds us that God gives courage and peace rather than fear."
        else:
            answer = f"A helpful reflection on {question} is to read the surrounding passage slowly and note the main theme and command."
    context = build_page_context("AI Assistant", "assistant", assistant_question=question, assistant_answer=answer)
    return render_template("assistant.html", **context)


@app.route("/books")
def books():
    context = build_page_context("Books", "books")
    context["book_groups"] = get_book_groups()
    return render_template("books.html", **context)


@app.route("/book/<book_name>")
def book_detail(book_name):
    context = build_page_context(book_name, "book_detail")
    context["book"] = get_book_detail(book_name)
    return render_template("book_detail.html", **context)


@app.route("/api/search")
def bible_search():
    query = (request.args.get("query") or "").strip().lower()
    passages = extract_bible_passages()
    if not query:
        return jsonify(passages[:10])
    matches = [
        passage for passage in passages
        if query in passage["text"].lower() or query in passage["reference"].lower()
    ][:10]
    return jsonify(matches)


@app.route("/api/prayers", methods=["GET"])
def get_prayers():
    return jsonify(load_prayers())


@app.route("/api/prayers", methods=["POST"])
def create_prayer():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "Untitled prayer").strip()
    body = (payload.get("body") or "").strip()
    if not title or not body:
        return jsonify({"error": "Title and body are required"}), 400
    prayers = load_prayers()
    prayer = {"id": len(prayers) + 1, "title": title, "body": body, "answered": False}
    prayers.append(prayer)
    save_prayers(prayers)
    return jsonify(prayer), 201


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
    conn.close()


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


def create_unique_slug(title, db_path=None):
    base_slug = uuid.uuid4().hex[:10]
    slug = base_slug
    conn = get_linkbox_connection(db_path)
    while conn.execute("SELECT 1 FROM linkbox_pages WHERE slug = ?", (slug,)).fetchone():
        slug = uuid.uuid4().hex[:10]
    close_linkbox_connection(conn, db_path)
    return slug


@app.route("/linkbox")
def linkbox_dashboard():
    pages = get_linkbox_pages()
    return render_template("linkbox_dashboard.html", pages=pages, page=None, editing=False, action_url=url_for("create_linkbox_page"))


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
    slug = create_unique_slug(title)
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
    return render_template("linkbox_dashboard.html", pages=pages, page=page, editing=True, action_url=url_for("edit_linkbox_page", slug=slug))


@app.route("/linkbox/<slug>/duplicate", methods=["POST"])
def duplicate_linkbox_page(slug):
    source = get_linkbox_page(slug)
    if not source:
        abort(404)

    conn = get_linkbox_connection()
    new_slug = create_unique_slug(f"{source['title']} copy")
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
    return render_template("linkbox_public.html", page={
        "title": "LinkBox Demo",
        "description": "A beautifully simple public share page built with Flask, SQLite, and glassmorphism styling.",
        "notes": "Use this as a preview for your own landing page.",
        "links": [
            {"title": "Docs", "url": "https://example.com/docs"},
            {"title": "GitHub", "url": "https://github.com"},
        ],
        "image_url": None,
        "theme_color": "#6d5dfc",
        "accent_color": "#4f46e5",
        "views": 42,
    })


@app.route("/page/<slug>")
def public_linkbox_page(slug):
    page = get_linkbox_page(slug)
    if not page:
        abort(404)

    conn = get_linkbox_connection()
    conn.execute("UPDATE linkbox_pages SET views = views + 1 WHERE slug = ?", (slug,))
    conn.commit()
    close_linkbox_connection(conn)
    return render_template("linkbox_public.html", page=page)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
