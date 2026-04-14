#!/usr/bin/env python3
import os
import sys
import requests
import json
from pathlib import Path
from typing import Optional, Tuple

# Environment
FILE_ID = os.getenv("FILE_ID")
CHAT_ID = os.getenv("CHAT_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", 300))

TEMP_DIR = Path("/tmp")
TELEGRAM_API = "https://api.telegram.org"

def send_message(chat_id: str, text: str) -> bool:
    """Send message to Telegram chat."""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Failed to send message: {e}", file=sys.stderr)
        return False

def get_file_info(file_id: str) -> Optional[dict]:
    """Get file info from Telegram API."""
    try:
        response = requests.get(
            f"{TELEGRAM_API}/bot{BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )
        data = response.json()
        if data.get("ok"):
            return data.get("result")
        print(f"❌ Telegram API error: {data.get('description')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Failed to get file info: {e}", file=sys.stderr)
        return None

def download_file(file_path: str, file_id: str) -> Optional[Path]:
    """Download file from Telegram."""
    try:
        file_url = f"{TELEGRAM_API}/file/bot{BOT_TOKEN}/{file_path}"
        response = requests.get(file_url, timeout=60)
        if response.status_code == 200:
            temp_file = TEMP_DIR / f"telegram_file_{file_id[:8]}"
            temp_file.write_bytes(response.content)
            print(f"✅ Downloaded {len(response.content)} bytes to {temp_file}")
            return temp_file
        else:
            print(f"❌ Download failed: HTTP {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"❌ Download error: {e}", file=sys.stderr)
        return None

def upload_to_0x0st(file_path: Path) -> Optional[str]:
    """Upload to 0x0.st (512 MB limit)."""
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://0x0.st",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        if response.status_code == 200:
            return response.text.strip()
        return None
    except Exception as e:
        print(f"⚠️  0x0.st failed: {e}", file=sys.stderr)
        return None

def upload_to_transfer_sh(file_path: Path) -> Optional[str]:
    """Upload to transfer.sh (10 GB limit, 14 day retention)."""
    try:
        filename = file_path.name
        with open(file_path, "rb") as f:
            response = requests.post(
                f"https://transfer.sh/{filename}",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        if response.status_code == 200:
            return response.text.strip()
        return None
    except Exception as e:
        print(f"⚠️  transfer.sh failed: {e}", file=sys.stderr)
        return None

def upload_to_gofile(file_path: Path) -> Optional[str]:
    """Upload to gofile.io (100 GB limit)."""
    try:
        # Get upload server
        response = requests.get("https://api.gofile.io/servers", timeout=10)
        server = response.json().get("data", {}).get("servers", [{}])[0].get("name")
        
        if not server:
            return None
        
        # Upload file
        with open(file_path, "rb") as f:
            response = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f},
                timeout=UPLOAD_TIMEOUT
            )
        
data = response.json()
        if data.get("status") == "ok":
            file_id = data.get("data", {}).get("fileId")
            return f"https://gofile.io/d/{file_id}" if file_id else None
        return None
    except Exception as e:
        print(f"⚠️  gofile.io failed: {e}", file=sys.stderr)
        return None

def upload_file(file_path: Path) -> Optional[str]:
    """Try uploading to services in priority order."""
    services = [
        ("0x0.st", upload_to_0x0st),
        ("transfer.sh", upload_to_transfer_sh),
        ("gofile.io", upload_to_gofile)
    ]
    
    for service_name, service_func in services:
        print(f"📤 Trying {service_name}...")
        url = service_func(file_path)
        if url:
            print(f"✅ Uploaded via {service_name}: {url}")
            return url
    
    print("❌ All upload services failed", file=sys.stderr)
    return None

def cleanup_file(file_path: Path) -> None:
    """Delete temp file."""
    try:
        file_path.unlink()
        print(f"🧹 Cleaned up {file_path}")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}", file=sys.stderr)

def main():
    """Main relay logic."""
    if not FILE_ID or not CHAT_ID or not BOT_TOKEN:
        print("❌ Missing required env vars: FILE_ID, CHAT_ID, TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)
    
    print(f"🔄 Relaying file {FILE_ID} to chat {CHAT_ID}")
    
    # Step 1: Get file info
    file_info = get_file_info(FILE_ID)
    if not file_info:
        send_message(CHAT_ID, "❌ Failed to get file info from Telegram")
        sys.exit(1)
    
    file_path = file_info.get("file_path")
    file_size = file_info.get("file_size", 0)
    print(f"📄 File: {file_path} ({file_size} bytes)")
    
    # Step 2: Download file
    temp_file = download_file(file_path, FILE_ID)
    if not temp_file:
        send_message(CHAT_ID, "❌ Failed to download file from Telegram")
        sys.exit(1)
    
    # Step 3: Upload to hosting
    download_url = upload_file(temp_file)
    
    # Step 4: Send result
    if download_url:
        message = f"✅ File ready!\n\n🔗 {download_url}"
        send_message(CHAT_ID, message)
        print(f"✅ Relay complete: {download_url}")
    else:
        send_message(CHAT_ID, "❌ Failed to upload file. Try again later.")
        sys.exit(1)
    
    # Step 5: Cleanup
    cleanup_file(temp_file)

if __name__ == "__main__":
    main()