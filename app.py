from flask import Flask, request, redirect, url_for, render_template, session
import os
from datetime import timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from dotenv import load_dotenv

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

def categorize_genres(genres):
    """Categorize specific genres into broader categories"""
    genre_mapping = {
        'rock': ['rock', 'alternative rock', 'indie rock', 'hard rock', 'classic rock', 'punk rock', 'pop rock', 'folk rock', 'psychedelic rock', 'progressive rock', 'garage rock', 'post-rock', 'math rock', 'shoegaze', 'grunge', 'metal', 'heavy metal', 'death metal', 'black metal', 'thrash metal', 'power metal', 'progressive metal', 'nu metal', 'industrial metal', 'folk metal', 'symphonic metal'],
        'pop': ['pop', 'pop rock', 'synthpop', 'electropop', 'indie pop', 'dream pop', 'jangle pop', 'power pop', 'teen pop', 'bubblegum pop', 'art pop', 'avant-pop', 'experimental pop', 'baroque pop', 'chamber pop', 'orchestral pop', 'psychedelic pop', 'sunshine pop', 'yacht rock'],
        'electronic': ['electronic', 'edm', 'house', 'techno', 'trance', 'dubstep', 'drum and bass', 'ambient', 'idm', 'breakbeat', 'garage', 'jungle', 'hardcore', 'industrial', 'synthwave', 'vaporwave', 'future bass', 'trap', 'progressive house', 'deep house', 'acid house', 'electro', 'eurodance', 'europop', 'euro house', 'euro trance', 'euro techno'],
        'hip_hop': ['hip hop', 'rap', 'trap', 'conscious hip hop', 'alternative hip hop', 'experimental hip hop', 'underground hip hop', 'east coast hip hop', 'west coast hip hop', 'southern hip hop', 'midwest hip hop', 'battle rap', 'horrorcore', 'gangsta rap', 'political hip hop', 'jazz rap', 'funk rap', 'soul rap', 'r&b', 'neo soul', 'contemporary r&b', 'alternative r&b'],
        'jazz': ['jazz', 'bebop', 'cool jazz', 'hard bop', 'modal jazz', 'free jazz', 'avant-garde jazz', 'post-bop', 'smooth jazz', 'fusion', 'acid jazz', 'nu jazz', 'latin jazz', 'afro-cuban jazz', 'bossa nova', 'samba', 'tango', 'flamenco', 'fado', 'reggae', 'ska', 'dub', 'dancehall', 'calypso', 'soca'],
        'classical': ['classical', 'baroque', 'romantic', 'modern classical', 'contemporary classical', 'minimalism', 'impressionism', 'expressionism', 'serialism', 'aleatoric', 'chance music', 'ambient', 'new age', 'world music', 'folk', 'country', 'bluegrass', 'americana', 'roots rock', 'blues', 'delta blues', 'chicago blues', 'texas blues', 'memphis blues', 'piedmont blues', 'country blues', 'electric blues', 'rhythm and blues', 'soul', 'motown', 'stax', 'atlantic', 'philadelphia soul', 'chicago soul', 'memphis soul', 'southern soul', 'northern soul', 'blue-eyed soul', 'brown-eyed soul', 'neo soul', 'alternative soul', 'psychedelic soul', 'funk', 'p-funk', 'g-funk', 'funk rock', 'funk metal', 'funk punk', 'funk pop', 'funk soul', 'funk jazz', 'funk blues', 'funk country', 'funk folk', 'funk classical', 'funk electronic', 'funk hip hop', 'funk reggae', 'funk ska', 'funk punk', 'funk metal', 'funk rock', 'funk pop', 'funk soul', 'funk jazz', 'funk blues', 'funk country', 'funk folk', 'funk classical', 'funk electronic', 'funk hip hop', 'funk reggae', 'funk ska']
    }
    
    categorized = {category: 0 for category in genre_mapping.keys()}
    
    for genre in genres:
        genre_lower = genre.lower()
        for category, subgenres in genre_mapping.items():
            if any(subgenre in genre_lower for subgenre in subgenres):
                categorized[category] += 1
                break
    
    return categorized

