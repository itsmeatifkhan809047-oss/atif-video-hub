import os
import sqlite3
import threading
from werkzeug.utils import secure_filename
from flask import Flask, request, redirect, url_for, render_template_string, flash, jsonify
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

# ================= HTML TEMPLATES (NO JS FOR OPERA MINI USERS) =================

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
    <title>Admin Upload Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eef2f7; display: flex; justify-content: center; align-items: center; min-height: 90vh; margin: 0; }
        .box { background: #ffffff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 90%; max-width: 420px; }
        h3 { text-align: center; color: #333; margin-top: 0; }
        .field { margin-bottom: 14px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #444; }
        input[type="text"], input[type="password"], input[type="file"] { width: 100%; padding: 9px; box-sizing: border-box; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; }
        .btn-ok { width: 100%; background: #007bff; color: #fff; padding: 12px; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .btn-ok:hover { background: #0056b3; }
        .back { display: block; text-align: center; margin-top: 15px; text-decoration: none; color: #666; font-size: 13px; }
        
        /* MediaFire Style Progress Bar */
        .progress-box { display: none; margin-top: 18px; background: #f8f9fa; border: 1px solid #ddd; padding: 12px; border-radius: 6px; }
        .progress-header { display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 6px; color: #333; }
        .progress-track { width: 100%; height: 18px; background: #e9ecef; border-radius: 10px; overflow: hidden; position: relative; }
        .progress-fill { width: 0%; height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.2s linear; }
        .status-text { font-size: 12px; color: #555; text-align: center; margin-top: 6px; }
        .alert-msg { display: none; padding: 10px; margin-bottom: 12px; font-size: 13px; border-radius: 4px; text-align: center; }
    </style>
</head>
<body>
    <div class="box">
        <h3>Upload Video Panel</h3>
        <div id="alert-msg" class="alert-msg"></div>

        <form id="uploadForm">
            <div class="field">
                <label>Choose Video File (Internal Storage):</label>
                <input type="file" id="video_file" name="video_file" accept="video/*" required>
            </div>
            <div class="field">
                <label>Video Name / Title:</label>
                <input type="text" id="video_name" name="name" placeholder="Enter video title" required>
            </div>
            <div class="field">
                <label>Admin Password:</label>
                <input type="password" id="admin_pass" name="password" placeholder="Enter Admin Password" required>
            </div>
            <input type="button" id="submitBtn" value="OK" class="btn-ok" onclick="uploadWithProgress()">
        </form>

        <div id="progressBox" class="progress-box">
            <div class="progress-header">
                <span>Uploading...</span>
                <span id="percentText">0%</span>
            </div>
            <div class="progress-track">
                <div id="progressFill" class="progress-fill"></div>
            </div>
            <div id="statusText" class="status-text">Uploading bytes: 0 MB / 0 MB</div>
        </div>

        <a href="{{ url_for('home') }}" class="back">&larr; Back to Videos</a>
    </div>

    <script>
        function uploadWithProgress() {
            var fileInput = document.getElementById('video_file');
            var nameInput = document.getElementById('video_name');
            var passInput = document.getElementById('admin_pass');
            var alertBox = document.getElementById('alert-msg');
            var progressBox = document.getElementById('progressBox');
            var progressFill = document.getElementById('progressFill');
            var percentText = document.getElementById('percentText');
            var statusText = document.getElementById('statusText');
            var submitBtn = document.getElementById('submitBtn');

            if (!fileInput.files.length || !nameInput.value.trim() || !passInput.value.trim()) {
                alertBox.style.display = 'block';
                alertBox.style.background = '#f8d7da';
                alertBox.style.color = '#721c24';
                alertBox.innerText = 'Please select a file and fill all fields!';
                return;
            }

            var file = fileInput.files[0];
            var formData = new FormData();
            formData.append('video_file', file);
            formData.append('name', nameInput.value.trim());
            formData.append('password', passInput.value.trim());

            var xhr = new XMLHttpRequest();
            xhr.open('POST', '{{ url_for("admin_panel") }}', true);

            progressBox.style.display = 'block';
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.6';
            alertBox.style.display = 'none';

            // Real-Time Progress Event
            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    var percent = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = percent + '%';
                    percentText.innerText = percent + '%';
                    var loadedMB = (e.loaded / (1024 * 1024)).toFixed(2);
                    var totalMB = (e.total / (1024 * 1024)).toFixed(2);
                    statusText.innerText = 'Uploading: ' + loadedMB + ' MB / ' + totalMB + ' MB';
                }
            };

            xhr.onload = function() {
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                if (xhr.status === 200) {
                    var res = JSON.parse(xhr.responseText);
                    if (res.status === 'success') {
                        alertBox.style.display = 'block';
                        alertBox.style.background = '#d1e7dd';
                        alertBox.style.color = '#0f5132';
                        alertBox.innerText = res.message;
                        statusText.innerText = 'Upload Completed 100%! Processing in cloud...';
                        document.getElementById('uploadForm').reset();
                    } else {
                        alertBox.style.display = 'block';
                        alertBox.style.background = '#f8d7da';
                        alertBox.style.color = '#721c24';
                        alertBox.innerText = res.message;
                        progressBox.style.display = 'none';
                    }
                } else {
                    alertBox.style.display = 'block';
                    alertBox.style.background = '#f8d7da';
                    alertBox.style.color = '#721c24';
                    alertBox.innerText = 'Upload failed with server error.';
                }
            };

            xhr.onerror = function() {
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
                alertBox.style.display = 'block';
                alertBox.style.background = '#f8d7da';
                alertBox.style.color = '#721c24';
                alertBox.innerText = 'Connection error occurred during upload.';
            };

            xhr.send(formData);
        }
    </script>
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
            return jsonify({"status": "error", "message": "Incorrect Admin Password!"})

        if not file or file.filename == "" or not name:
            return jsonify({"status": "error", "message": "File and Video Name are required!"})

        safe_name = secure_filename(file.filename)
        saved_path = os.path.join(UPLOAD_FOLDER, f"up_{os.getpid()}_{safe_name}")
        file.save(saved_path)

        th = threading.Thread(target=process_file_upload_background, args=(saved_path, name))
        th.daemon = True
        th.start()

        return jsonify({"status": "success", "message": "File upload complete! Background cloud processing started."})

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

# ================= RENDER ENTRY POINT =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
