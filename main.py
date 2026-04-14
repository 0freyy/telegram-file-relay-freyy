#!/usr/bin/env python3
import os
import sys
import requests
from pathlib import Path
from typing import Optional

# Environment
FILE_ID = os.getenv("FILE_ID")
CHAT_ID = os.getenv("CHAT_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", 300))

TEMP_DIR = Path("/tmp")
TELEGRAM_API = "https://api.telegram.org"


def send_message(chat_id: str, text: str):
    try:
        requests.post(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except Exception as e:
        print(f"send_message error: {e}", file=sys.stderr)


# STEP 1 — Get file_path from Telegram (lightweight metadata only)
def get_file_path(file_id: str) -> Optional[str]:
    try:
        r = requests.get(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )

        data = r.json()

        if not data.get("ok"):
            print(f"Telegram error: {data}", file=sys.stderr)
            return None

        return data["result"]["file_path"]

    except Exception as e:
        print(f"get_file_path error: {e}", file=sys.stderr)
        return None


# STEP 2 — STREAM download (IMPORTANT FIX for large files)
def download_file(file_path: str, file_id: str) -> Optional[Path]:
    try:
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        local_path = TEMP_DIR / f"{file_id}.bin"

        with requests.get(url, stream=True, timeout=300) as r:
            if r.status_code != 200:
                return None

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        return local_path

    except Exception as e:
        print(f"download error: {e}", file=sys.stderr)
        return None


# STEP 3 — upload (kept simple, stable priority chain)
def upload_file(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                "https://0x0.st",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        if r.status_code == 200:
            return r.text.strip()
    except:
        pass

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://transfer.sh/{file_path.name}",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        if r.status_code == 200:
            return r.text.strip()
    except:
        pass

    try:
        r = requests.get("https://api.gofile.io/servers", timeout=10)
        server = r.json()["data"]["servers"][0]["name"]

        with open(file_path, "rb") as f:
            r2 = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )

        data = r2.json()

        if data.get("status") == "ok":
            return f"https://gofile.io/d/{data['data']['fileId']}"

    except Exception as e:
        print(f"gofile error: {e}", file=sys.stderr)

    return None


def cleanup(path: Path):
    try:
        path.unlink()
    except:
        pass


def main():
    if not FILE_ID or not CHAT_ID or not BOT_TOKEN:
        print("Missing env vars", file=sys.stderr)
        sys.exit(1)

    send_message(CHAT_ID, "📥 Starting download...")

    file_path = get_file_path(FILE_ID)
    if not file_path:
        send_message(CHAT_ID, "❌ Failed to get file info")
        sys.exit(1)

    local_file = download_file(file_path, FILE_ID)
    if not local_file:
        send_message(CHAT_ID, "❌ Download failed")
        sys.exit(1)

    send_message(CHAT_ID, "📤 Uploading...")

    url = upload_file(local_file)

    if url:
        send_message(CHAT_ID, f"✅ Done:\n{url}")
    else:
        send_message(CHAT_ID, "❌ Upload failed")

    cleanup(local_file)


if __name__ == "__main__":
    main()