def normalize_genre_scores(categorized_genres):
    """Normalize genre scores to create a balanced radar chart"""
    max_score = max(categorized_genres.values()) if any(categorized_genres.values()) else 1
    if max_score == 0:
        return {k: 0 for k in categorized_genres.keys()}
    
    # Normalize to 0-100 scale with some minimum values for visual appeal
    normalized = {}
    for genre, score in categorized_genres.items():
        if score > 0:
            # Create a more dynamic range: minimum 20, maximum 100
            normalized[genre] = 20 + (score / max_score) * 80
        else:
            normalized[genre] = 5  # Small base value for visual appeal
    
    return normalized

def get_genre_icon(genre_name):
    """Get an appropriate icon for a genre"""
    genre_lower = genre_name.lower()
    
    # Rock and Metal genres
    if any(word in genre_lower for word in ['rock', 'metal', 'punk', 'grunge', 'hardcore']):
        return '🤘'
    # Electronic genres
    elif any(word in genre_lower for word in ['electronic', 'edm', 'house', 'techno', 'trance', 'dubstep', 'ambient', 'synthwave']):
        return '⚡'
    # Hip Hop and Rap
    elif any(word in genre_lower for word in ['hip hop', 'rap', 'trap', 'r&b', 'soul']):
        return '🎤'
    # Pop genres
    elif any(word in genre_lower for word in ['pop', 'synthpop', 'electropop', 'indie pop']):
        return '💫'
    # Jazz and Blues
    elif any(word in genre_lower for word in ['jazz', 'blues', 'bebop', 'smooth jazz']):
        return '🎷'
    # Classical and Orchestral
    elif any(word in genre_lower for word in ['classical', 'orchestral', 'symphonic', 'baroque', 'romantic']):
        return '🎼'
    # Country and Folk
    elif any(word in genre_lower for word in ['country', 'folk', 'bluegrass', 'americana']):
        return '🌾'
    # Reggae and World
    elif any(word in genre_lower for word in ['reggae', 'ska', 'dub', 'world music', 'latin']):
        return '🌍'
    # Funk and Disco
    elif any(word in genre_lower for word in ['funk', 'disco', 'groove']):
        return '🕺'
    # Alternative and Indie
    elif any(word in genre_lower for word in ['alternative', 'indie', 'experimental']):
        return '🎭'
    # Default icon
    else:
        return '🎵'

