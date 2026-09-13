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

FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "YOUR_FIREBASE_API_KEY")
FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "your-app.firebaseapp.com")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "your-app-id")
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "your-app.appspot.com")
FIREBASE_MESSAGING_SENDER_ID = os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "123456789")
FIREBASE_APP_ID = os.environ.get("FIREBASE_APP_ID", "1:123456:web:abcd")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

app = Flask(__name__)
app.secret_key = "jiobharat_opera_super_secret_key"
DB_NAME = "videos.db"

# ================= DATABASE SETUP =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            download_url TEXT NOT NULL,
            public_id TEXT NOT NULL UNIQUE,
            storage_type TEXT DEFAULT 'cloudinary',
            thumb_url TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def sync_from_cloudinary():
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
            dl_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/fl_attachment/{pub_id}.mp4"
            thumb_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/so_0,w_480,h_270,c_fill,f_jpg/{pub_id}.jpg"
            clean_title = pub_id.split("/")[-1].replace("_", " ").replace("-", " ")
            
            cur.execute("""
                INSERT OR IGNORE INTO videos (title, download_url, public_id, storage_type, thumb_url)
                VALUES (?, ?, ?, 'cloudinary', ?)
            """, (clean_title, dl_url, pub_id, thumb_url))
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cloudinary sync error: {e}")

init_db()
sync_from_cloudinary()

# ================= UI TEMPLATES =================

HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamHub - Video Portal</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #3b82f6; --danger: #ef4444; --warning: #f59e0b; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 12px; }
        .nav-bar { display: flex; justify-content: space-between; align-items: center; background: var(--card); padding: 12px 16px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .logo { font-size: 18px; font-weight: 800; color: #60a5fa; text-decoration: none; }
        .nav-btns { display: flex; gap: 8px; }
        .btn { padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px; text-decoration: none; border: none; cursor: pointer; transition: 0.2s ease; display: inline-flex; align-items: center; justify-content: center; }
        .btn-primary { background: var(--accent); color: #fff; }
        .btn-sync { background: #334155; color: #cbd5e1; }
        .btn-rename { background: var(--warning); color: #000; flex: 1; }
        .btn-delete { background: var(--danger); color: #fff; flex: 1; }
        .btn-download { background: #10b981; color: #fff; width: 100%; font-size: 14px; margin-bottom: 8px; }
        .search-box { display: flex; gap: 8px; margin-bottom: 20px; }
        .search-input { flex: 1; padding: 10px 14px; background: var(--card); border: 1px solid #334155; color: #fff; border-radius: 8px; font-size: 14px; outline: none; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
        .card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; display: flex; flex-direction: column; }
        .thumb-wrapper { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; overflow: hidden; }
        .thumb-img { width: 100%; height: 100%; object-fit: cover; }
        .card-body { padding: 12px; display: flex; flex-direction: column; flex: 1; }
        .card-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; line-height: 1.4; color: #f1f5f9; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; height: 38px; }
        .actions { display: flex; gap: 8px; margin-top: auto; }
        .pagination { display: flex; justify-content: center; gap: 10px; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="nav-bar">
        <a href="{{ url_for('home') }}" class="logo">▶ StreamHub</a>
        <div class="nav-btns">
            <a href="{{ url_for('sync_videos') }}" class="btn btn-sync">Sync</a>
            <a href="{{ url_for('admin_panel') }}" class="btn btn-primary">+ Upload</a>
        </div>
    </div>

    <form method="GET" action="{{ url_for('home') }}" class="search-box">
        <input type="text" name="q" value="{{ query }}" placeholder="Search videos..." class="search-input">
        <button type="submit" class="btn btn-primary">Search</button>
    </form>

    <div class="grid">
        {% for vid in videos %}
        <div class="card">
            <div class="thumb-wrapper">
                {% if vid[4] and vid[4] != '' %}
                    <img src="{{ vid[4] }}" class="thumb-img" onerror="this.onerror=null; this.src='https://via.placeholder.com/480x270/0f172a/60a5fa?text=Video+File';">
                {% else %}
                    <div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:#0284c7; color:#fff; font-weight:bold;">▶ MP4 Video</div>
                {% endif %}
            </div>
            <div class="card-body">
                <div class="card-title">{{ vid[1] }}</div>
                <a href="{{ vid[2] }}" class="btn btn-download" target="_blank" download>↓ Download MP4</a>
                <div class="actions">
                    <a href="{{ url_for('rename_video', video_id=vid[0]) }}" class="btn btn-rename">Rename</a>
                    <a href="{{ url_for('delete_video', video_id=vid[0]) }}" class="btn btn-delete">Delete</a>
                </div>
            </div>
        </div>
        {% else %}
        <p style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 40px 0;">No videos found.</p>
        {% endfor %}
    </div>

    <div class="pagination">
        {% if page > 1 %}
            <a href="{{ url_for('home', page=page-1, q=query) }}" class="btn btn-sync">&laquo; Prev</a>
        {% endif %}
        {% if has_next %}
            <a href="{{ url_for('home', page=page+1, q=query) }}" class="btn btn-sync">Next &raquo;</a>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Center</title>
    <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-storage-compat.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #fff; margin: 0; padding: 16px; display: flex; justify-content: center; align-items: center; min-height: 90vh; }
        .box { background: #1e293b; border-radius: 12px; padding: 24px; width: 100%; max-width: 440px; border: 1px solid #334155; }
        h3 { margin-top: 0; color: #60a5fa; text-align: center; font-size: 20px; }
        .field { margin-bottom: 16px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #cbd5e1; }
        input[type="text"], input[type="password"], input[type="file"] { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #fff; box-sizing: border-box; font-size: 14px; }
        .btn-submit { width: 100%; padding: 12px; background: #3b82f6; color: #fff; border: none; border-radius: 8px; font-weight: bold; font-size: 15px; cursor: pointer; }
        .progress-box { display: none; margin-top: 16px; background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155; }
        .track { background: #334155; height: 10px; border-radius: 5px; overflow: hidden; margin-top: 8px; }
        .fill { background: #10b981; height: 100%; width: 0%; transition: width 0.2s; }
        .alert { display: none; padding: 10px; border-radius: 8px; font-size: 13px; margin-bottom: 12px; text-align: center; }
        .back-link { display: block; text-align: center; color: #94a3b8; text-decoration: none; font-size: 13px; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="box">
        <h3>Upload Media</h3>
        <div id="alert" class="alert"></div>
        <form id="upForm">
            <div class="field">
                <label>Select Video</label>
                <input type="file" id="file" accept="video/*" required>
            </div>
            <div class="field">
                <label>Video Title</label>
                <input type="text" id="title" placeholder="My Awesome Video" required>
            </div>
            <div class="field">
                <label>Admin Password</label>
                <input type="password" id="pass" placeholder="••••••••" required>
            </div>
            <button type="button" id="subBtn" class="btn-submit" onclick="processUpload()">Start Upload</button>
        </form>

        <div id="pBox" class="progress-box">
            <div style="display:flex; justify-content:space-between; font-size:12px;">
                <span id="stText">Uploading...</span>
                <span id="pText">0%</span>
            </div>
            <div class="track"><div id="pFill" class="fill"></div></div>
        </div>

        <a href="{{ url_for('home') }}" class="back-link">&larr; Back to Portal</a>
    </div>

    <script>
        const firebaseConfig = {
            apiKey: "{{ fb_config.apiKey }}",
            authDomain: "{{ fb_config.authDomain }}",
            projectId: "{{ fb_config.projectId }}",
            storageBucket: "{{ fb_config.storageBucket }}",
            messagingSenderId: "{{ fb_config.messagingSenderId }}",
            appId: "{{ fb_config.appId }}"
        };

        if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);

        async function processUpload() {
            const file = document.getElementById('file').files[0];
            const title = document.getElementById('title').value.trim();
            const pass = document.getElementById('pass').value.trim();
            const alert = document.getElementById('alert');
            const pBox = document.getElementById('pBox');
            const pFill = document.getElementById('pFill');
            const pText = document.getElementById('pText');
            const stText = document.getElementById('stText');

            if (!file || !title || !pass) return;

            pBox.style.display = 'block';
            alert.style.display = 'none';

            if (file.size > 95 * 1024 * 1024) {
                stText.innerText = "Direct Firebase Upload (>95MB)...";
                const ref = firebase.storage().ref('videos/' + Date.now() + '_' + file.name);
                const task = ref.put(file);

                task.on('state_changed', 
                    s => {
                        let pct = Math.round((s.bytesTransferred / s.totalBytes) * 100);
                        pFill.style.width = pct + '%';
                        pText.innerText = pct + '%';
                    },
                    e => { alert.innerText = e.message; alert.style.display = 'block'; },
                    async () => {
                        let url = await task.snapshot.ref.getDownloadURL();
                        let res = await fetch('{{ url_for("save_firebase_video") }}', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ password: pass, title: title, download_url: url, public_id: ref.fullPath })
                        });
                        let d = await res.json();
                        if(d.status === 'success') location.href = '{{ url_for("home") }}';
                    }
                );
            } else {
                stText.innerText = "Cloudinary Upload...";
                let signRes = await fetch('{{ url_for("get_upload_params") }}', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ password: pass })
                });
                let sign = await signRes.json();
                if(sign.status !== 'success') { alert.innerText = sign.message; alert.style.display = 'block'; return; }

                let fd = new FormData();
                fd.append('file', file);
                fd.append('api_key', sign.api_key);
                fd.append('timestamp', sign.timestamp);
                fd.append('signature', sign.signature);
                fd.append('eager', sign.eager);

                let xhr = new XMLHttpRequest();
                xhr.open('POST', `https://api.cloudinary.com/v1_1/${sign.cloud_name}/video/upload`, true);
                xhr.upload.onprogress = e => {
                    let pct = Math.round((e.loaded / e.total) * 100);
                    pFill.style.width = pct + '%';
                    pText.innerText = pct + '%';
                };
                xhr.onload = async () => {
                    if(xhr.status === 200) {
                        let cData = JSON.parse(xhr.responseText);
                        await fetch('{{ url_for("save_video") }}', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ password: pass, title: title, public_id: cData.public_id })
                        });
                        location.href = '{{ url_for("home") }}';
                    }
                };
                xhr.send(fd);
            }
        }
    </script>
</body>
</html>
"""

CONFIRM_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ action|title }} Action</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #fff; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 80vh; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; width: 100%; max-width: 340px; border: 1px solid #334155; text-align: center; }
        input { width: 100%; padding: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 8px; margin: 10px 0; box-sizing: border-box; }
        .btn-act { width: 100%; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; background: #3b82f6; color: #fff; }
    </style>
</head>
<body>
    <div class="card">
        <h3>Confirm {{ action|title }}</h3>
        <p style="font-size: 14px; color: #94a3b8;">{{ video[1] }}</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<p style="color: #ef4444; font-size: 13px;">{{ messages[0] }}</p>{% endif %}
        {% endwith %}
        <form method="POST">
            {% if action == 'rename' %}
                <input type="text" name="new_name" value="{{ video[1] }}" required>
            {% endif %}
            <input type="password" name="password" placeholder="Admin Password" required>
            <button type="submit" class="btn-act">Confirm</button>
        </form>
        <br>
        <a href="{{ url_for('home') }}" style="color: #64748b; font-size: 13px; text-decoration: none;">Cancel</a>
    </div>
</body>
</html>
"""

# ================= ROUTES =================

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    limit = 12
    offset = (page - 1) * limit

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    if query:
        cur.execute("SELECT id, title, download_url, public_id, thumb_url, storage_type FROM videos WHERE title LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?", (f"%{query}%", limit + 1, offset))
    else:
        cur.execute("SELECT id, title, download_url, public_id, thumb_url, storage_type FROM videos ORDER BY id DESC LIMIT ? OFFSET ?", (limit + 1, offset))

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
    fb_config = {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID
    }
    return render_template_string(ADMIN_PAGE, fb_config=fb_config)

@app.route("/get_upload_params", methods=["POST"])
def get_upload_params():
    data = request.get_json() or {}
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Incorrect Admin Password!"}), 403

    timestamp = int(time.time())
    eager_trans = "so_0,w_480,h_270,c_fill,f_jpg"
    params_to_sign = {"timestamp": timestamp, "eager": eager_trans}
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
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid password"}), 403

    title = data.get("title", "").strip()
    public_id = data.get("public_id", "").strip()
    
    download_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/fl_attachment/{public_id}.mp4"
    thumb_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/so_0,w_480,h_270,c_fill,f_jpg/{public_id}.jpg"

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO videos (title, download_url, public_id, storage_type, thumb_url) VALUES (?, ?, ?, 'cloudinary', ?)", (title, download_url, public_id, thumb_url))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/save_firebase_video", methods=["POST"])
def save_firebase_video():
    data = request.get_json() or {}
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid password"}), 403

    title = data.get("title", "").strip()
    download_url = data.get("download_url", "").strip()
    public_id = data.get("public_id", "").strip()

    thumb_url = ""

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO videos (title, download_url, public_id, storage_type, thumb_url) VALUES (?, ?, ?, 'firebase', ?)", (title, download_url, public_id, thumb_url))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/rename/<int:video_id>", methods=["GET", "POST"])
def rename_video(video_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video: return redirect(url_for("home"))

    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            flash("Invalid Password!")
            return render_template_string(CONFIRM_PAGE, video=video, action="rename")

        new_name = request.form.get("new_name", "").strip()
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
    cur.execute("SELECT id, title, public_id, storage_type FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()
    conn.close()

    if not video: return redirect(url_for("home"))

    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            flash("Invalid Password!")
            return render_template_string(CONFIRM_PAGE, video=video, action="delete")

        if video[3] == "cloudinary":
            try: cloudinary.uploader.destroy(video[2], resource_type="video")
            except Exception as e: print(e)

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template_string(CONFIRM_PAGE, video=video, action="delete")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
