import json, os, logging, uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "posts.json"
UPLOAD_DIR = "uploads"
TOKEN = "8992436164:AAGRoWbsfsw54LL4vBnt7wOaPXtHUmuYg0Y"
ADMIN_PASS = "admin"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

def load_data():
    default = {"posts": [], "config": {"channel_link": ""}}
    if not os.path.exists(DATA_FILE):
        return default
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def check_admin():
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {ADMIN_PASS}"

@app.route("/")
def index():
    return send_from_directory("templates", "mini_app.html")

@app.route("/admin")
def admin_page():
    return send_from_directory("templates", "admin.html")

@app.route("/uploads/<name>")
def uploaded_file(name):
    return send_from_directory(UPLOAD_DIR, name)

@app.route("/api/admin/check", methods=["POST"])
def admin_check():
    pwd = request.json.get("password", "")
    return jsonify({"ok": pwd == ADMIN_PASS})

@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    if not check_admin():
        return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    link = request.form.get("link", "")
    file = request.files.get("photo")

    if not file or not link:
        return jsonify({"error": "photo and link required"}), 400

    fname = f"{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(UPLOAD_DIR, fname)
    file.save(filepath)

    post = {
        "id": uuid.uuid4().hex[:8],
        "photo": fname,
        "link": link,
        "views": 0,
        "viewers": [],
        "clicks": {},
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["posts"].insert(0, post)
    save_data(data)
    return jsonify({"ok": True, "id": post["id"], "photo": f"/uploads/{fname}"})

@app.route("/api/admin/post/<post_id>", methods=["DELETE"])
def admin_delete_post(post_id):
    if not check_admin():
        return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    idx = None
    for i, p in enumerate(data["posts"]):
        if p["id"] == post_id:
            idx = i
            break
    if idx is None:
        return jsonify({"error": "not found"}), 404
    removed = data["posts"].pop(idx)
    save_data(data)
    if removed.get("photo"):
        try: os.remove(os.path.join(UPLOAD_DIR, removed["photo"]))
        except: pass
    return jsonify({"ok": True})

@app.route("/api/admin/config", methods=["POST"])
def admin_set_config():
    if not check_admin():
        return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    data["config"] = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/posts")
def get_posts():
    data = load_data()
    posts = []
    for p in data["posts"]:
        posts.append({
            "id": p["id"],
            "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
            "views": p.get("views", 0),
            "date": p.get("date", ""),
            "link": p.get("link", ""),
        })
    return jsonify(posts)

@app.route("/api/post/<post_id>")
def get_post(post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            return jsonify({
                "id": p["id"],
                "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
                "link": p.get("link", ""),
                "views": p.get("views", 0),
                "date": p.get("date", ""),
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/view/<post_id>", methods=["POST"])
def view_post(post_id):
    data = load_data()
    user_id = request.json.get("user_id", "unknown")
    for p in data["posts"]:
        if p["id"] == post_id:
            viewers = p.setdefault("viewers", [])
            if user_id not in viewers:
                viewers.append(user_id)
                p["views"] = len(viewers)
            save_data(data)
            return jsonify({"views": p["views"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/config")
def get_config():
    data = load_data()
    return jsonify(data.get("config", {}))

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_flask()