def calculate_listener_rating(profile, categorized_genres):
    """Calculate a music listener rating from S+ to D- based on listening habits"""
    
    # Base score starts at 0 (much more challenging)
    score = 0
    
    # Factor 1: Genre Diversity (0-20 points)
    # Only count genres with substantial listening (3+ artists)
    active_genres = sum(1 for count in categorized_genres.values() if count >= 3)
    max_genres = len(categorized_genres)
    if max_genres > 0:
        genre_diversity_score = (active_genres / max_genres) * 20
        score += genre_diversity_score
    
    # Factor 2: Listening Depth (0-30 points)
    # This is the most important factor - how much they actually listen
    total_artist_count = sum(categorized_genres.values())
    if total_artist_count >= 50:
        depth_score = 30  # Heavy listener
    elif total_artist_count >= 30:
        depth_score = 25  # Regular listener
    elif total_artist_count >= 20:
        depth_score = 20  # Moderate listener
    elif total_artist_count >= 15:
        depth_score = 15  # Light listener
    elif total_artist_count >= 10:
        depth_score = 10  # Very light listener
    elif total_artist_count >= 5:
        depth_score = 5   # Minimal listener
    else:
        depth_score = 0   # Barely listens
    score += depth_score
    
    # Factor 3: Genre Balance (0-25 points)
    # Check if user has a good mix of different genre categories
    genre_counts = list(categorized_genres.values())
    if genre_counts and len(genre_counts) > 1:
        # Calculate standard deviation to measure balance
        mean_count = sum(genre_counts) / len(genre_counts)
        variance = sum((x - mean_count) ** 2 for x in genre_counts) / len(genre_counts)
        std_dev = variance ** 0.5
        
        # Lower standard deviation = more balanced listening
        if std_dev == 0:
            balance_score = 25  # Perfect balance
        else:
            # Normalize: lower std dev gets higher score
            max_std = max(genre_counts)
            balance_score = max(0, 25 - (std_dev / max_std) * 15)
        score += balance_score
    
    # Factor 4: Genre Exploration (0-15 points)
    # Bonus for having multiple genres with decent counts (5+ artists)
    substantial_genres = sum(1 for count in categorized_genres.values() if count >= 5)
    exploration_score = min(15, substantial_genres * 3)
    score += exploration_score
    
    # Factor 5: Specialization Penalty (-10 to +10 points)
    # Penalize if they only listen to 1-2 genres heavily
    max_genre_count = max(categorized_genres.values()) if categorized_genres.values() else 0
    active_genre_count = sum(1 for count in categorized_genres.values() if count > 0)
    
    if active_genre_count <= 2 and max_genre_count >= 8:
        # Heavy listener but very limited genres
        specialization_score = -10
    elif active_genre_count <= 3 and max_genre_count >= 6:
        # Moderate listener but limited genres
        specialization_score = -5
    elif active_genre_count >= 4 and max_genre_count >= 5:
        # Good variety and depth
        specialization_score = 10
    elif active_genre_count >= 3 and max_genre_count >= 3:
        # Decent variety
        specialization_score = 5
    else:
        specialization_score = 0
    
    score += specialization_score
    
    # Factor 6: Minimum Threshold Penalty
    # If they barely listen to music, cap their score
    if total_artist_count < 10:
        score = min(score, 30)  # Cap at D+ for very light listeners
    elif total_artist_count < 20:
        score = min(score, 50)  # Cap at C for light listeners
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Convert score to letter grade (much more challenging)
    if score >= 98:
        return "S+"
    elif score >= 95:
        return "S"
    elif score >= 92:
        return "S-"
    elif score >= 88:
        return "A+"
    elif score >= 84:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 76:
        return "B+"
    elif score >= 73:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 68:
        return "C+"
    elif score >= 65:
        return "C"
    elif score >= 62:
        return "C-"
    elif score >= 59:
        return "D+"
    elif score >= 56:
        return "D"
    elif score >= 53:
        return "D-"
    else:
        return "F"

def get_rating_description(grade):
    """Get a description for the rating grade"""
    descriptions = {
        "S+": "Legendary Music Explorer - You're a true music connoisseur with exceptional taste and depth!",
        "S": "Elite Music Enthusiast - Your musical knowledge and diversity are outstanding!",
        "S-": "Superior Music Lover - You have excellent taste and explore music actively!",
        "A+": "Excellent Music Explorer - You're very well-rounded with great listening habits!",
        "A": "Great Music Listener - You have diverse taste and listen to music regularly!",
        "A-": "Very Good Music Fan - You explore music actively and have good variety!",
        "B+": "Good Music Listener - You have solid musical taste and decent variety!",
        "B": "Decent Music Fan - You're on the right track with room to grow!",
        "B-": "Okay Music Listener - You have potential but need to explore more!",
        "C+": "Average Music Fan - You listen to music but could diversify more!",
        "C": "Basic Music Listener - Time to expand your musical horizons!",
        "C-": "Limited Music Fan - Try branching out to new genres!",
        "D+": "Casual Listener - Music could be more important in your life!",
        "D": "Occasional Listener - Time to discover the world of music!",
        "D-": "Music Newcomer - Welcome to the wonderful world of music!",
        "F": "Music Beginner - Start your musical journey today!"
    }
    return descriptions.get(grade, "Unknown rating")

@app.route("/")
def index():
    session.clear()
    return render_template("landing.html")

