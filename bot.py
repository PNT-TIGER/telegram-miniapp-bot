import json, os, logging, uuid, requests as http_requests
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8992436164:AAGRoWbsfsw54LL4vBnt7wOaPXtHUmuYg0Y"
ADMIN_ID = 7797816241
DATA_FILE = "posts.json"
BOT_USERNAME = None
APP_URL = "https://c608d31e3c7c6fe9-103-126-20-86.serveousercontent.com"

def load_data():
    default = {"posts": [], "config": {"channel_link": ""}}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Post", callback_data="upload_post")],
        [InlineKeyboardButton("🔗 Set Channel Link", callback_data="set_channel")],
        [InlineKeyboardButton("📹 All Video Links", callback_data="all_videos")],
        [InlineKeyboardButton("📷 All Photo Links", callback_data="all_photos")],
        [InlineKeyboardButton("📁 All Files", callback_data="all_files")],
        [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_admin")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        data = load_data()
        key = args[0]
        if key.startswith("post_"):
            pid = key[5:]
            for p in data["posts"]:
                if p["id"] == pid:
                    await update.message.reply_photo(photo=open(f"uploads/{p['photo']}", "rb") if os.path.exists(f"uploads/{p['photo']}") else p.get("photo", ""), caption=f"📢 Post: {p.get('link', '')}")
                    return
            await update.message.reply_text("Post not found.")
            return
        if key.startswith("video_"):
            for p in data["posts"]:
                if p["id"] == key[6:]:
                    await update.message.reply_text(f"🔗 Video link: {p['link']}")
                    return
            await update.message.reply_text("Not found.")
            return

    web_app_url = APP_URL or "https://example.com"
    welcome = "👋 Welcome! Open the Mini App below to view posts."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Open Mini App", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("⚙️ Admin Panel", callback_data="go_admin")],
    ])
    await update.message.reply_text(welcome, reply_markup=keyboard)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text("⚙️ Admin Panel", parse_mode="Markdown", reply_markup=admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.edit_message_text("⛔ Unauthorized.")
        return
    cb = q.data

    if cb == "go_admin":
        await q.edit_message_text("⚙️ Admin Panel", parse_mode="Markdown", reply_markup=admin_keyboard())
    elif cb == "upload_post":
        context.user_data["awaiting"] = "post_photo"
        msg = await q.edit_message_text("📤 Send me the PHOTO for the post (16:9 recommended).")
        context.user_data["msg_id"] = msg.message_id
    elif cb == "set_channel":
        context.user_data["awaiting"] = "channel_link"
        msg = await q.edit_message_text("🔗 Send me the channel invite link.")
        context.user_data["msg_id"] = msg.message_id
    elif cb == "all_videos":
        d = load_data()
        if not d["posts"]:
            await q.edit_message_text("No posts yet.", reply_markup=back_btn()); return
        lines = []
        for p in d["posts"]:
            lines.append(f"🎬 {p.get('link', 'N/A')}")
        await q.edit_message_text("📹 *All Video Links:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=back_btn(), disable_web_page_preview=True)
    elif cb == "all_photos":
        d = load_data()
        if not d["posts"]:
            await q.edit_message_text("No photos yet.", reply_markup=back_btn()); return
        lines = []
        for p in d["posts"]:
            lines.append(f"📷 {p.get('date', '')}")
        await q.edit_message_text("📷 *All Photos:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=back_btn())
    elif cb == "all_files":
        d = load_data()
        parts = []
        if d["posts"]:
            parts.append("*📁 Posts:*")
            for p in d["posts"]:
                parts.append(f"📁 `{p['id']}` - {p.get('link', 'N/A')}")
        if d.get("config", {}).get("channel_link"):
            parts.append(f"\n*🔗 Channel:* {d['config']['channel_link']}")
        if not parts:
            await q.edit_message_text("Nothing yet.", reply_markup=back_btn()); return
        await q.edit_message_text("\n".join(parts), parse_mode="Markdown", reply_markup=back_btn(), disable_web_page_preview=True)
    elif cb == "all_users":
        d = load_data()
        users = set()
        for p in d["posts"]:
            for uid in p.get("viewers", []):
                users.add(uid)
            for uid in p.get("clicks", {}):
                users.add(uid)
        if not users:
            await q.edit_message_text("👥 No users yet.", reply_markup=back_btn()); return
        text = "👥 *All Users:*\n\n" + "\n".join([f"• `{u}`" for u in users])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return

    data = load_data()

    if awaiting == "post_photo" and update.message.photo:
        file_id = update.message.photo[-1].file_id
        r = http_requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}")
        if r.status_code == 200:
            fp = r.json()["result"]["file_path"]
            dl = http_requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}")
            if dl.status_code == 200:
                fname = f"{uuid.uuid4().hex[:8]}.jpg"
                os.makedirs("uploads", exist_ok=True)
                with open(f"uploads/{fname}", "wb") as f:
                    f.write(dl.content)
                context.user_data["post_photo"] = fname
        context.user_data["awaiting"] = "post_link"
        context.user_data["msg_id"] = None
        await update.message.reply_text("✅ Photo saved! Now send me the VIDEO LINK for this post.")
        return

    if awaiting == "post_link" and update.message.text:
        link = update.message.text.strip()
        context.user_data["post_link"] = link
        context.user_data["awaiting"] = "post_clicks"
        await update.message.reply_text("✅ Link saved! Now send the number of clicks required (1, 3, or 5).")
        return

    if awaiting == "post_clicks" and update.message.text:
        try:
            clicks = int(update.message.text.strip())
            if clicks not in [1, 3, 5]:
                await update.message.reply_text("❌ Please send 1, 3, or 5.")
                return
        except:
            await update.message.reply_text("❌ Please send a number (1, 3, or 5).")
            return

        photo = context.user_data.get("post_photo", "")
        link = context.user_data.get("post_link", "")
        post = {
            "id": uuid.uuid4().hex[:8],
            "photo": photo,
            "link": link,
            "click_required": clicks,
            "views": 0,
            "viewers": [],
            "clicks": {},
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        data["posts"].insert(0, post)
        save_data(data)
        context.user_data["awaiting"] = None
        context.user_data.pop("post_photo", None)
        context.user_data.pop("post_link", None)
        await update.message.reply_text(f"✅ Post created!\nID: `{post['id']}`\nClicks required: {clicks}\nMini App URL: {APP_URL}/?post={post['id']}", parse_mode="Markdown")
        return

    if awaiting == "channel_link" and update.message.text:
        data["config"]["channel_link"] = update.message.text.strip()
        save_data(data)
        context.user_data["awaiting"] = None
        await update.message.reply_text("✅ Channel link saved!")
        if "msg_id" in context.user_data:
            try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data["msg_id"])
            except: pass
        return

    if update.message.text and not awaiting.startswith("post_"):
        await update.message.reply_text("❓ Use admin panel buttons first.")

async def post_init(app: Application):
    global BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"Bot username: {BOT_USERNAME}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
