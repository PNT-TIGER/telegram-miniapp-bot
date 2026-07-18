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
    default = {"posts": [], "gift_codes": [], "users": {}, "config": {}}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def check_admin():
    return request.headers.get("Authorization", "") == f"Bearer {ADMIN_PASS}"

def save_upload(file_obj):
    ext = file_obj.filename.rsplit(".", 1)[-1] if "." in file_obj.filename else "jpg"
    fname = f"{uuid.uuid4().hex[:8]}.{ext}"
    file_obj.save(os.path.join(UPLOAD_DIR, fname))
    return fname

def save_upload_url(url):
    try:
        r = http_requests.get(url, timeout=10)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            ext = "jpg"
            if "png" in ct: ext = "png"
            elif "gif" in ct: ext = "gif"
            elif "webp" in ct: ext = "webp"
            elif "mp4" in ct: ext = "mp4"
            elif "pdf" in ct: ext = "pdf"
            elif "zip" in ct: ext = "zip"
            fname = f"{uuid.uuid4().hex[:8]}.{ext}"
            with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
                f.write(r.content)
            return fname
    except: pass
    return None

@app.route("/")
def index():
    return send_from_directory("templates", "mini_app.html")

@app.route("/admin")
def admin_page():
    return send_from_directory("templates", "admin.html")

@app.route("/uploads/<name>")
def uploaded_file(name):
    return send_from_directory(UPLOAD_DIR, name)

# === AUTH ===
@app.route("/api/admin/check", methods=["POST"])
def admin_check():
    return jsonify({"ok": request.json.get("password", "") == ADMIN_PASS})

