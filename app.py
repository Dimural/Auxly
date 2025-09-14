from flask import Flask, request, redirect, url_for, render_template, session
import os
from datetime import timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from dotenv import load_dotenv
from spotipy.cache_handler import FlaskSessionCacheHandler
from collections import Counter
import math


load_dotenv()
#DEFINING CONSTANTS
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SECRET_KEY = os.urandom(24)

REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SCOPE = "user-top-read"

# ==== Flask App Setup ====
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = "spotify_session"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

# ==== OAuth Setup ====
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

# ---------- Auth helpers (unchanged) ----------
def get_auth_manager():
    cache_handler = FlaskSessionCacheHandler(session)
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=cache_handler,
        show_dialog=True,
    )

def get_sp():
    auth_manager = get_auth_manager()
    if not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
        return None
    return spotipy.Spotify(auth_manager=auth_manager)

# ---------- Icons (kept) ----------
def get_genre_icon(genre_name):
    genre_lower = genre_name.lower()
    if any(word in genre_lower for word in ['rock', 'metal', 'punk', 'grunge', 'hardcore']):
        return '🤘'
    elif any(word in genre_lower for word in ['electronic', 'edm', 'house', 'techno', 'trance', 'dubstep', 'ambient', 'synthwave']):
        return '⚡'
    elif any(word in genre_lower for word in ['hip hop', 'rap', 'trap', 'r&b', 'soul']):
        return '🎤'
    elif any(word in genre_lower for word in ['pop', 'synthpop', 'electropop', 'indie pop']):
        return '💫'
    elif any(word in genre_lower for word in ['jazz', 'blues', 'bebop', 'smooth jazz']):
        return '🎷'
    elif any(word in genre_lower for word in ['classical', 'orchestral', 'symphonic', 'baroque', 'romantic']):
        return '🎼'
    elif any(word in genre_lower for word in ['country', 'folk', 'bluegrass', 'americana']):
        return '🌾'
    elif any(word in genre_lower for word in ['reggae', 'ska', 'dub', 'world music', 'latin']):
        return '🌍'
    elif any(word in genre_lower for word in ['funk', 'disco', 'groove']):
        return '🕺'
    elif any(word in genre_lower for word in ['alternative', 'indie', 'experimental']):
        return '🎭'
    else:
        return '🎵'

# =========================
# Super-genre RADAR + GRADE
# =========================

# 1) Roll-up rules: map micro-genres to broader buckets
SUPER_GENRE_RULES = {
    "Pop": ["pop", "synthpop", "electropop", "dance pop", "k-pop", "kpop", "j-pop", "jpop"],
    "Hip-Hop/Rap": ["hip hop", "rap", "trap", "drill", "boom bap"],
    "R&B/Soul": ["r&b", "neo soul", "soul", "contemporary r&b"],
    "Rock": ["rock", "punk", "emo", "grunge", "shoegaze", "garage"],
    "Metal": ["metal", "core", "grind", "doom", "sludge", "deathcore"],
    "Indie/Alt": ["indie", "alt", "bedroom pop", "lo-fi", "lofi", "dreampop", "dream pop"],
    "Electronic": ["electronic", "edm", "house", "techno", "trance", "dubstep",
                   "dnb", "drum and bass", "ambient", "synthwave", "future bass", "garage"],
    "Latin": ["latin", "reggaeton", "salsa", "bachata", "cumbia", "mariachi", "regional mexican"],
    "Reggae/Dancehall": ["reggae", "dancehall", "ska", "dub"],
    "Country/Folk": ["country", "americana", "bluegrass", "folk", "singer-songwriter"],
    "Jazz/Blues": ["jazz", "bebop", "bossa", "swing", "fusion", "blues"],
    "Classical/Score": ["classical", "baroque", "romantic", "orchestral", "soundtrack", "score"],
    "World/Global": ["afro", "afrobeats", "afrobeat", "afro-house", "afro pop", "afropop",
                     "bollywood", "desi", "c-pop", "mandopop", "cantopop", "fado", "flamenco", "klezmer", "world", "global"],
}

