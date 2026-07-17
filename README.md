# Telegram Mini App + Bot

A Telegram bot with a Mini App for sharing videos, photos, and files with a task-based unlock system.

## Features

- **Telegram Bot** - Upload posts, manage content, admin panel
- **Mini App** - View posts, complete tasks to unlock video links
- **Task System** - Users click buttons (1/3/5 times) to unlock content
- **Albums** - Grid view of all uploaded photos
- **Profile** - User info, join channel button

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Telegram bot (polling) |
| `mini_app_server.py` | Flask server for Mini App + API |
| `templates/mini_app.html` | Mini App frontend |
| `posts.json` | Data storage (auto-created) |
| `uploads/` | Uploaded photos (auto-created) |

## Setup

1. Install dependencies:
```bash
pip install flask requests python-telegram-bot
```

2. Update `TOKEN` and `ADMIN_ID` in both `bot.py` and `mini_app_server.py`

3. Set up HTTPS tunnel (for Mini App):
```bash
ssh -R 80:localhost:5000 serveo.net
```

4. Update `APP_URL` in `bot.py` with the tunnel URL

5. Start the server:
```bash
python3 mini_app_server.py &
```

6. Start the bot:
```bash
python3 bot.py &
```

## Usage

- `/start` - Open Mini App
- `/admin` - Admin panel (admin only)
  - Upload posts (photo + link + click count)
  - Set channel link
  - View all users, posts, links
