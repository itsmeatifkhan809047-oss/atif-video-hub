import os
import time
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, flash, jsonify
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils

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

# ================= HTML TEMPLATES (NO JAVASCRIPT FOR OPERA MINI) =================

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
        .btn-ok { width: 100%; background: #007bff; color: #fff; padding: 12px; border: none; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; }
        .btn-ok:disabled { background: #86b7fe; cursor: not-allowed; }
        .back { display: block; text-align: center; margin-top: 15px; text-decoration: none; color: #666; font-size: 13px; }
        
        .progress-box { display: none; margin-top: 18px; background: #f8f9fa; border: 1px solid #ddd; padding: 12px; border-radius: 6px; }
        .progress-header { display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 6px; color: #333; }
        .progress-track { width: 100%; height: 18px; background: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { width: 0%; height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.15s ease-out; }
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
                <input type="file" id="video_file" accept="video/*" required>
            </div>
            <div class="field">
                <label>Video Name / Title:</label>
                <input type="text" id="video_name" placeholder="Enter video title" required>
            </div>
            <div class="field">
                <label>Admin Password:</label>
                <input type="password" id="admin_pass" placeholder="Enter Admin Password" required>
            </div>
            <input type="button" id="submitBtn" value="OK" class="btn-ok" onclick="startDirectUpload()">
        </form>

        <div id="progressBox" class="progress-box">
            <div class="progress-header">
                <span id="procLabel">Uploading...</span>
                <span id="percentText">0%</span>
            </div>
            <div class="progress-track">
                <div id="progressFill" class="progress-fill"></div>
            </div>
            <div id="statusText" class="status-text">Starting high-speed upload...</div>
        </div>

        <a href="{{ url_for('home') }}" class="back">&larr; Back to Videos</a>
    </div>

    <script>
        async function startDirectUpload() {
            const fileInput = document.getElementById('video_file');
            const nameInput = document.getElementById('video_name');
            const passInput = document.getElementById('admin_pass');
            const alertBox = document.getElementById('alert-msg');
            const progressBox = document.getElementById('progressBox');
            const progressFill = document.getElementById('progressFill');
            const percentText = document.getElementById('percentText');
            const statusText = document.getElementById('statusText');
            const submitBtn = document.getElementById('submitBtn');
            const procLabel = document.getElementById('procLabel');

            if (!fileInput.files.length || !nameInput.value.trim() || !passInput.value.trim()) {
                alertBox.style.display = 'block';
                alertBox.style.background = '#f8d7da';
                alertBox.style.color = '#721c24';
                alertBox.innerText = 'Please choose a file and fill all fields!';
                return;
            }

            const file = fileInput.files[0];
            const videoTitle = nameInput.value.trim();
            const password = passInput.value.trim();

            submitBtn.disabled = true;
            alertBox.style.display = 'none';
            progressBox.style.display = 'block';
            progressFill.style.width = '0%';
            percentText.innerText = '0%';
            statusText.innerText = 'Authenticating with cloud...';

            try {
                // Step 1: Get signature from Render backend
                const signRes = await fetch('{{ url_for("get_upload_params") }}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: password })
                });
                const signData = await signRes.json();

                if (signData.status !== 'success') {
                    throw new Error(signData.message || 'Authentication failed!');
                }

                // Step 2: Direct Upload to Cloudinary (Bypasses Render completely - No Timeout)
                const formData = new FormData();
                formData.append('file', file);
                formData.append('api_key', signData.api_key);
                formData.append('timestamp', signData.timestamp);
                formData.append('signature', signData.signature);
                formData.append('eager', signData.eager);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', `https://api.cloudinary.com/v1_1/${signData.cloud_name}/video/upload`, true);

                xhr.upload.onprogress = function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        progressFill.style.width = percent + '%';
                        percentText.innerText = percent + '%';
                        const loadedMB = (e.loaded / (1024 * 1024)).toFixed(2);
                        const totalMB = (e.total / (1024 * 1024)).toFixed(2);
                        statusText.innerText = `Uploading: ${loadedMB} MB / ${totalMB} MB`;
                    }
                };

                xhr.onload = async function() {
                    if (xhr.status === 200) {
                        const cloudRes = JSON.parse(xhr.responseText);
                        procLabel.innerText = 'Saving...';
                        statusText.innerText = 'Upload 100%! Saving video to portal...';

                        // Step 3: Save metadata to website database
                        const saveRes = await fetch('{{ url_for("save_video") }}', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                password: password,
                                title: videoTitle,
                                public_id: cloudRes.public_id
                            })
                        });
                        const saveData = await saveRes.json();

                        if (saveData.status === 'success') {
                            alertBox.style.display = 'block';
                            alertBox.style.background = '#d1e7dd';
                            alertBox.style.color = '#0f5132';
                            alertBox.innerText = 'Video Uploaded and Saved Successfully!';
                            document.getElementById('uploadForm').reset();
                            statusText.innerText = 'Complete!';
                        } else {
                            throw new Error(saveData.message);
                        }
                    } else {
                        throw new Error('Cloud upload failed! Status: ' + xhr.status);
                    }
                    submitBtn.disabled = false;
                };

                xhr.onerror = function() {
                    throw new Error('Network error during upload to cloud.');
                };

                xhr.send(formData);

            } catch (err) {
                submitBtn.disabled = false;
                alertBox.style.display = 'block';
                alertBox.style.background = '#f8d7da';
                alertBox.style.color = '#721c24';
                alertBox.innerText = err.message;
                progressBox.style.display = 'none';
            }
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

@app.route("/admin")
def admin_panel():
    return render_template_string(ADMIN_PAGE)

@app.route("/get_upload_params", methods=["POST"])
def get_upload_params():
    data = request.get_json() or {}
    password = data.get("password", "")
    if password != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Incorrect Admin Password!"}), 403

    timestamp = int(time.time())
    eager_trans = "w_360,c_scale,q_auto:eco,fl_attachment"
    
    params_to_sign = {
        "timestamp": timestamp,
        "eager": eager_trans
    }
    signature = cloudinary.utils.api_sign_request(params_to_sign, CLOUDINARY_API_SECRET)

    return jsonify({
        "status": "success",
        "timestamp": timestamp,
        "signature": signature,
        "api_key": CLOUDINARY_API_KEY,
        "cloud_name": CLOUDINARY_CLOUD_NAME,
        "eager": eager_trans
    })

@app.route("/save_video", methods=["POST"])
def save_video():
    data = request.get_json() or {}
    password = data.get("password", "")
    title = data.get("title", "").strip()
    public_id = data.get("public_id", "").strip()

    if password != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Incorrect Admin Password!"}), 403

    if not title or not public_id:
        return jsonify({"status": "error", "message": "Title and public_id are required!"}), 400

    download_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/w_360,c_scale,q_auto:eco,fl_attachment/{public_id}.mp4"

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO videos (title, download_url, public_id) VALUES (?, ?, ?)",
        (title, download_url, public_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Video registered successfully!"})

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
