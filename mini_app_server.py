import json, os, logging, uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "posts.json"
UPLOAD_DIR = "uploads"
TOKEN = "8867263661:AAFVGrC_GN-IUNOzaXCBUHMo9JiKyXTw53Q"
ADMIN_PASS = "admin"

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "*"
    return resp

def load_data():
    default = {"posts": [], "users": {}, "config": {}}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def check_admin():
    return request.headers.get("Authorization", "") == f"Bearer {ADMIN_PASS}"

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
    return jsonify({"ok": request.json.get("password", "") == ADMIN_PASS})

@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    if not check_admin():
        return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    title = request.form.get("title", "Untitled")
    link = request.form.get("link", "")
    unlock_req = int(request.form.get("unlock_required", 4))
    file = request.files.get("photo")
    image_url = request.form.get("image_url", "")

    if not link:
        return jsonify({"error": "link required"}), 400

    fname = ""
    if file and file.filename:
        fname = f"{uuid.uuid4().hex[:8]}.jpg"
        file.save(os.path.join(UPLOAD_DIR, fname))
    elif image_url:
        try:
            r = http_requests.get(image_url, timeout=10)
            if r.status_code == 200:
                ext = "jpg"
                ct = r.headers.get("content-type", "")
                if "png" in ct: ext = "png"
                elif "gif" in ct: ext = "gif"
                elif "webp" in ct: ext = "webp"
                fname = f"{uuid.uuid4().hex[:8]}.{ext}"
                with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
                    f.write(r.content)
            else:
                return jsonify({"error": "download failed"}), 400
        except:
            return jsonify({"error": "invalid URL"}), 400
    else:
        return jsonify({"error": "photo required"}), 400

    post = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "photo": fname,
        "link": link,
        "unlock_required": unlock_req,
        "views": 0, "viewers": [], "downloads": 0,
        "likes": [], "favorites": [], "unlock_clicks": {},
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["posts"].insert(0, post)
    save_data(data)
    return jsonify({"ok": True, "id": post["id"]})

@app.route("/api/admin/post/<post_id>", methods=["DELETE"])
def admin_delete_post(post_id):
    if not check_admin():
        return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    for i, p in enumerate(data["posts"]):
        if p["id"] == post_id:
            if p.get("photo"):
                try: os.remove(os.path.join(UPLOAD_DIR, p["photo"]))
                except: pass
            data["posts"].pop(i)
            save_data(data)
            return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404

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
    out = []
    for p in data["posts"]:
        out.append({
            "id": p["id"], "title": p.get("title", "Untitled"),
            "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
            "link": p.get("link", ""),
            "unlock_required": p.get("unlock_required", 4),
            "views": p.get("views", 0), "downloads": p.get("downloads", 0),
            "likes": len(p.get("likes", [])), "favorites": len(p.get("favorites", [])),
            "date": p.get("date", ""),
        })
    return jsonify(out)

@app.route("/api/post/<post_id>")
def get_post(post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            return jsonify({
                "id": p["id"], "title": p.get("title", "Untitled"),
                "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
                "link": p.get("link", ""),
                "unlock_required": p.get("unlock_required", 4),
                "views": p.get("views", 0), "downloads": p.get("downloads", 0),
                "likes": len(p.get("likes", [])), "favorites": len(p.get("favorites", [])),
                "date": p.get("date", ""),
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/view/<post_id>", methods=["POST"])
def view_post(post_id):
    data = load_data()
    uid = request.json.get("user_id", "unknown")
    for p in data["posts"]:
        if p["id"] == post_id:
            viewers = p.setdefault("viewers", [])
            if uid not in viewers:
                viewers.append(uid)
                p["views"] = len(viewers)
            save_data(data)
            return jsonify({"views": p["views"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/like/<post_id>", methods=["POST"])
def like_post(post_id):
    data = load_data()
    uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            likes = p.setdefault("likes", [])
            if uid in likes: likes.remove(uid)
            else: likes.append(uid)
            save_data(data)
            return jsonify({"likes": len(likes), "liked": uid in likes})
    return jsonify({"error": "not found"}), 404

@app.route("/api/favorite/<post_id>", methods=["POST"])
def fav_post(post_id):
    data = load_data()
    uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            favs = p.setdefault("favorites", [])
            if uid in favs: favs.remove(uid)
            else: favs.append(uid)
            save_data(data)
            return jsonify({"favorites": len(favs), "favorited": uid in favs})
    return jsonify({"error": "not found"}), 404

@app.route("/api/download/<post_id>", methods=["POST"])
def download_post(post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            p["downloads"] = p.get("downloads", 0) + 1
            save_data(data)
            return jsonify({"downloads": p["downloads"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/unlock_click/<post_id>", methods=["POST"])
def unlock_click(post_id):
    data = load_data()
    uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.setdefault("unlock_clicks", {})
            current = clicks.get(uid, 0)
            required = p.get("unlock_required", 4)
            if current >= required:
                return jsonify({"done": True, "remaining": 0})
            current += 1
            clicks[uid] = current
            save_data(data)
            return jsonify({"done": current >= required, "remaining": required - current, "total": required})
    return jsonify({"error": "not found"}), 404

@app.route("/api/user/<user_id>/status/<post_id>")
def user_post_status(user_id, post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.get("unlock_clicks", {})
            c = clicks.get(str(user_id), 0)
            r = p.get("unlock_required", 4)
            liked = str(user_id) in p.get("likes", [])
            faved = str(user_id) in p.get("favorites", [])
            return jsonify({"remaining": r - c, "total": r, "done": c >= r, "liked": liked, "favorited": faved})
    return jsonify({"error": "not found"}), 404

@app.route("/api/user/<uid>", methods=["GET"])
def get_user(uid):
    data = load_data()
    u = data["users"].get(str(uid), {"wallet": 0, "premium": False, "join_date": datetime.now().strftime("%Y-%m-%d"), "redeemed": []})
    favs = []
    for p in data["posts"]:
        if str(uid) in p.get("favorites", []):
            favs.append(p["id"])
    return jsonify({"wallet": u.get("wallet", 0), "premium": u.get("premium", False), "join_date": u.get("join_date", ""), "favorites": favs})

@app.route("/api/user/<uid>", methods=["POST"])
def update_user(uid):
    data = load_data()
    data["users"][str(uid)] = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/redeem", methods=["POST"])
def redeem_code():
    code = request.json.get("code", "").strip().upper()
    if code == "VIP2024":
        return jsonify({"ok": True, "amount": 100, "msg": "🎉 100 coins added!"})
    return jsonify({"ok": False, "msg": "Invalid code"})

@app.route("/api/config")
def get_config():
    data = load_data()
    return jsonify(data.get("config", {}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
