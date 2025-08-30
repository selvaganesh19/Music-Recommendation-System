import gradio as gr
import requests
import webbrowser
import json
import os
import time
import re
from html import escape
from dotenv import load_dotenv


load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")


if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in environment or .env")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
TOKEN_FILE = "token.json"

ACCESS_TOKEN = None
REFRESH_TOKEN = None
EXPIRES_AT = 0

# --- Token Helpers ---
def _now(): return int(time.time())

def save_tokens(data: dict):
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    ACCESS_TOKEN = data["access_token"]
    REFRESH_TOKEN = data.get("refresh_token", REFRESH_TOKEN)
    EXPIRES_AT = _now() + int(data.get("expires_in", 36000000000000000000000000000000000))
    data["expires_at"] = EXPIRES_AT
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_tokens():
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            ACCESS_TOKEN = data.get("access_token")
            REFRESH_TOKEN = data.get("refresh_token")
            EXPIRES_AT = data.get("expires_at", 0)
        except Exception:
            pass

def refresh_access_token():
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    if not REFRESH_TOKEN:
        return False
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(TOKEN_URL, data=payload, timeout=15)
    if r.status_code == 200:
        save_tokens(r.json())
        return True
    return False

def get_access_token():
    global ACCESS_TOKEN, EXPIRES_AT
    if ACCESS_TOKEN and _now() < EXPIRES_AT - 60:
        return ACCESS_TOKEN
    if refresh_access_token():
        return ACCESS_TOKEN
    return None

# --- Config Validation ---
def validate_spotify_config() -> tuple[bool, str]:
    if not CLIENT_ID or not CLIENT_SECRET:
        return False, "SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is missing in your environment (.env)."
    if not re.match(r'^[0-9a-fA-F]{32}$', CLIENT_ID):
        return True, "⚠️ Warning: CLIENT_ID format looks unusual. Double-check it."
    if not (REDIRECT_URI.startswith("http://127.0.0.1") or REDIRECT_URI.startswith("http://localhost")):
        return False, "Redirect URI should be local while testing (http://127.0.0.1:5000/callback). Ensure it matches Spotify Dashboard."
    return True, "Configuration looks OK."

def build_auth_url(scope="playlist-read-private user-library-read"):
    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "show_dialog": "true"
    }
    return AUTH_URL + "?" + urlencode(params)