# === POSTS ===
@app.route("/api/posts", methods=["GET"])
def get_posts():
    data = load_data()
    cat = request.args.get("cat", "")
    out = []
    for p in data["posts"]:
        if cat and p.get("category", "").lower() != cat.lower():
            continue
        out.append({
            "id": p["id"], "title": p.get("title", "Untitled"),
            "description": p.get("description", ""),
            "category": p.get("category", "others"),
            "tags": p.get("tags", ""),
            "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
            "file_type": p.get("file_type", "link"),
            "file_url": p.get("file_url", ""),
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
                "id": p["id"], "title": p.get("title", ""),
                "description": p.get("description", ""),
                "category": p.get("category", ""),
                "tags": p.get("tags", ""),
                "photo": f"/uploads/{p['photo']}" if p.get("photo") else None,
                "file_type": p.get("file_type", ""),
                "file_url": p.get("file_url", ""),
                "link": p.get("link", ""),
                "unlock_required": p.get("unlock_required", 4),
                "views": p.get("views", 0), "downloads": p.get("downloads", 0),
                "likes": len(p.get("likes", [])), "favorites": len(p.get("favorites", [])),
                "date": p.get("date", ""),
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/admin/post", methods=["POST"])
def admin_create_post():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    title = request.form.get("title", "Untitled")
    description = request.form.get("description", "")
    category = request.form.get("category", "others")
    tags = request.form.get("tags", "")
    link = request.form.get("link", "")
    unlock_req = int(request.form.get("unlock_required", 4))
    file_type = request.form.get("file_type", "link")
    image_url = request.form.get("image_url", "")
    file_obj = request.files.get("file")
    file_upl = request.files.get("upload_file")

    fname = ""
    if file_obj and file_obj.filename:
        fname = save_upload(file_obj)
    elif file_upl and file_upl.filename:
        fname = save_upload(file_upl)
    elif image_url:
        fname = save_upload_url(image_url)

    if not fname and file_type in ("video","image","apk","zip","pdf"):
        fname = ""

    post = {
        "id": uuid.uuid4().hex[:8],
        "title": title, "description": description,
        "category": category, "tags": tags,
        "photo": fname, "file_type": file_type, "file_url": "",
        "link": link, "unlock_required": unlock_req,
        "views": 0, "viewers": [], "downloads": 0,
        "likes": [], "favorites": [], "unlock_clicks": {},
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["posts"].insert(0, post)
    save_data(data)
    return jsonify({"ok": True, "id": post["id"]})

@app.route("/api/admin/post/<post_id>", methods=["PUT"])
def admin_update_post(post_id):
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            for k in ["title","description","category","tags","link"]:
                v = request.form.get(k)
                if v: p[k] = v
            v = request.form.get("unlock_required")
            if v: p["unlock_required"] = int(v)
            file_obj = request.files.get("file") or request.files.get("upload_file")
            if file_obj and file_obj.filename:
                if p.get("photo"):
                    try: os.remove(os.path.join(UPLOAD_DIR, p["photo"]))
                    except: pass
                p["photo"] = save_upload(file_obj)
            save_data(data)
            return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404

@app.route("/api/admin/post/<post_id>", methods=["DELETE"])
def admin_delete_post(post_id):
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
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

# === INTERACTIONS ===
@app.route("/api/view/<post_id>", methods=["POST"])
def view_post(post_id):
    data = load_data(); uid = request.json.get("user_id", "unknown")
    for p in data["posts"]:
        if p["id"] == post_id:
            viewers = p.setdefault("viewers", [])
            if uid not in viewers: viewers.append(uid); p["views"] = len(viewers)
            save_data(data); return jsonify({"views": p["views"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/like/<post_id>", methods=["POST"])
def like_post(post_id):
    data = load_data(); uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            likes = p.setdefault("likes", [])
            if uid in likes: likes.remove(uid)
            else: likes.append(uid)
            save_data(data); return jsonify({"likes": len(likes), "liked": uid in likes})
    return jsonify({"error": "not found"}), 404

@app.route("/api/favorite/<post_id>", methods=["POST"])
def fav_post(post_id):
    data = load_data(); uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            favs = p.setdefault("favorites", [])
            if uid in favs: favs.remove(uid)
            else: favs.append(uid)
            save_data(data); return jsonify({"favorites": len(favs), "favorited": uid in favs})
    return jsonify({"error": "not found"}), 404

@app.route("/api/download/<post_id>", methods=["POST"])
def download_post(post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            p["downloads"] = p.get("downloads", 0) + 1
            save_data(data); return jsonify({"downloads": p["downloads"]})
    return jsonify({"error": "not found"}), 404

@app.route("/api/unlock_click/<post_id>", methods=["POST"])
def unlock_click(post_id):
    data = load_data(); uid = str(request.json.get("user_id", ""))
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.setdefault("unlock_clicks", {})
            current = clicks.get(uid, 0)
            required = p.get("unlock_required", 4)
            if current >= required:
                return jsonify({"done": True, "remaining": 0})
            current += 1; clicks[uid] = current
            save_data(data)
            return jsonify({"done": current >= required, "remaining": required - current, "total": required})
    return jsonify({"error": "not found"}), 404

@app.route("/api/user/<uid>/status/<post_id>")
def user_post_status(uid, post_id):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            clicks = p.get("unlock_clicks", {}); c = clicks.get(str(uid), 0)
            r = p.get("unlock_required", 4)
            liked = str(uid) in p.get("likes", [])
            faved = str(uid) in p.get("favorites", [])
            return jsonify({"remaining": r-c, "total": r, "done": c>=r, "liked": liked, "favorited": faved})
    return jsonify({"error": "not found"}), 404

# === USERS ===
@app.route("/api/user/<uid>", methods=["GET"])
def get_user(uid):
    data = load_data()
    u = data["users"].get(str(uid), {
        "wallet": 0, "premium": False, "join_date": datetime.now().strftime("%Y-%m-%d"),
        "redeemed": [], "favorites": []
    })
    favs = []
    for p in data["posts"]:
        if str(uid) in p.get("favorites", []): favs.append(p["id"])
    return jsonify({
        "wallet": u.get("wallet", 0), "premium": u.get("premium", False),
        "join_date": u.get("join_date", ""), "favorites": favs,
        "redeemed": u.get("redeemed", []),
    })

@app.route("/api/user/<uid>", methods=["POST"])
def update_user(uid):
    data = load_data()
    data["users"][str(uid)] = request.json
    save_data(data)
    return jsonify({"ok": True})

# === GIFT CODES ===
@app.route("/api/admin/gift_codes", methods=["GET"])
def admin_get_gift_codes():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    return jsonify(data.get("gift_codes", []))

@app.route("/api/admin/gift_codes", methods=["POST"])
def admin_create_gift_code():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    body = request.json
    gc = {
        "code": body.get("code", uuid.uuid4().hex[:8].upper()),
        "expire": body.get("expire", ""),
        "max_uses": int(body.get("max_uses", 1)),
        "allowed_posts": body.get("allowed_posts", []),
        "permission_count": int(body.get("permission_count", 0)),
        "uses": 0, "used_by": [],
    }
    data["gift_codes"].append(gc)
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/admin/gift_code/<code>", methods=["DELETE"])
def admin_delete_gift_code(code):
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    for i, gc in enumerate(data["gift_codes"]):
        if gc["code"] == code.upper():
            data["gift_codes"].pop(i)
            save_data(data)
            return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404

@app.route("/api/redeem", methods=["POST"])
def redeem_code():
    data = load_data()
    code = request.json.get("code", "").strip().upper()
    uid = str(request.json.get("user_id", ""))
    for gc in data["gift_codes"]:
        if gc["code"] == code:
            if len(gc.get("used_by", [])) >= gc.get("max_uses", 1):
                return jsonify({"ok": False, "msg": "Code expired"})
            if uid in gc.get("used_by", []):
                return jsonify({"ok": False, "msg": "Already used"})
            gc.setdefault("used_by", []).append(uid)
            gc["uses"] = len(gc["used_by"])
            # Grant wallet coins
            u = data["users"].get(uid, {})
            u["wallet"] = u.get("wallet", 0) + gc.get("permission_count", 10)
            data["users"][uid] = u
            save_data(data)
            return jsonify({"ok": True, "amount": gc.get("permission_count", 10), "msg": f"🎉 +{gc.get('permission_count', 10)} coins!"})
    return jsonify({"ok": False, "msg": "Invalid code"})

# === CONFIG ===
@app.route("/api/config")
def get_config():
    data = load_data()
    return jsonify(data.get("config", {}))

@app.route("/api/admin/config", methods=["POST"])
def admin_set_config():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    data["config"] = request.json
    save_data(data)
    return jsonify({"ok": True})

# === ANALYTICS ===
@app.route("/api/admin/stats")
def admin_stats():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    total_views = sum(p.get("views", 0) for p in data["posts"])
    total_downloads = sum(p.get("downloads", 0) for p in data["posts"])
    total_likes = sum(len(p.get("likes", [])) for p in data["posts"])
    users = data.get("users", {})
    premium_users = sum(1 for u in users.values() if u.get("premium"))
    return jsonify({
        "posts": len(data["posts"]),
        "users": len(users),
        "premium_users": premium_users,
        "views": total_views,
        "downloads": total_downloads,
        "likes": total_likes,
    })

@app.route("/api/admin/users")
def admin_get_users():
    if not check_admin(): return jsonify({"error": "unauthorized"}), 401
    data = load_data()
    return jsonify(data.get("users", {}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
