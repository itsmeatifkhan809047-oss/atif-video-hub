import os
import sqlite3
import threading
from werkzeug.utils import secure_filename
from flask import Flask, request, redirect, url_for, render_template_string, flash
import cloudinary
import cloudinary.uploader
import cloudinary.api

# ================= CREDENTIALS CONFIGURATION =================
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "809047")
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dmzqlfd9s")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "884785368881513")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "t2JjczLpiFQw2OnW_vbvjbdLwEg")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

app = Flask(__name__)
app.secret_key = "jiobharat_opera_super_secret_key"
DB_NAME = "videos.db"
UPLOAD_FOLDER = "temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE SETUP & AUTO-SYNC =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            download_url TEXT NOT NULL,
            public_id TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def sync_from_cloudinary():
    """Cloudinary se saari purani uploaded videos fetch karke DB me sync karta hai"""
    try:
        init_db()
        result = cloudinary.api.resources(
            resource_type="video",
            type="upload",
            max_results=500
        )
        resources = result.get("resources", [])
        
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        for item in resources:
            pub_id = item.get("public_id")
            dl_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/w_360,c_scale,q_auto:eco,fl_attachment/{pub_id}.mp4"
            clean_title = pub_id.split("/")[-1].replace("_", " ")
            
            cur.execute("""
                INSERT OR IGNORE INTO videos (title, download_url, public_id)
                VALUES (?, ?, ?)
            """, (clean_title, dl_url, pub_id))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cloudinary sync error: {e}")

init_db()
sync_from_cloudinary()

