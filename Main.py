from flask import Flask, render_template, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

# Initialize Spotify OAuth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope='playlist-modify-public playlist-modify-private playlist-read-private'
)

@app.route('/')
def home():
    if 'token_info' not in session:
        return render_template('index.html', logged_in=False)
    return render_template('index.html', logged_in=True)

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for('home'))

@app.route('/playlists')
def get_playlists():
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    sp = spotipy.Spotify(auth=session['token_info']['access_token'])
    playlists = sp.current_user_playlists()
    return render_template('playlists.html', playlists=playlists['items'])

@app.route('/shuffle/<playlist_id>')
def shuffle_playlist(playlist_id):
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    sp = spotipy.Spotify(auth=session['token_info']['access_token'])
    
    # Get playlist tracks
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    # Extract track URIs
    track_uris = [item['track']['uri'] for item in tracks if item['track'] is not None]
    
    # Custom shuffle algorithm (Fisher-Yates shuffle)
    for i in range(len(track_uris)-1, 0, -1):
        j = random.randint(0, i)
        track_uris[i], track_uris[j] = track_uris[j], track_uris[i]
    
    # Remove all tracks from playlist
    sp.playlist_replace_items(playlist_id, [])
    
    # Add tracks back in new order
    # Spotify API has a limit of 100 tracks per request
    for i in range(0, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i:i+100])
    
    return redirect(url_for('get_playlists'))

if __name__ == '__main__':
    app.run(debug=True)
