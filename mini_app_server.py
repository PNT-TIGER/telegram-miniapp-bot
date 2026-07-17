import json, os, logging, uuid, threading
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "posts.json"
UPLOAD_DIR = "uploads"
TOKEN = "8992436164:AAGRoWbsfsw54LL4vBnt7wOaPXtHUmuYg0Y"

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

def download_telegram_file(file_id, filename):
    r = http_requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}")
    if r.status_code != 200:
        return None
    path = r.json()["result"]["file_path"]
    dl = http_requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{path}")
    if dl.status_code != 200:
        return None
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(dl.content)
    return filename

@app.route("/")
def index():
    return send_from_directory("templates", "mini_app.html")

@app.route("/uploads/<name>")
def uploaded_file(name):
    return send_from_directory(UPLOAD_DIR, name)

@app.route("/api/posts")
def get_posts():
    data = load_data()
    posts = []
    for p in data["posts"]:
        posts.append({
            "id": p["id"],
            "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
            "click_required": p.get("click_required", 5),
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
                "click_required": p.get("click_required", 5),
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
            p["views"] = p.get("views", 0) + 1
            viewers = p.setdefault("viewers", [])
            if user_id not in viewers:
                viewers.append(user_id)
                p["views"] = len(viewers)
            save_data(data)
            return jsonify({"views": p["views"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/task/<post_id>/click", methods=["POST"])
def task_click(post_id):
    data = load_data()
    user_id = str(request.json.get("user_id", "unknown"))
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.setdefault("clicks", {})
            current = clicks.get(user_id, 0)
            required = p.get("click_required", 5)
            if current >= required:
                return jsonify({"done": True, "completed": True, "remaining": 0})
            current += 1
            clicks[user_id] = current
            save_data(data)
            remaining = required - current
            return jsonify({
                "done": current >= required,
                "completed": current >= required,
                "remaining": remaining,
                "total": required
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/user/<user_id>/click_status/<post_id>")
def click_status(user_id, post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.get("clicks", {})
            current = clicks.get(user_id, 0)
            required = p.get("click_required", 5)
            return jsonify({
                "completed": current >= required,
                "remaining": required - current,
                "total": required
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/config")
def get_config():
    data = load_data()
    return jsonify(data.get("config", {}))

@app.route("/api/config", methods=["POST"])
def set_config():
    data = load_data()
    data["config"] = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/posts", methods=["POST"])
def create_post():
    data = load_data()
    body = request.json
    post = {
        "id": str(uuid.uuid4())[:8],
        "photo": body.get("photo", ""),
        "link": body.get("link", ""),
        "click_required": body.get("click_required", 5),
        "views": 0,
        "viewers": [],
        "clicks": {},
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["posts"].insert(0, post)
    save_data(data)
    return jsonify({"ok": True, "id": post["id"]})

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_flask()