@app.route("/login")
def login():
    session.clear()
    auth_url = sp_oauth.get_authorize_url() + "&show_dialog=true"
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        show_dialog=True
    )

    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    sp = spotipy.Spotify(auth=token_info['access_token'])
    profile = sp.current_user()

    session["display_name"] = profile.get("display_name", "Spotify User")
    images = profile.get("images", [])
    session["profile_pic"] = images[0]["url"] if images else None

    return redirect(url_for("menu"))

@app.route("/menu")
def menu():
    token_info = session.get("token_info")
    if not token_info:
        return redirect(url_for("login"))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    profile = sp.current_user()
    display_name = profile.get("display_name", "Spotify User")
    images = profile.get("images", [])
    profile_pic = images[0]["url"] if images else None

    # Get top artists and extract genres for radar chart
    top_artists = sp.current_user_top_artists(limit=50, time_range="long_term")["items"]
    user_genres = []
    for artist in top_artists:
        user_genres.extend(artist["genres"])

    # Categorize and normalize genres for radar chart
    categorized_genres = categorize_genres(user_genres)
    radar_data = normalize_genre_scores(categorized_genres)
    
    # Calculate listener rating
    listener_grade = calculate_listener_rating(profile, categorized_genres)
    rating_description = get_rating_description(listener_grade)
    
    # Convert to format suitable for Chart.js
    radar_labels = list(radar_data.keys())
    radar_values = list(radar_data.values())

    return render_template("menu.html",
        display_name=display_name,
        profile_pic=profile_pic,
        radar_labels=json.dumps(radar_labels),
        radar_values=json.dumps(radar_values),
        listener_grade=listener_grade,
        listener_score="N/A",  # Since we're not returning score anymore
        rating_description=rating_description
    )

@app.route("/top-artists")
def top_artists():
    time_range = request.args.get("range", "short_term")
    token_info = session.get("token_info")
    if not token_info:
        return redirect(url_for("login"))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    raw_artists = sp.current_user_top_artists(limit=10, time_range=time_range)["items"]
    
    # Include artist images from Spotify API
    artists = []
    for artist in raw_artists:
        artist_data = {
            "name": artist["name"],
            "image": None
        }
        # Get the first available image (usually the highest quality)
        if artist.get("images") and len(artist["images"]) > 0:
            artist_data["image"] = artist["images"][0]["url"]
        artists.append(artist_data)

    return render_template("topartists.html", artists=artists, time_range=time_range)

@app.route("/top-tracks")
def top_tracks():
    time_range = request.args.get("range", "short_term")
    token_info = session.get("token_info")
    if not token_info:
        return redirect(url_for("login"))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    raw_tracks = sp.current_user_top_tracks(limit=10, time_range=time_range)["items"]
    
    # Include track info and album images
    tracks = []
    for track in raw_tracks:
        track_data = {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "album_image": None
        }
        # Get album image (more relevant for tracks)
        if track.get("album", {}).get("images") and len(track["album"]["images"]) > 0:
            track_data["album_image"] = track["album"]["images"][0]["url"]
        tracks.append(track_data)

    return render_template("toptracks.html", tracks=tracks, time_range=time_range)

@app.route("/top-genres")
def top_genres():
    time_range = request.args.get("range", "short_term")
    token_info = session.get("token_info")
    if not token_info:
        return redirect(url_for("login"))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    artists = sp.current_user_top_artists(limit=20, time_range=time_range)["items"]

    genre_counts = {}
    for artist in artists:
        for genre in artist["genres"]:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    genres = []
    
    for genre, count in sorted_genres[:10]:
        genres.append({
            "name": genre,
            "icon": get_genre_icon(genre)
        })

    return render_template("topgenres.html", genres=genres, time_range=time_range)

@app.route("/logout")
def logout():
    session.clear()
    return """
        <p>You have been logged out.</p>
        <a href='/'>Log in again</a>
    """

if __name__ == "__main__":
    app.run(debug=True)
    

