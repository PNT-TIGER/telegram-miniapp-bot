import logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8992436164:AAGRoWbsfsw54LL4vBnt7wOaPXtHUmuYg0Y"
ADMIN_ID = 7797816241
APP_URL = "https://pnt-tiger.github.io/telegram-miniapp-bot"
BOT_USERNAME = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        key = args[0]
        if key.startswith("post_"):
            post_link = f"{APP_URL}/?post={key[5:]}"
            await update.message.reply_text(f"🔗 Open post: {post_link}")
            return

    welcome = "👋 Welcome! Tap the button below to open the Mini App."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Open Mini App", web_app=WebAppInfo(url=APP_URL))],
    ])
    await update.message.reply_text(welcome, reply_markup=keyboard)

async def post_init(app: Application):
    global BOT_USERNAME
    me = await app.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"User bot: @{BOT_USERNAME}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    logger.info("User bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
