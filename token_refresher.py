import time
import threading
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = "token.json"
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TOKEN_URL = "https://accounts.spotify.com/api/token"

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tokens(data):
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def refresh_access_token():
    tokens = load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("No refresh token found.")
        return
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(TOKEN_URL, data=payload, timeout=15)
    if r.status_code == 200:
        new_tokens = r.json()
        # Keep the old refresh_token if not provided
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        # Calculate new expires_at
        new_tokens["expires_at"] = int(time.time()) + int(new_tokens.get("expires_in", 3600))
        save_tokens(new_tokens)
        print("Spotify token refreshed.")
    else:
        print("Failed to refresh token:", r.text)

def token_refresher_loop():
    while True:
        tokens = load_tokens()
        expires_at = tokens.get("expires_at", 0)
        now = int(time.time())
        # Refresh 5 minutes before expiry
        sleep_time = max(30, expires_at - now - 300)
        if expires_at > now:
            print(f"Token valid, sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)
            refresh_access_token()
        else:
            print("Token expired or missing, waiting 60 seconds.")
            time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=token_refresher_loop, daemon=True).start()
    print("Token refresher started. Press Ctrl+C to stop.")
    while True:
        time.sleep(3600)