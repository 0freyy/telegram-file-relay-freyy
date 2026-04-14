# 📡 Telegram File Relay

A stateless GitHub Actions-based system that relays files from Telegram to free file hosting services.

## How It Works

```
Telegram Bot → GitHub API (dispatch) → GitHub Actions → Download from Telegram → Upload to Host → Send Link Back
```

### Flow
1. Telegram bot receives file
2. Bot triggers GitHub Actions via `repository_dispatch` with `file_id` and `chat_id`
3. Workflow downloads file using Telegram Bot API
4. File uploaded to free hosting (0x0.st → transfer.sh → gofile.io)
5. Download link sent back to Telegram chat
6. Temp files cleaned up

## Setup

### 1. Add GitHub Token to Telegram Bot

```python
import requests

GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # Create at https://github.com/settings/tokens
REPO_OWNER = "0freyy"
REPO_NAME = "telegram-file-relay-freyy"

def relay_file_to_github(file_id, chat_id):
    requests.post(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/dispatches",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+raw"
        },
        json={
            "event_type": "telegram_file",
            "client_payload": {
                "file_id": file_id,
                "chat_id": chat_id
            }
        }
    )
```

### 2. Add Telegram Bot Token to Repository Secrets

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Create secret: `TELEGRAM_BOT_TOKEN=123456:ABCDefghIJKlmnopQRStuvwxyz`

### 3. Trigger from Bot

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    relay_file_to_github(document.file_id, update.effective_chat.id)
    await update.message.reply_text("📤 Relaying file...")

app = Application.builder().token("YOUR_BOT_TOKEN").build()
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.run_polling()
```

## Features

- ✅ **Stateless** - No database, no server required
- ✅ **Resilient** - 3-tier upload fallback system
- ✅ **Fast** - Prefers 0x0.st (fastest, no tracking)
- ✅ **Secure** - Token stored in secrets, files never persisted
- ✅ **Production-Ready** - Error handling, cleanup, timeout protection

## Upload Services (Priority Order)

1. **0x0.st** - Fastest, no tracking, 365-day retention
2. **transfer.sh** - Reliable, 14-day retention
3. **gofile.io** - Large file support, permanent storage

## File Size Limits

- 0x0.st: 512 MB
- transfer.sh: 10 GB
- gofile.io: 100 GB

## Environment Variables

Set in workflow or via GitHub secrets:

| Variable | Description | Source |
|----------|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | Bot token for Telegram API | GitHub Secret |
| `FILE_ID` | Telegram file ID | Dispatch payload |
| `CHAT_ID` | Telegram chat ID | Dispatch payload |
| `UPLOAD_TIMEOUT` | Upload timeout in seconds | Default: 300 |

## Error Handling

- Network failures: Retried with next service
- All services down: User notified in Telegram
- File download failed: Error message sent to chat

## Cost

**$0** - Uses only:
- GitHub Actions free tier (2000 minutes/month for private repos)
- Free file hosting services
- Telegram Bot API (free)

## Security Notes

- GitHub token should have minimal permissions (only `repo:status` and `public_repo`)
- Never commit `TELEGRAM_BOT_TOKEN` to repository
- Files are deleted after upload completes
- Uploaded files inherit host service's retention policy

## Limitations

- Max execution time: 6 hours (GitHub Actions limit)
- File download timeout: 60 seconds
- Upload timeout: 5 minutes
- Stateless design: No retry queue if Actions fails

## Example Bot Implementation

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests

GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"
REPO = "0freyy/telegram-file-relay-freyy"

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    filename = "file"
    
    if update.message.document:
        file_id = update.message.document.file_id
        filename = update.message.document.file_name or "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        filename = f"video_{update.message.video.file_id[:8]}.mp4"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        filename = update.message.audio.file_name or "audio.mp3"
    
    if not file_id:
        return
    
    # Trigger relay
    response = requests.post(
        f"https://api.github.com/repos/{REPO}/dispatches",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+raw"
        },
        json={
            "event_type": "telegram_file",
            "client_payload": {
                "file_id": file_id,
                "chat_id": str(update.effective_chat.id)
            }
        }
    )
    
    if response.status_code == 204:
        await update.message.reply_text("📤 Uploading file...")
    else:
        await update.message.reply_text("❌ Relay failed. Try again later.")

app = Application.builder().token("YOUR_BOT_TOKEN").build()
app.add_handler(MessageHandler(filters.Document.ALL | filters.Video | filters.Audio, handle_media))
app.run_polling()
```

## Troubleshooting

**Workflow doesn't run:**
- Check if token has `repo` scope
- Verify `TELEGRAM_BOT_TOKEN` is set in secrets
- Check workflow syntax: `gh workflow view telegram-relay.yml`

**File upload fails:**
- Check if services are accessible (not blocked in region)
- Increase `UPLOAD_TIMEOUT` if on slow connection
- Verify file size is under service limits

**Bot doesn't reply:**
- Check if bot has `sendMessage` permission
- Verify chat ID is correct (private chat vs. group)
- Check workflow logs: Actions tab → Latest run

## License

MIT