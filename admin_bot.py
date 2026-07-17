import json, os, logging, uuid, requests as http_requests
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8867263661:AAFVGrC_GN-IUNOzaXCBUHMo9JiKyXTw53Q"
ADMIN_ID = 7797816241
DATA_FILE = "posts.json"
BOT_USERNAME = None
UPLOAD_DIR = "uploads"

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
        [InlineKeyboardButton("📋 All Posts", callback_data="all_posts")],
        [InlineKeyboardButton("👥 Users", callback_data="all_users")],
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="go_admin")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text("⚙️ Admin Bot — use /admin to manage posts.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text("⚙️ *Admin Panel*", parse_mode="Markdown", reply_markup=admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.edit_message_text("⛔ Unauthorized.")
        return
    cb = q.data

    if cb == "go_admin":
        await q.edit_message_text("⚙️ *Admin Panel*", parse_mode="Markdown", reply_markup=admin_keyboard())
    elif cb == "upload_post":
        context.user_data["awaiting"] = "post_photo"
        msg = await q.edit_message_text("📤 Send the PHOTO for the post.")
        context.user_data["msg_id"] = msg.message_id
    elif cb == "set_channel":
        context.user_data["awaiting"] = "channel_link"
        msg = await q.edit_message_text("🔗 Send the channel invite link.")
        context.user_data["msg_id"] = msg.message_id
    elif cb == "all_posts":
        d = load_data()
        if not d["posts"]:
            await q.edit_message_text("No posts yet.", reply_markup=back_btn())
            return
        lines = [f"📌 `{p['id']}` — 👁 {p.get('views',0)} views" for p in d["posts"]]
        await q.edit_message_text("📋 *All Posts:*\n\n" + "\n".join(lines[-10:]), parse_mode="Markdown", reply_markup=back_btn())
    elif cb == "all_users":
        d = load_data()
        users = set()
        for p in d["posts"]:
            for uid in p.get("viewers", []): users.add(uid)
        if not users:
            await q.edit_message_text("👥 No users yet.", reply_markup=back_btn())
            return
        text = "👥 *Users:*\n\n" + "\n".join([f"• `{u}`" for u in users])
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
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                with open(f"{UPLOAD_DIR}/{fname}", "wb") as f:
                    f.write(dl.content)
                context.user_data["post_photo"] = fname
        context.user_data["awaiting"] = "post_link"
        await update.message.reply_text("✅ Photo saved! Now send the VIDEO LINK.")
        return

    if awaiting == "post_link" and update.message.text:
        link = update.message.text.strip()
        context.user_data["post_link"] = link
        context.user_data["awaiting"] = "post_clicks"
        await update.message.reply_text("✅ Link saved! Send clicks required (1, 3, or 5):")
        return

    if awaiting == "post_clicks" and update.message.text:
        try:
            clicks = int(update.message.text.strip())
            if clicks not in [1, 3, 5]:
                await update.message.reply_text("❌ Send 1, 3, or 5.")
                return
        except:
            await update.message.reply_text("❌ Send a number (1, 3, or 5).")
            return
        photo = context.user_data.get("post_photo", "")
        link = context.user_data.get("post_link", "")
        post = {
            "id": uuid.uuid4().hex[:8],
            "photo": photo,
            "link": link,
            "click_required": clicks,
            "views": 0, "viewers": [], "clicks": {},
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        data["posts"].insert(0, post)
        save_data(data)
        context.user_data["awaiting"] = None
        context.user_data.pop("post_photo", None)
        context.user_data.pop("post_link", None)
        await update.message.reply_text(f"✅ Post created!\nID: `{post['id']}`")
        return

    if awaiting == "channel_link" and update.message.text:
        data["config"]["channel_link"] = update.message.text.strip()
        save_data(data)
        context.user_data["awaiting"] = None
        await update.message.reply_text("✅ Channel link saved!")
        return

async def post_init(app: Application):
    global BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"Admin bot: @{BOT_USERNAME}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    logger.info("Admin bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
