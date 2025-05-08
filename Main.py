from flask import Flask, render_template, request, redirect, session, url_for, flash
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
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/callback'

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
    
    # Get playlist info for the name
    playlist = sp.playlist(playlist_id)
    playlist_name = playlist['name']
    
    # Get all playlist tracks
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    tracks.extend(results['items'])
    
    # Keep getting tracks until we have all of them
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    # Extract track URIs
    track_uris = [item['track']['uri'] for item in tracks if item['track'] is not None]
    total_tracks = len(track_uris)
    
    # Split into batches of 100 and shuffle each batch
    batches = []
    for i in range(0, total_tracks, 100):
        batch = track_uris[i:i+100]
        # Shuffle this batch
        for j in range(len(batch)-1, 0, -1):
            k = random.randint(0, j)
            batch[j], batch[k] = batch[k], batch[j]
        batches.append(batch)
    
    # Shuffle the order of the batches themselves
    for i in range(len(batches)-1, 0, -1):
        j = random.randint(0, i)
        batches[i], batches[j] = batches[j], batches[i]
    
    # Flatten the batches back into a single list
    shuffled_tracks = [track for batch in batches for track in batch]
    
    # Clear the current queue
    sp._put("me/player/queue", None)
    
    # Add tracks to queue in shuffled order
    for track_uri in shuffled_tracks:
        sp.add_to_queue(track_uri)
    
    flash(f'Successfully shuffled queue for playlist: {playlist_name} ({total_tracks} tracks)')
    return redirect(url_for('get_playlists'))

if __name__ == '__main__':
    app.run(debug=True)
