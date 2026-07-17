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
        context.user_data["awaiting"] = "upload"
        await q.edit_message_text("📤 Send me a Video, Photo, or File. I'll generate a link for it.")
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

    fname = None
    caption = None

    if awaiting == "upload":
        file_id = None
        if update.message.video:
            f = update.message.video
            file_id = f.file_id
            fid = uuid.uuid4().hex[:8]
            fname = f"{fid}.mp4"
            caption = "🎬 Video uploaded!"
        elif update.message.photo:
            f = update.message.photo[-1]
            file_id = f.file_id
            fid = uuid.uuid4().hex[:8]
            fname = f"{fid}.jpg"
            caption = "📷 Photo uploaded!"
        elif update.message.document:
            f = update.message.document
            file_id = f.file_id
            fid = uuid.uuid4().hex[:8]
            ext = f.file_name.split(".")[-1] if f.file_name else "file"
            fname = f"{fid}.{ext}"
            caption = "📁 File uploaded!"

        if file_id and fname:
            r = http_requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}")
            if r.status_code == 200:
                fp = r.json()["result"]["file_path"]
                dl = http_requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}")
                if dl.status_code == 200:
                    with open(f"{UPLOAD_DIR}/{fname}", "wb") as wf:
                        wf.write(dl.content)
                    link = f"https://t.me/{BOT_USERNAME}?start=v_{fid}" if BOT_USERNAME else f"v_{fid}"
                    await update.message.reply_text(f"{caption}\n🔗 `{link}`", parse_mode="Markdown")
                    context.user_data["awaiting"] = None
                    return

    await update.message.reply_text("❓ Please use the admin panel buttons first.")

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
