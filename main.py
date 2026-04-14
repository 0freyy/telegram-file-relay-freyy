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


def send_message(chat_id: str, text: str) -> bool:
    try:
        response = requests.post(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ send_message error: {e}", file=sys.stderr)
        return False


def get_file_info(file_id: str) -> Optional[dict]:
    try:
        response = requests.get(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )

        data = response.json()

        if data.get("ok"):
            return data.get("result")

        print(f"❌ Telegram error: {data}", file=sys.stderr)
        return None

    except Exception as e:
        print(f"❌ get_file_info error: {e}", file=sys.stderr)
        return None


def download_file(file_path: str, file_id: str) -> Optional[Path]:
    try:
        url = f"{TELEGRAM_API}/file/bot{BOT_TOKEN}/{file_path}"
        response = requests.get(url, timeout=60)

        if response.status_code != 200:
            return None

        temp_file = TEMP_DIR / f"telegram_{file_id[:8]}"
        temp_file.write_bytes(response.content)

        print(f"✅ downloaded: {temp_file}")
        return temp_file

    except Exception as e:
        print(f"❌ download error: {e}", file=sys.stderr)
        return None


def upload_to_0x0(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            r = requests.post("https://0x0.st", files={"file": f}, timeout=UPLOAD_TIMEOUT)
        return r.text.strip() if r.status_code == 200 else None
    except Exception as e:
        print(f"0x0 failed: {e}", file=sys.stderr)
        return None


def upload_to_transfer(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://transfer.sh/{file_path.name}",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        return r.text.strip() if r.status_code == 200 else None
    except Exception as e:
        print(f"transfer failed: {e}", file=sys.stderr)
        return None


def upload_to_gofile(file_path: Path) -> Optional[str]:
    try:
        r = requests.get("https://api.gofile.io/servers", timeout=10)
        server = r.json().get("data", {}).get("servers", [{}])[0].get("name")

        if not server:
            return None

        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )

        data = r.json()

        if data.get("status") == "ok":
            file_id = data.get("data", {}).get("fileId")
            if file_id:
                return f"https://gofile.io/d/{file_id}"

        return None

    except Exception as e:
        print(f"gofile failed: {e}", file=sys.stderr)
        return None


def upload_file(file_path: Path) -> Optional[str]:
    services = [
        upload_to_0x0,
        upload_to_transfer,
        upload_to_gofile
    ]

    for service in services:
        url = service(file_path)
        if url:
            return url

    return None


def cleanup(file_path: Path):
    try:
        file_path.unlink()
    except:
        pass


def main():
    if not FILE_ID or not CHAT_ID or not BOT_TOKEN:
        print("Missing env vars", file=sys.stderr)
        sys.exit(1)

    send_message(CHAT_ID, "Downloading...")

    file_info = get_file_info(FILE_ID)
    if not file_info:
        send_message(CHAT_ID, "Failed to get file info")
        sys.exit(1)

    file_path = file_info["file_path"]

    temp_file = download_file(file_path, FILE_ID)
    if not temp_file:
        send_message(CHAT_ID, "Download failed")
        sys.exit(1)

    send_message(CHAT_ID, "Uploading...")

    url = upload_file(temp_file)

    if url:
        send_message(CHAT_ID, f"Done:\n{url}")
    else:
        send_message(CHAT_ID, "Upload failed")

    cleanup(temp_file)


if __name__ == "__main__":
    main()
