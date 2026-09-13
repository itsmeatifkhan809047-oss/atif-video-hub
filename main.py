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
            dl_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/{pub_id}.mp4"
            thumb_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/{pub_id}.jpg"
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
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamHub</title>
    <style>
        body { background-color: #0f172a; color: #ffffff; font-family: sans-serif; margin: 0; padding: 10px; }
        .nav-bar { background-color: #1e293b; padding: 10px; border-radius: 8px; margin-bottom: 12px; }
        .logo { font-size: 18px; font-weight: bold; color: #60a5fa; text-decoration: none; }
        .btn { display: inline-block; padding: 8px 12px; font-size: 12px; font-weight: bold; border-radius: 6px; text-decoration: none; border: none; cursor: pointer; text-align: center; }
        .btn-primary { background-color: #3b82f6; color: #ffffff; }
        .btn-sync { background-color: #334155; color: #cbd5e1; }
        .btn-rename { background-color: #f59e0b; color: #000000; }
        .btn-delete { background-color: #ef4444; color: #ffffff; }
        .btn-download { background-color: #10b981; color: #ffffff; display: block; width: 92%; margin: 6px auto; text-align: center; }
        .search-box { margin-bottom: 15px; }
        .search-input { width: 70%; padding: 8px; background-color: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 6px; }
        .card { background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; margin-bottom: 14px; overflow: hidden; }
        .thumb-wrapper { width: 100%; height: 180px; background-color: #000000; text-align: center; display: block; }
        .thumb-img { width: 100%; height: 180px; object-fit: cover; }
        .card-body { padding: 10px; }
        .card-title { font-size: 14px; font-weight: bold; margin-bottom: 8px; color: #f1f5f9; word-break: break-all; }
        .btn-grid { width: 100%; text-align: center; }
        .btn-grid td { width: 50%; padding: 2px; }
    </style>
</head>
<body>
    <div class="nav-bar">
        <table width="100%">
            <tr>
                <td><a href="{{ url_for('home') }}" class="logo">▶ StreamHub</a></td>
                <td align="right">
                    <a href="{{ url_for('sync_videos') }}" class="btn btn-sync">Sync</a>
                    <a href="{{ url_for('admin_panel') }}" class="btn btn-primary">+ Upload</a>
                </td>
            </tr>
        </table>
    </div>

    <form method="GET" action="{{ url_for('home') }}" class="search-box">
        <input type="text" name="q" value="{{ query }}" placeholder="Search..." class="search-input">
        <button type="submit" class="btn btn-primary">Search</button>
    </form>

    <div>
        {% for vid in videos %}
        <div class="card">
            <div class="thumb-wrapper">
                <img src="{{ vid[4] }}" class="thumb-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding-top:70px; color:#60a5fa; font-weight:bold;">▶ MP4 VIDEO</div>
            </div>
            <div class="card-body">
                <div class="card-title">{{ vid[1] }}</div>
                <a href="{{ vid[2] }}" class="btn btn-download" target="_blank">↓ Download MP4</a>
                <table class="btn-grid">
                    <tr>
                        <td><a href="{{ url_for('rename_video', video_id=vid[0]) }}" class="btn btn-rename" style="display:block;">Rename</a></td>
                        <td><a href="{{ url_for('delete_video', video_id=vid[0]) }}" class="btn btn-delete" style="display:block;">Delete</a></td>
                    </tr>
                </table>
            </div>
        </div>
        {% else %}
        <p style="text-align: center; color: #94a3b8; padding: 20px;">No videos found.</p>
        {% endfor %}
    </div>

    <div style="text-align: center; margin-top: 15px;">
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
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Center</title>
    <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-storage-compat.js"></script>
    <style>
        body { background: #0f172a; color: #fff; font-family: sans-serif; padding: 15px; }
        .box { background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }
        input[type="text"], input[type="password"], input[type="file"] { width: 92%; padding: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; margin-bottom: 12px; border-radius: 6px; }
        .btn-submit { width: 98%; padding: 10px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="box">
        <h3 style="color:#60a5fa; text-align:center;">Upload Media</h3>
        <div id="alert" style="display:none; color:red; margin-bottom:10px;"></div>
        <form id="upForm">
            <label>Select Video:</label><br>
            <input type="file" id="file" accept="video/*" required><br>
            <label>Title:</label><br>
            <input type="text" id="title" required><br>
            <label>Password:</label><br>
            <input type="password" id="pass" required><br>
            <button type="button" class="btn-submit" onclick="processUpload()">Start Upload</button>
        </form>
        <div id="stText" style="margin-top:10px; color:#10b981; font-weight:bold;"></div>
        <br>
        <a href="{{ url_for('home') }}" style="color:#94a3b8;">&larr; Back</a>
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
            const stText = document.getElementById('stText');
            const alert = document.getElementById('alert');

            if (!file || !title || !pass) return;
            alert.style.display = 'none';

            if (file.size > 95 * 1024 * 1024) {
                stText.innerText = "Uploading to Firebase...";
                const ref = firebase.storage().ref('videos/' + Date.now() + '_' + file.name);
                const task = ref.put(file);

                task.on('state_changed', 
                    s => { stText.innerText = "Uploading: " + Math.round((s.bytesTransferred / s.totalBytes) * 100) + "%"; },
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
                stText.innerText = "Uploading to Cloudinary...";
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

                let xhr = new XMLHttpRequest();
                xhr.open('POST', `https://api.cloudinary.com/v1_1/${sign.cloud_name}/video/upload`, true);
                xhr.upload.onprogress = e => {
                    stText.innerText = "Uploading: " + Math.round((e.loaded / e.total) * 100) + "%";
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
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confirm Action</title>
    <style>
        body { background: #0f172a; color: #fff; font-family: sans-serif; padding: 20px; text-align: center; }
        .card { background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }
        input { width: 90%; padding: 8px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; margin: 10px 0; }
        .btn-act { width: 95%; padding: 10px; border: none; border-radius: 6px; font-weight: bold; background: #3b82f6; color: #fff; }
    </style>
</head>
<body>
    <div class="card">
        <h3>Confirm Action</h3>
        <p>{{ video[1] }}</p>
        {% with messages = get_flashed_messages() %}
            {% if messages %}<p style="color: #ef4444;">{{ messages[0] }}</p>{% endif %}
        {% endwith %}
        <form method="POST">
            {% if action == 'rename' %}
                <input type="text" name="new_name" value="{{ video[1] }}" required>
            {% endif %}
            <input type="password" name="password" placeholder="Admin Password" required><br>
            <button type="submit" class="btn-act">Confirm</button>
        </form>
        <br>
        <a href="{{ url_for('home') }}" style="color: #94a3b8;">Cancel</a>
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
        return jsonify({"status": "error", "message": "Incorrect Password!"}), 403

    timestamp = int(time.time())
    params_to_sign = {"timestamp": timestamp}
    signature = cloudinary.utils.api_sign_request(params_to_sign, CLOUDINARY_API_SECRET)

    return jsonify({
        "status": "success",
        "timestamp": timestamp,
        "signature": signature,
        "api_key": CLOUDINARY_API_KEY,
        "cloud_name": CLOUDINARY_CLOUD_NAME
    })

@app.route("/save_video", methods=["POST"])
def save_video():
    data = request.get_json() or {}
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid password"}), 403

    title = data.get("title", "").strip()
    public_id = data.get("public_id", "").strip()
    
    download_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/{public_id}.mp4"
    thumb_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/video/upload/{public_id}.jpg"

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

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO videos (title, download_url, public_id, storage_type, thumb_url) VALUES (?, ?, ?, 'firebase', '')", (title, download_url, public_id))
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