def test_auth_url(auth_url: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        r = requests.get(auth_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        return False, f"Could not contact Spotify: {e}"
    body = (r.text or "").strip()
    if "INVALID_CLIENT" in body or "Invalid redirect URI" in body or "Failed to get client" in body:
        return False, f"Spotify rejected authorize URL: {body[:300]}"
    if r.status_code != 200 and r.status_code not in (302, 303):
        return False, f"Spotify returned HTTP {r.status_code}. Body: {body[:200]}"
    return True, "Auth URL tested OK."

# --- Auth Flow ---
def login_open_browser():
    ok, msg = validate_spotify_config()
    if not ok:
        return f"❌ Config error: {msg}"

    auth_url = build_auth_url()
    ok2, msg2 = test_auth_url(auth_url)
    if not ok2:
        return (
            f"❌ Spotify rejected the auth URL.\n{msg2}\n\n"
            "➡️ Fix in your Spotify Dashboard:\n"
            "- Correct Client ID / Secret\n"
            "- Add this Redirect URI exactly:\n"
            f"{REDIRECT_URI}\n\n"
            f"Auth URL was:\n{auth_url}"
        )
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass
    return f"✅ Browser opened. If not, paste this URL manually:\n\n{auth_url}"

def exchange_code(code: str):
    payload = {
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    r = requests.post(TOKEN_URL, data=payload, timeout=15)
    if r.status_code == 200:
        save_tokens(r.json())
        return "✅ Login successful — token saved to token.json"
    else:
        return (
            f"❌ Login failed ({r.status_code})\nResponse: {r.text}\n\n"
            "➡️ Likely causes:\n- Wrong Client Secret\n- Expired/used code\n- Redirect URI mismatch."
        )

def logout_action():
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    ACCESS_TOKEN = REFRESH_TOKEN = None
    EXPIRES_AT = 0
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass
    return "🔓 Logged out (token.json removed)."

# --- Music Recommendation ---
LANG_HINT = {"en": "english", "hi": "hindi", "ta": "tamil"}
MOOD_SYNS = {
    "happy": {"happy","joy","cheerful","upbeat","glad"},
    "sad": {"sad","blue","melancholy","lonely"},
    "energetic": {"energetic","excited","active","lively"},
    "relaxed": {"relaxed","calm","chill","peaceful","serene"}
}

def normalize_mood(txt: str) -> str:
    if not txt: return "happy"
    t = txt.lower().strip()
    for k, syns in MOOD_SYNS.items():
        if t in syns: return k
        for w in syns:
            if w in t: return k
    return "happy"

def ms_to_mmss(ms:int)->str:
    s = int(ms//1000); return f"{s//60}:{s%60:02d}"

def spotify_request_get(endpoint, token, params=None):
    url = "https://api.spotify.com/v1/" + endpoint.lstrip("/")
    return requests.get(url, headers={"Authorization":f"Bearer {token}"}, params=params, timeout=15)

def search_playlists_for_language_mood(token,mood,lang,limit=6):
    q = f"{LANG_HINT.get(lang,'english')} {mood} songs"
    r = spotify_request_get("search", token, {"q":q,"type":"playlist","limit":limit})
    if r.status_code!=200: return None,r
    items = (r.json().get("playlists",{}) or {}).get("items",[]) or []
    if not items: return None,r
    return items[0],r

def get_tracks_from_playlist(token,pid,max_tracks=20):
    r = spotify_request_get(f"playlists/{pid}/tracks", token, {"limit":max_tracks})
    if r.status_code!=200: return None,r
    tracks=[]
    for item in r.json().get("items",[]):
        t=item.get("track")
        if not t: continue
        album_images = (t.get("album") or {}).get("images", [])
        img_url = album_images[1]["url"] if len(album_images)>=2 else (album_images[0]["url"] if album_images else "")
        tracks.append({
            "name":t.get("name",""),
            "artists":", ".join(a.get("name","") for a in t.get("artists",[])),
            "url":t.get("external_urls",{}).get("spotify",""),
            "album":(t.get("album") or {}).get("name",""),
            "duration":ms_to_mmss(t.get("duration_ms",0)),
            "image": img_url
        })
        if len(tracks)>=max_tracks: break
    return tracks,r

def fallback_track_search(token,mood,lang,limit=10):
    q=f"{LANG_HINT.get(lang,'english')} {mood} song"
    r=spotify_request_get("search", token, {"q":q,"type":"track","limit":limit})
    if r.status_code!=200: return None,r
    tracks=[]
    for t in r.json().get("tracks",{}).get("items",[]):
        album_images = (t.get("album") or {}).get("images", [])
        img_url = album_images[1]["url"] if len(album_images)>=2 else (album_images[0]["url"] if album_images else "")
        tracks.append({
            "name":t.get("name",""),
            "artists":", ".join(a.get("name","") for a in t.get("artists",[])),
            "url":t.get("external_urls",{}).get("spotify",""),
            "album":(t.get("album") or {}).get("name",""),
            "duration":ms_to_mmss(t.get("duration_ms",0)),
            "image": img_url
        })
    return tracks,r

def recommend_music_ui(mood_text, language, theme):
    token=get_access_token()
    if not token:
        return "<div style='color:crimson;font-weight:600'>⚠️ Not logged in. Click Login and paste the code.</div>"
    mood=normalize_mood(mood_text)
    playlist,_=search_playlists_for_language_mood(token,mood,language)
    tracks=None; pname=None;purl=None
    if playlist:
        pname=playlist.get("name"); purl=playlist.get("external_urls",{}).get("spotify")
        tracks,_=get_tracks_from_playlist(token,playlist.get("id"),20)
    if not tracks:
        tracks,_=fallback_track_search(token,mood,language)
    if not tracks:
        return "<div style='color:crimson'>No songs found.</div>"

    if theme=="dark":
        bg="#0f0f0f"; fg="#ffffff"; sub="#bfbfbf"; link="#1DB954"; card="#161616"
    else:
        bg="#f7f7f7"; fg="#111111"; sub="#555555"; link="#1DB954"; card="#ffffff"

    placeholder_img = "https://via.placeholder.com/300?text=No+Image"

    html_parts = [f"<div style='background:{bg};color:{fg};padding:18px;border-radius:12px'>"]
    html_parts.append(f"<h3 style='color:{link};margin:0 0 10px 0'>🎶 Top {min(10,len(tracks))} — {escape(mood.title())} Songs ({escape(language)})</h3>")
    if pname and purl:
        html_parts.append(f"<div style='margin-bottom:10px;color:{sub}'>Playlist: <a href='{purl}' target='_blank' style='color:{link}'>{escape(pname)}</a></div>")

    html_parts.append("<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px'>")
    for t in tracks[:10]:
        name, artists, album, dur, url, img = (
            escape(t.get("name","Unknown")),
            escape(t.get("artists","")),
            escape(t.get("album","")),
            escape(t.get("duration","")),
            t.get("url","") or "#",
            t.get("image") or placeholder_img,
        )
        card_html = f"""
        <a href="{url}" target="_blank" style="text-decoration:none;color:{fg}">
          <div style="background:{card};padding:10px;border-radius:10px;display:flex;flex-direction:column;gap:8px;box-shadow:0 6px 18px rgba(0,0,0,0.15)">
            <div style="width:100%;height:140px;overflow:hidden;border-radius:8px;background:#000">
              <img src="{img}" style="width:100%;height:100%;object-fit:cover;"/>
            </div>
            <div style="font-weight:700;font-size:0.98em">{name}</div>
            <div style="font-size:0.88em;color:{sub}">{artists}</div>
            <div style="font-size:0.78em;color:{sub};margin-top:auto">{album} • {dur}</div>
          </div>
        </a>"""
        html_parts.append(card_html)

    html_parts.append("</div></div>")
    return "\n".join(html_parts)

# --- Build Gradio UI ---
load_tokens()
theme_obj = None
try:
    theme_obj = gr.themes.Soft()
except Exception:
    theme_obj = None

with gr.Blocks(title="Mood-based Spotify Recommender", theme=theme_obj) as demo:
    gr.Markdown("<h2 style='color:#1DB954;text-align:center'>🎵 Mood-based Spotify Recommender</h2>")
    with gr.Row():
        with gr.Column(scale=1):
            login_group = gr.Column(visible=True)
            with login_group:
                login_btn = gr.Button("🔑 Login with Spotify")
                code_box = gr.Textbox(label="Paste Spotify `code`", placeholder="Paste code from redirect URL", lines=1)
                auth_out = gr.Textbox(label="Auth status", interactive=False)
            logout_btn = gr.Button("🔓 Logout")
            gr.Markdown("----")
            mood_in = gr.Textbox(label="Mood", value="happy")
            lang_in = gr.Dropdown(label="Language", choices=["en","hi","ta"], value="en")
            theme_in = gr.Radio(label="Theme", choices=["dark","light"], value="dark")
            submit_btn = gr.Button("🎶 Get Songs", variant="primary")
        with gr.Column(scale=2):
            output_html = gr.HTML("<div style='color:#888'>Results will appear here</div>")

    login_btn.click(lambda: login_open_browser(), None, auth_out)
    code_box.submit(lambda code: exchange_code(code), inputs=code_box, outputs=auth_out)
    logout_btn.click(logout_action, outputs=auth_out)
    submit_btn.click(recommend_music_ui, inputs=[mood_in, lang_in, theme_in], outputs=[output_html])

    def hide_login_ui():
        if get_access_token():
            return gr.update(visible=False), "✅ Logged in (token loaded)"
        return gr.update(visible=True), ""
    demo.load(hide_login_ui, outputs=[login_group, auth_out])

demo.launch(debug=True)