def super_genre_for(genre: str) -> str:
    g = genre.lower()
    for bucket, keywords in SUPER_GENRE_RULES.items():
        for kw in keywords:
            if kw in g:
                return bucket
    if "r&b" in g or "soul" in g:
        return "R&B/Soul"
    if "hip" in g and "hop" in g:
        return "Hip-Hop/Rap"
    return "Indie/Alt"  # safe default if nothing matched

# 2) Collect way more listening: short/medium/long + top-tracks artists
def collect_user_genre_counts(sp):
    """
    Returns (Counter of super-genres, unique_artist_count).
    Aggregates:
      - current_user_top_artists across short/medium/long (weighted by recency)
      - artists from current_user_top_tracks across the same ranges (lower weight)
    """
    weights = {"short_term": 1.0, "medium_term": 0.8, "long_term": 0.6}
    ranges = ["short_term", "medium_term", "long_term"]

    super_counts = Counter()
    seen_artists = set()

    # Top ARTISTS
    for rng in ranges:
        items = sp.current_user_top_artists(limit=50, time_range=rng).get("items", [])
        for a in items:
            aid = a.get("id")
            if aid:
                seen_artists.add(aid)
            for gen in a.get("genres", []):
                super_counts[super_genre_for(gen)] += weights[rng]

    # Top TRACKS → artist genres (only if not already seen)
    for rng in ranges:
        tracks = sp.current_user_top_tracks(limit=50, time_range=rng).get("items", [])
        for t in tracks:
            for a in t.get("artists", []):
                aid = a.get("id")
                if not aid or aid in seen_artists:
                    continue
                try:
                    art = sp.artist(aid)
                    seen_artists.add(aid)
                    for gen in art.get("genres", []):
                        super_counts[super_genre_for(gen)] += 0.6 * weights[rng]
                except Exception:
                    pass

    return super_counts, len(seen_artists)

# 3) Build a readable radar: top-8 + Other; sqrt scaling
def build_radar_from_counts(super_counts: Counter, top_k: int = 8):
    common = super_counts.most_common(top_k)
    kept_labels = [name for name, _ in common]
    other_sum = sum(c for g, c in super_counts.items() if g not in kept_labels)

    values = []
    max_val = max([c for _, c in common] + ([other_sum] if other_sum > 0 else [1]))
    for _, c in common:
        values.append(5 + 95 * (math.sqrt(c / max_val)))  # 5..100
    if other_sum > 0:
        kept_labels.append("Other")
        values.append(5 + 95 * (math.sqrt(other_sum / max_val)))

    return kept_labels, values

# 4) New letter grade: diversity (entropy) + depth (unique artists) + activity
def grade_from_genres(super_counts: Counter, unique_artist_count: int):
    total = sum(super_counts.values())
    if total == 0:
        return "F", "We couldn’t detect enough listening to evaluate."

    probs = [c / total for c in super_counts.values()]
    H = -sum(p * math.log(p + 1e-12) for p in probs)
    H_max = math.log(len(super_counts)) if len(super_counts) > 0 else 1.0
    diversity = (H / H_max) if H_max > 0 else 0.0

    depth = min(1.0, math.log(1 + unique_artist_count) / math.log(1 + 100))
    activity = min(1.0, total / 200.0)

    score = 100 * (0.45 * diversity + 0.35 * depth + 0.20 * activity)
    score = max(0, min(100, score))

    def to_letter(s):
        if s >= 98: return "S+"
        if s >= 95: return "S"
        if s >= 92: return "S-"
        if s >= 88: return "A+"
        if s >= 84: return "A"
        if s >= 80: return "A-"
        if s >= 76: return "B+"
        if s >= 73: return "B"
        if s >= 70: return "B-"
        if s >= 68: return "C+"
        if s >= 65: return "C"
        if s >= 62: return "C-"
        if s >= 59: return "D+"
        if s >= 56: return "D"
        if s >= 53: return "D-"
        return "F"

    grade = to_letter(score)
    descriptions = {
        "S+": "Legendary explorer—huge variety and depth.",
        "S":  "Elite listener—balanced and deep catalog.",
        "S-": "Superior taste—diverse and engaged.",
        "A+": "Excellent range with strong depth.",
        "A":  "Great variety and consistent listening.",
        "A-": "Very good mix and habits.",
        "B+": "Good variety; keep exploring.",
        "B":  "Decent range; room to grow.",
        "B-": "Some variety; try new corners.",
        "C+": "Average diversity; explore more.",
        "C":  "Basic listening patterns.",
        "C-": "Limited genres; branch out.",
        "D+": "Casual listener; discover more.",
        "D":  "Occasional listening.",
        "D-": "New to music; welcome!",
        "F":  "Not enough data to rate.",
    }
    return grade, descriptions.get(grade, "Unknown rating")

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/login")
def login():
    # Clear any cached token inside THIS session so the user can switch accounts
    try:
        get_auth_manager().cache_handler.delete_cached_token()
    except Exception:
        pass
    session.clear()
    auth_manager = get_auth_manager()
    return redirect(auth_manager.get_authorize_url())

