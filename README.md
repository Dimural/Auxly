# Auxly

Auxly is a playful Spotify insights companion built with Flask. Connect your Spotify account to see your listening DNA visualized as a radar chart, get a letter-grade for your habits, and dive into your top artists, tracks, and genres across different time ranges.

## Features
- Spotify OAuth login with session-based cache.
- Genre rollups + radar chart that blends short, medium, and long-term listening.
- Listener letter-grade that weighs diversity, depth, and activity.
- Animated, mobile-friendly pages for top artists, tracks, and genres.
- One-click range filters (last month, this year, all time).

## Stack
- Python + Flask for the web app and routing.
- Spotipy for Spotify Web API access.
- Jinja templates with Chart.js for visualization.
- Vanilla HTML/CSS animations for the UI.

## Quickstart
1) Install Python 3.10+ and create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install flask spotipy python-dotenv
```
2) Create a Spotify app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and set the redirect URI to match `SPOTIFY_REDIRECT_URI` (e.g., `http://localhost:5000/callback`).
3) Add a `.env` file in the project root:
```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/callback
```
4) Run the server:
```bash
python app.py
```
5) Open `http://localhost:5000` and log in with Spotify.

## How it works
- `/` landing page → `/login` for Spotify OAuth.
- `/menu` shows your radar chart, listener grade, and navigation cards.
- `/top-artists`, `/top-tracks`, `/top-genres` each support `?range=short_term|medium_term|long_term`.
- Genre rollups and grading live in `app.py` (see `collect_user_genre_counts`, `build_radar_from_counts`, `grade_from_genres`).

## Customization ideas
- Tweak super-genre buckets or grade weights in `app.py`.
- Adjust colors/animations in `templates/` to fit your brand.
- Add more panels (recently played, playlists) using Spotipy helpers.

## Troubleshooting
- Stuck in a login loop: clear your browser cookies for the site and ensure the redirect URI matches the Spotify app config.
- Empty data: Spotify returns limited stats for brand-new accounts; listen to a few tracks first.
