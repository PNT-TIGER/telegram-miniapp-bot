import json, os, logging, uuid
from datetime import datetime
import requests as http_requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8867263661:AAFVGrC_GN-IUNOzaXCBUHMo9JiKyXTw53Q"
ADMIN_ID = 7797816241
UPLOAD_DIR = "uploads"
BOT_USERNAME = None

os.makedirs(UPLOAD_DIR, exist_ok=True)

ADMIN_APP_URL = "https://pnt-tiger.github.io/telegram-miniapp-bot/admin.html"

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Open Web Admin", web_app=WebAppInfo(url=ADMIN_APP_URL))],
        [InlineKeyboardButton("📤 Upload (Video/Photo/File)", callback_data="upload")],
        [InlineKeyboardButton("🔗 All Links", callback_data="all_links")],
    ])

def back_btn():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        key = args[0]
        if key.startswith("v_"):
            vid = key[2:]
            for f in os.listdir(UPLOAD_DIR):
                if vid in f:
                    fp = os.path.join(UPLOAD_DIR, f)
                    if f.endswith((".mp4", ".mov", ".avi", ".mkv")):
                        with open(fp, "rb") as vf:
                            await update.message.reply_video(vf, caption="🎬 Your video")
                    elif f.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                        with open(fp, "rb") as pf:
                            await update.message.reply_photo(pf, caption="📷 Your photo")
                    else:
                        with open(fp, "rb") as df:
                            await update.message.reply_document(df, caption="📁 Your file")
                    return
            await update.message.reply_text("❌ Not found.")
            return

    welcome = "👋 Welcome to Admin Bot!\n\nUse /admin to manage uploads."
    if update.effective_user.id == ADMIN_ID:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Admin Panel", callback_data="back_admin")]])
        await update.message.reply_text(welcome, reply_markup=keyboard)
    else:
        await update.message.reply_text(welcome)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text("⚙️ *Admin Panel*\n\nUpload content and get shareable links.", parse_mode="Markdown", reply_markup=admin_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.edit_message_text("⛔ Unauthorized.")
        return
    cb = q.data

    if cb == "back_admin":
        await q.edit_message_text("⚙️ *Admin Panel*", parse_mode="Markdown", reply_markup=admin_keyboard())
        return

    if cb == "upload":
        context.user_data["awaiting"] = "post_title"
        await q.edit_message_text("📤 Send the TITLE for this post.")
    elif cb == "all_links":
        files = [f for f in os.listdir(UPLOAD_DIR) if not f.startswith(".")]
        if not files:
            await q.edit_message_text("🔗 No uploads yet.", reply_markup=back_btn())
            return
        lines = []
        for f in sorted(files, key=lambda x: os.path.getmtime(f"{UPLOAD_DIR}/{x}"), reverse=True)[:20]:
            fid = f.split(".")[0]
            link = f"https://t.me/{BOT_USERNAME}?start=v_{fid}" if BOT_USERNAME else f"v_{fid}"
            icon = "🎬" if f.endswith((".mp4",".mov",".avi",".mkv")) else "📷" if f.endswith((".jpg",".jpeg",".png",".gif",".webp")) else "📁"
            lines.append(f"{icon} `{link}`")
        await q.edit_message_text("🔗 *All Links:*\n\n" + "\n".join(lines), parse_mode="Markdown", reply_markup=back_btn(), disable_web_page_preview=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return

    if awaiting == "post_title" and update.message.text:
        context.user_data["post_title"] = update.message.text.strip()
        context.user_data["awaiting"] = "post_photo"
        await update.message.reply_text("✅ Title saved! Now send the PHOTO or VIDEO (thumbnail).")
        return

    if awaiting == "post_photo":
        file_id = None
        fid = uuid.uuid4().hex[:8]
        if update.message.video:
            file_id = update.message.video.file_id
            fname = f"{fid}.mp4"
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
            fname = f"{fid}.jpg"
        elif update.message.document:
            file_id = update.message.document.file_id
            ext = update.message.document.file_name.split(".")[-1] if update.message.document.file_name else "file"
            fname = f"{fid}.{ext}"
        else:
            await update.message.reply_text("❌ Send a photo, video, or file.")
            return
        r = http_requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}")
        if r.status_code == 200:
            fp = r.json()["result"]["file_path"]
            dl = http_requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}")
            if dl.status_code == 200:
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                with open(f"{UPLOAD_DIR}/{fname}", "wb") as wf:
                    wf.write(dl.content)
                context.user_data["post_photo"] = fname
                context.user_data["awaiting"] = "post_link"
                await update.message.reply_text("✅ Thumbnail saved! Now send the FINAL LINK.")
                return
        await update.message.reply_text("❌ Download failed. Try again.")
        return

    if awaiting == "post_link" and update.message.text:
        context.user_data["post_link"] = update.message.text.strip()
        context.user_data["awaiting"] = "post_clicks"
        await update.message.reply_text("✅ Link saved! Send UNLOCK COUNT (e.g. 4):")
        return

    if awaiting == "post_clicks" and update.message.text:
        try:
            clicks = int(update.message.text.strip())
            if clicks < 1 or clicks > 20:
                await update.message.reply_text("❌ Send 1-20.")
                return
        except:
            await update.message.reply_text("❌ Send a valid number.")
            return

        title = context.user_data.get("post_title", "Untitled")
        photo = context.user_data.get("post_photo", "")
        link = context.user_data.get("post_link", "")
        if not link:
            await update.message.reply_text("❌ Missing data. Start again.")
            context.user_data["awaiting"] = None
            return

        try:
            with open("posts.json") as f:
                data = json.load(f)
        except:
            data = {"posts": [], "users": {}, "config": {}}

        post = {
            "id": uuid.uuid4().hex[:8],
            "title": title, "photo": photo, "link": link,
            "unlock_required": clicks,
            "views": 0, "viewers": [], "downloads": 0,
            "likes": [], "favorites": [], "unlock_clicks": {},
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        data["posts"].insert(0, post)
        with open("posts.json", "w") as f:
            json.dump(data, f, indent=2)

        for k in ["post_title", "post_photo", "post_link"]:
            context.user_data.pop(k, None)
        context.user_data["awaiting"] = None

        bname = BOT_USERNAME or "bot"
        await update.message.reply_text(
            f"✅ *Post Created!*\n"
            f"📌 `{title}`\n"
            f"🔢 Unlock: {clicks} clicks\n"
            f"🆔 `{post['id']}`\n"
            f"🔗 `https://t.me/{bname}?start=v_{post['id']}`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("❓ Use /admin to start.")

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