@app.route("/callback")
def callback():
    auth_manager = get_auth_manager()
    code = request.args.get("code")
    auth_manager.get_access_token(code)  # stores token in Flask session
    sp = spotipy.Spotify(auth_manager=auth_manager)

    profile = sp.current_user()
    session["display_name"] = profile.get("display_name", "Spotify User")
    images = profile.get("images", [])
    session["profile_pic"] = images[0]["url"] if images else None

    return redirect(url_for("menu"))

@app.route("/menu")
def menu():
    sp = get_sp()
    if sp is None:
        return redirect(url_for("login"))

    profile = sp.current_user()
    display_name = profile.get("display_name", "Spotify User")
    images = profile.get("images", [])
    profile_pic = images[0]["url"] if images else None

    # >>> NEW: richer aggregation + roll-up + radar + grade <<<
    super_counts, unique_artist_count = collect_user_genre_counts(sp)
    radar_labels, radar_values = build_radar_from_counts(super_counts, top_k=8)
    listener_grade, rating_description = grade_from_genres(super_counts, unique_artist_count)

    return render_template(
        "menu.html",
        display_name=display_name,
        profile_pic=profile_pic,
        radar_labels=json.dumps(radar_labels),
        radar_values=json.dumps(radar_values),
        listener_grade=listener_grade,
        listener_score="N/A",
        rating_description=rating_description
    )

@app.route("/top-artists")
def top_artists():
    time_range = request.args.get("range", "short_term")
    sp = get_sp()
    if sp is None:
        return redirect(url_for("login"))

    raw_artists = sp.current_user_top_artists(limit=10, time_range=time_range)["items"]

    artists = []
    for artist in raw_artists:
        artist_data = {
            "name": artist["name"],
            "image": None
        }
        if artist.get("images"):
            artist_data["image"] = artist["images"][0]["url"]
        artists.append(artist_data)

    return render_template("topartists.html", artists=artists, time_range=time_range)

@app.route("/top-tracks")
def top_tracks():
    time_range = request.args.get("range", "short_term")
    sp = get_sp()
    if sp is None:
        return redirect(url_for("login"))

    raw_tracks = sp.current_user_top_tracks(limit=10, time_range=time_range)["items"]

    tracks = []
    for track in raw_tracks:
        track_data = {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album_image": None
        }
        if track.get("album", {}).get("images"):
            track_data["album_image"] = track["album"]["images"][0]["url"]
        tracks.append(track_data)

    return render_template("toptracks.html", tracks=tracks, time_range=time_range)

@app.route("/top-genres")
def top_genres():
    time_range = request.args.get("range", "short_term")
    sp = get_sp()
    if sp is None:
        return redirect(url_for("login"))

    artists = sp.current_user_top_artists(limit=20, time_range=time_range)["items"]

    genre_counts = {}
    for artist in artists:
        for genre in artist.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    genres = []
    for genre, _count in sorted_genres[:10]:
        genres.append({
            "name": genre,
            "icon": get_genre_icon(genre)
        })

    return render_template("topgenres.html", genres=genres, time_range=time_range)

@app.route("/logout")
def logout():
    try:
        get_auth_manager().cache_handler.delete_cached_token()
    except Exception:
        pass
    session.clear()
    return """
        <p>You have been logged out.</p>
        <a href='/'>Log in again</a>
    """

if __name__ == "__main__":
    try:
        os.remove(".cache")
    except OSError:
        pass
    app.run(debug=True)