# ================= BACKGROUND LOCAL FILE UPLOAD =================
def process_file_upload_background(file_path, video_title):
    try:
        # Cloudinary Chunk Upload with Auto 360p Downscaling & Attachment Flag
        upload_data = cloudinary.uploader.upload_large(
            file_path,
            resource_type="video",
            chunk_size=6000000,
            eager=[
                {
                    "width": 360,
                    "crop": "scale",
                    "quality": "auto:eco",
                    "flags": "attachment",
                    "format": "mp4"
                }
            ],
            eager_async=False
        )

        pub_id = upload_data.get("public_id")
        final_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/w_360,c_scale,q_auto:eco,fl_attachment/{pub_id}.mp4"

        # SQLite DB save
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO videos (title, download_url, public_id) VALUES (?, ?, ?)",
            (video_title, final_url, pub_id)
        )
        conn.commit()
        conn.close()
    except Exception as err:
        print(f"Background upload error: {err}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ================= HTML TEMPLATES (PURE HTML / OPERA MINI COMPLIANT) =================

HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Portal</title>
    <style>
        body { font-family: Arial, sans-serif; background: #e5e5e5; margin: 0; padding: 8px; }
        .top-bar { text-align: right; margin-bottom: 12px; }
        .admin-link { background: #222; color: #fff; padding: 6px 12px; text-decoration: none; font-size: 13px; font-weight: bold; border-radius: 3px; }
        .sync-link { background: #007bff; color: #fff; padding: 6px 10px; text-decoration: none; font-size: 13px; font-weight: bold; border-radius: 3px; margin-right: 5px; }
        .search-container { background: #fff; border: 1px solid #bbb; padding: 10px; margin-bottom: 12px; text-align: center; }
        .search-input { width: 65%; padding: 6px; font-size: 14px; border: 1px solid #999; }
        .search-btn { padding: 6px 12px; font-size: 14px; background: #0b5ed7; color: #fff; border: 1px solid #0a58ca; font-weight: bold; }
        .video-card { background: #fff; border: 1px solid #ccc; padding: 10px; margin-bottom: 12px; text-align: center; }
        .thumb-img { width: 100%; max-height: 180px; object-fit: cover; background: #000; display: block; margin-bottom: 8px; border: 1px solid #eee; }
        .video-title { font-size: 15px; font-weight: bold; margin-bottom: 8px; color: #111; word-wrap: break-word; text-align: left; }
        .btn-download { display: block; background: #198754; color: #ffffff; text-align: center; padding: 9px 0; text-decoration: none; font-size: 15px; font-weight: bold; margin-bottom: 6px; }
        .action-row { width: 100%; }
        .btn-action { display: inline-block; width: 48%; text-align: center; padding: 6px 0; text-decoration: none; font-size: 13px; font-weight: bold; }
        .btn-rename { background: #ffc107; color: #000; float: left; }
        .btn-delete { background: #dc3545; color: #fff; float: right; }
        .clear { clear: both; }
        .pagination { text-align: center; margin: 15px 0; }
        .page-btn { display: inline-block; padding: 6px 15px; background: #333; color: #fff; text-decoration: none; font-size: 13px; margin: 0 4px; }
    </style>
</head>
<body>
    <div class="top-bar">
        <a href="{{ url_for('sync_videos') }}" class="sync-link">&#8635; Refresh Videos</a>
        <a href="{{ url_for('admin_panel') }}" class="admin-link">Admin Upload</a>
    </div>

    <div class="search-container">
        <form method="GET" action="{{ url_for('home') }}">
            <input type="text" name="q" value="{{ query }}" placeholder="Search here..." class="search-input">
            <input type="submit" value="Search" class="search-btn">
        </form>
    </div>

    {% for vid in videos %}
    <div class="video-card">
        <img src="https://res.cloudinary.com/dmzqlfd9s/video/upload/w_320,h_180,c_fill,so_0,q_auto:eco/{{ vid[3] }}.jpg" alt="Thumbnail" class="thumb-img">
        <div class="video-title">{{ vid[1] }}</div>
        <a href="{{ vid[2] }}" class="btn-download">DOWNLOAD</a>
        <div class="action-row">
            <a href="{{ url_for('rename_video', video_id=vid[0]) }}" class="btn-action btn-rename">Rename</a>
            <a href="{{ url_for('delete_video', video_id=vid[0]) }}" class="btn-action btn-delete">Delete</a>
            <div class="clear"></div>
        </div>
    </div>
    {% else %}
    <p style="text-align: center; color: #666;">No videos found.</p>
    {% endfor %}

    <div class="pagination">
        {% if page > 1 %}
            <a href="{{ url_for('home', page=page-1, q=query) }}" class="page-btn">&laquo; Prev</a>
        {% endif %}
        {% if has_next %}
            <a href="{{ url_for('home', page=page+1, q=query) }}" class="page-btn">Next &raquo;</a>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .box { background: #fff; border: 1px solid #ddd; padding: 20px; width: 100%; max-width: 380px; box-sizing: border-box; }
        h3 { text-align: center; margin-top: 0; }
        .field { margin-bottom: 12px; }
        label { display: block; font-size: 13px; font-weight: bold; margin-bottom: 4px; }
        input[type="text"], input[type="password"], input[type="file"] { width: 100%; padding: 8px; box-sizing: border-box; font-size: 14px; border: 1px solid #aaa; }
        .btn-ok { width: 100%; background: #007bff; color: #fff; padding: 10px; border: none; font-size: 16px; font-weight: bold; cursor: pointer; }
        .alert { padding: 8px; margin-bottom: 12px; font-size: 13px; text-align: center; }
        .err { background: #f8d7da; color: #721c24; }
        .succ { background: #d1e7dd; color: #0f5132; }
        .back { display: block; text-align: center; margin-top: 15px; text-decoration: none; color: #444; font-size: 13px; }
    </style>
</head>
<body>
    <div class="box">
        <h3>Upload Video From Storage</h3>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for cat, msg in messages %}
                    <div class="alert {{ cat }}">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST" enctype="multipart/form-data">
            <div class="field">
                <label>Choose Video File (from phone):</label>
                <input type="file" name="video_file" accept="video/*" required>
            </div>
            <div class="field">
                <label>Video Name / Title:</label>
                <input type="text" name="name" placeholder="Enter video name" required>
            </div>
            <div class="field">
                <label>Admin Password:</label>
                <input type="password" name="password" placeholder="Enter Admin Password" required>
            </div>
            <input type="submit" value="OK" class="btn-ok">
        </form>
        <a href="{{ url_for('home') }}" class="back">&larr; Back to Videos</a>
    </div>
</body>
</html>
"""

CONFIRM_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ action|title }} Video</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f7f7f7; padding: 15px; text-align: center; }
        .card { background: #fff; border: 1px solid #ccc; padding: 15px; max-width: 320px; margin: 0 auto; }
        input { width: 90%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
        .btn-sub { background: #333; color: #fff; border: none; font-size: 15px; font-weight: bold; padding: 8px 0; width: 90%; cursor: pointer; }
    </style>
</head>
<body>
    <div class="card">
        <h3>{{ action|title }} Video</h3>
        <p><strong>{{ video[1] }}</strong></p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for cat, msg in messages %}
                    <p style="color: red; font-size: 13px;">{{ msg }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            {% if action == 'rename' %}
                <input type="text" name="new_name" value="{{ video[1] }}" required>
            {% endif %}
            <input type="password" name="password" placeholder="Admin Password" required>
            <input type="submit" value="OK" class="btn-sub">
        </form>
        <br>
        <a href="{{ url_for('home') }}" style="font-size: 13px; color: #555;">Cancel</a>
    </div>
</body>
</html>
"""

# ================= APPLICATION ROUTES =================

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    limit = 10
    offset = (page - 1) * limit

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if query:
        cur.execute(
            "SELECT id, title, download_url, public_id FROM videos WHERE title LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (f"%{query}%", limit + 1, offset)
        )
    else:
        cur.execute(
            "SELECT id, title, download_url, public_id FROM videos ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit + 1, offset)
        )

    rows = cur.fetchall()
    conn.close()

    has_next = len(rows) > limit
    videos = rows[:limit]

    return render_template_string(HOME_PAGE, videos=videos, query=query, page=page, has_next=has_next)

@app.route("/sync")
def sync_videos():
    sync_from_cloudinary()
    return redirect(url_for("home"))

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        file = request.files.get("video_file")
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()

        if password != ADMIN_PASSWORD:
            flash("Incorrect Password!", "err")
            return render_template_string(ADMIN_PAGE)

        if not file or file.filename == "" or not name:
            flash("File and Video Name are both required!", "err")
            return render_template_string(ADMIN_PAGE)

        # Temporary phone/storage save
        safe_name = secure_filename(file.filename)
        saved_path = os.path.join(UPLOAD_FOLDER, f"up_{os.getpid()}_{safe_name}")
        file.save(saved_path)

        # Background chunk upload start
        th = threading.Thread(target=process_file_upload_background, args=(saved_path, name))
        th.daemon = True
        th.start()

        flash("Video storage se upload hona shuru ho gayi hai! Thodi der me home page par dikh jayegi.", "succ")

    return render_template_string(ADMIN_PAGE)

@app.route("/rename/<int:video_id>", methods=["GET", "POST"])
def rename_video(video_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video:
        return redirect(url_for("home"))

    if request.method == "POST":
        new_name = request.form.get("new_name", "").strip()
        password = request.form.get("password", "").strip()

        if password != ADMIN_PASSWORD:
            flash("Invalid Password!", "err")
            return render_template_string(CONFIRM_PAGE, video=video, action="rename")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE videos SET title = ? WHERE id = ?", (new_name, video_id))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template_string(CONFIRM_PAGE, video=video, action="rename")

@app.route("/delete/<int:video_id>", methods=["GET", "POST"])
def delete_video(video_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, title, public_id FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video:
        return redirect(url_for("home"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if password != ADMIN_PASSWORD:
            flash("Invalid Password!", "err")
            return render_template_string(CONFIRM_PAGE, video=video, action="delete")

        try:
            cloudinary.uploader.destroy(video[2], resource_type="video")
        except Exception as e:
            print(f"Cloudinary destroy error: {e}")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template_string(CONFIRM_PAGE, video=video, action="delete")

# ================= RENDER & PRODUCTION ENTRY POINT =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
